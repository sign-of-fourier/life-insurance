"""Phase 7 (free part): similarity spaces, offline neighbour quality, and the neighbour-vote baseline. No LLM calls.

Every space is fit on the split's pool only; test cases are queries; neighbours come from the pool.
Representations: R1 = pretrained embeddings (experiments/emb/*.npy); R2 = own tokenizer (exp_data.tokens) + TF-IDF.
Spaces: random, cosine, pca (R2: LSA/SVD), vae (unsupervised), pls (supervised on pool golden), oracle (golden).

Scores per query (k neighbours), judged with golden (scoring side only):
  coverage   share of the query's rated conditions/chapters present in any neighbour
  jaccard    mean label Jaccard query vs neighbour
  grey       grey queries: share of neighbours with a shared GRY rule
  partial    partial-evidence queries: share of neighbours sharing a partial-evidence reason
  band       share of neighbours with the same outcome band
  vote       similarity-weighted majority band of the neighbours == query band (the free semi-supervised score)
  vendor     mean vendor-schema Jaccard (diagnostic: matching on format; compare with random)
Run: python src/retrieval.py [--k 3] [--spaces ...] -> experiments/offline_retrieval.{json,md}
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import exp_data as E  # noqa: E402

CIDS = E.ids()
IDX = {c: i for i, c in enumerate(CIDS)}
LAB = E.labels()
CLASS_RANK = {"Elite": 0, "Preferred Plus": 1, "Preferred": 2, "Preferred Tobacco": 2, "Standard Plus": 3, "Standard": 4,
              "Standard Tobacco": 4, "Table": 6, "Table Tobacco": 6, "Postpone": 9, "Decline": 10}


def l2(X):
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)


# --------------------------------------------------------------------------- representations
def rep_r1(name):
    return np.load(E.EXP / "emb" / f"{name}.npy")


_TOK = None


def rep_r2(pool, dims=None):
    """TF-IDF over own tokens, vocabulary fit on pool. Returns sparse matrix for all CIDS."""
    global _TOK
    from sklearn.feature_extraction.text import TfidfVectorizer
    if _TOK is None:
        _TOK = [E.tokens(c) for c in CIDS]
    v = TfidfVectorizer(analyzer=lambda x: x, min_df=2, sublinear_tf=True)
    v.fit([_TOK[IDX[c]] for c in pool])
    return v.transform(_TOK)


def dense_base(X, pool, n=256, seed=0):
    """Dense input for PCA/VAE/PLS: R1 as is; R2 sparse -> SVD(n) fit on pool."""
    if hasattr(X, "tocsr"):
        from sklearn.decomposition import TruncatedSVD
        svd = TruncatedSVD(n_components=n, random_state=seed).fit(X[[IDX[c] for c in pool]])
        return svd.transform(X)
    return X


# --------------------------------------------------------------------------- spaces
def sp_cosine(X, pool, **_):
    if hasattr(X, "tocsr"):
        from sklearn.preprocessing import normalize
        return normalize(X)
    return l2(X)


def sp_pca(X, pool, n=50, seed=0, **_):
    from sklearn.decomposition import PCA, TruncatedSVD
    P = [IDX[c] for c in pool]
    if hasattr(X, "tocsr"):
        m = TruncatedSVD(n_components=n, random_state=seed).fit(X[P])
    else:
        m = PCA(n_components=n, random_state=seed).fit(X[P])
    return l2(m.transform(X))


def sp_vae(X, pool, z=16, epochs=300, seed=0, **_):
    import torch
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    D = dense_base(X, pool, seed=seed)
    P = [IDX[c] for c in pool]
    mu, sd = D[P].mean(0), D[P].std(0) + 1e-6
    T = torch.tensor((D - mu) / sd, dtype=torch.float32)
    d = T.shape[1]
    enc = torch.nn.Sequential(torch.nn.Linear(d, 256), torch.nn.ReLU(), torch.nn.Linear(256, 2 * z))
    dec = torch.nn.Sequential(torch.nn.Linear(z, 256), torch.nn.ReLU(), torch.nn.Linear(256, d))
    opt = torch.optim.Adam(list(enc.parameters()) + list(dec.parameters()), lr=1e-3)
    tr = T[P]
    g = torch.Generator().manual_seed(seed)
    for ep in range(epochs):
        perm = torch.randperm(len(tr), generator=g)
        beta = min(1.0, ep / 100)            # KL warm-up
        for i in range(0, len(tr), 200):
            x = tr[perm[i:i + 200]]
            h = enc(x)
            m, lv = h[:, :z], h[:, z:].clamp(-8, 8)
            q = m + torch.randn_like(m) * (0.5 * lv).exp()
            rec = ((dec(q) - x) ** 2).sum(1).mean()
            kl = (-0.5 * (1 + lv - m ** 2 - lv.exp()).sum(1)).mean()
            loss = rec + beta * kl
            opt.zero_grad()
            loss.backward()
            opt.step()
    with torch.no_grad():
        M = enc(T)[:, :z].numpy()
    return l2(M)


def pls_targets(cids):
    chs = sorted({ch for c in CIDS for ch in LAB[c]["chapter_debits"]})
    grys = sorted({g for c in CIDS for g in LAB[c]["grey"]})
    Y = []
    for c in cids:
        L = LAB[c]
        row = [L["chapter_debits"].get(ch, 0) for ch in chs]
        row += [CLASS_RANK.get(L["risk_class"], 5), L["risk_class"] == "Decline", L["risk_class"] == "Postpone", L["ladder"] == "tobacco",
                L["table"], max(-50, min(L["net"], 450)), L["fe"], L["fe_perm"]]
        row += [g in L["grey"] for g in grys]
        Y.append(row)
    return np.asarray(Y, dtype=float)


def sp_pls(X, pool, n=16, seed=0, **_):
    from sklearn.cross_decomposition import PLSRegression
    D = dense_base(X, pool, n=512, seed=seed)
    P = [IDX[c] for c in pool]
    Y = pls_targets(pool)
    keep = Y.std(0) > 0
    m = PLSRegression(n_components=n, scale=True).fit(D[P], Y[:, keep])
    return l2(m.transform(D))


SPACES = {"cosine": sp_cosine, "pca": sp_pca, "vae": sp_vae, "pls": sp_pls}


# --------------------------------------------------------------------------- neighbours
def neighbours(S, test, pool, k):
    P = [IDX[c] for c in pool]
    Q = [IDX[c] for c in test]
    sim = S[Q] @ S[P].T
    if hasattr(sim, "toarray"):
        sim = sim.toarray()
    sim = np.asarray(sim)
    top = np.argsort(-sim, axis=1)[:, :k]
    return {test[i]: [(pool[j], float(sim[i, j])) for j in top[i]] for i in range(len(test))}


def oracle(test, pool, k):
    def sim(a, b):
        A, B = LAB[a], LAB[b]
        la, lb = set(A["labels"]), set(B["labels"])
        ga, gb = set(A["grey"]), set(B["grey"])
        j = len(la & lb) / len(la | lb) if la | lb else 1.0
        gj = len(ga & gb) / len(ga | gb) if ga | gb else 1.0
        return j + 0.5 * gj + 0.5 * (A["band"] == B["band"])
    out = {}
    for q in test:
        s = sorted(((p, sim(q, p)) for p in pool), key=lambda x: -x[1])
        out[q] = s[:k]
    return out


def random_nb(test, pool, k, seed):
    r = np.random.default_rng(seed)
    return {q: [(pool[j], 1.0) for j in r.choice(len(pool), k, replace=False)] for q in test}


# --------------------------------------------------------------------------- scoring
def score(nb):
    rows = defaultdict(list)
    for q, ns in nb.items():
        Lq = LAB[q]
        sl = E.slice_of(Lq)
        lq = set(Lq["labels"])
        lab_n = [LAB[p] for p, _ in ns]
        r = {}
        if lq:
            r["coverage"] = len(lq & set().union(*[set(x["labels"]) for x in lab_n])) / len(lq)
            r["jaccard"] = float(np.mean([len(lq & set(x["labels"])) / len(lq | set(x["labels"])) for x in lab_n]))
        if Lq["grey"]:
            r["grey"] = float(np.mean([bool(set(Lq["grey"]) & set(x["grey"])) for x in lab_n]))
        if Lq["partial"]:
            r["partial"] = float(np.mean([bool(set(Lq["partial"]) & set(x["partial"])) for x in lab_n]))
        r["band"] = float(np.mean([x["band"] == Lq["band"] for x in lab_n]))
        w = Counter()
        for (p, s), x in zip(ns, lab_n):
            w[x["band"]] += max(s, 1e-3)
        r["vote"] = float(w.most_common(1)[0][0] == Lq["band"])
        wx = Counter()
        for (p, s), x in zip(ns, lab_n):
            wx[x["decision"]] += max(s, 1e-3)
        r["vote_exact"] = float(wx.most_common(1)[0][0] == Lq["decision"])
        r["fe_match"] = float(np.mean([(x["fe"] > 0) == (Lq["fe"] > 0) for x in lab_n]))
        vq = E.vendors(q)
        r["vendor"] = float(np.mean([len(vq & E.vendors(p)) / len(vq | E.vendors(p)) for p, _ in ns]))
        for k_, v in r.items():
            rows[("all", k_)].append(v)
            rows[(sl, k_)].append(v)
    return {f"{s}:{m}": float(np.mean(v)) for (s, m), v in rows.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--reps", default="titan_whole,titan_docmean,cohere_whole,r2")
    ap.add_argument("--spaces", default="cosine,pca,vae,pls")
    ap.add_argument("--pool-frac", type=float, default=1.0, help="fit spaces on this fraction of the pool (learning curve)")
    ap.add_argument("--out", default="offline_retrieval")
    a = ap.parse_args()
    sp = E.splits()
    res = defaultdict(list)
    prior = []
    for seed, s in sp.items():
        test, pool = s["test"], s["pool"]
        maj = Counter(LAB[p]["band"] for p in pool).most_common(1)[0][0]
        prior.append(np.mean([LAB[q]["band"] == maj for q in test]))
        res[("random", "-")].append(score(random_nb(test, pool, a.k, int(seed))))
        res[("oracle", "-")].append(score(oracle(test, pool, a.k)))
        for rep in a.reps.split(","):
            if rep != "r2" and not (E.EXP / "emb" / f"{rep}.npy").exists():
                print("skip", rep, "(no embeddings yet)")
                continue
            X = rep_r2(pool) if rep == "r2" else rep_r1(rep)
            fit_pool = sorted(np.random.default_rng(int(seed)).choice(pool, int(len(pool) * a.pool_frac), replace=False)) if a.pool_frac < 1 else pool
            for name in a.spaces.split(","):
                S = SPACES[name](X, list(fit_pool), seed=int(seed))
                res[(name, rep)].append(score(neighbours(S, test, pool, a.k)))
                print(seed, rep, name, "done", flush=True)
    agg = {}
    for key, lst in res.items():
        ks = sorted(set().union(*lst))
        agg["|".join(key)] = {m: (float(np.mean([d[m] for d in lst if m in d])), float(np.std([d[m] for d in lst if m in d]))) for m in ks}
    out = {"k": a.k, "prior_majority_band_acc": float(np.mean(prior)), "results": agg}
    (E.EXP / f"{a.out}.json").write_text(json.dumps(out, indent=1))
    cols = ["all:coverage", "all:jaccard", "grey:grey", "partial:partial", "all:band", "all:vote", "all:vote_exact", "grey:vote",
            "partial:vote", "clean:vote", "all:fe_match", "all:vendor"]
    L = [f"# Offline retrieval quality (k={a.k}, mean ± sd over {len(sp)} splits, 200 test / 800 pool)", "",
         f"Majority-band prior (always predict the pool's most common band): {out['prior_majority_band_acc']:.3f}", "",
         "| space | repr | " + " | ".join(cols) + " |", "|---|---|" + "---|" * len(cols)]
    for key, v in sorted(agg.items(), key=lambda x: -x[1].get("all:coverage", (0, 0))[0]):
        sp_, rep = key.split("|")
        L.append(f"| {sp_} | {rep} | " + " | ".join(f"{v[c][0]:.3f}±{v[c][1]:.3f}" if c in v else "-" for c in cols) + " |")
    (E.EXP / f"{a.out}.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
