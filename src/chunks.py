"""Phase 7 U2: chunk by condition, and score condition-level retrieval offline (no LLM; Cohere embeddings only).

Index side (pool cases): golden steps grouped by condition (facts' truth_ref -> condition key) or by chapter for
non-condition items (TOB, BLD, MVR, ...). Each group = one chunk payload: the note lines written for its steps
(data/notes/<case>.lines.json), the clean golden findings, and the outcome (debits, cap, FE, decline/postpone, grey).
Chunk key = the LLM-extracted item (experiments/conditions/<case>.json) aligned to the group by embedding similarity;
items with no matching group become "no rating" chunks. Query side = the test case's extracted items only.

Offline scores (golden used only to judge):
  detect      share of the query's rated groups that some extracted item aligns to (misses = query-side detection gaps)
  label@k     share of retrieved chunks (per detected rated group) whose group label equals the query group's label
  debit@k     share of retrieved chunks with the same debit bucket as the query group (severity, not just topic)
  vote        case decision from condition-level votes: median neighbour debits per item, summed -> band
Run: python src/chunks.py [--k 3]  -> experiments/chunks/index.json, experiments/offline_chunks.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import exp_data as E  # noqa: E402
import llm  # noqa: E402
from rules import table_from_net  # noqa: E402
from schemas import Golden  # noqa: E402

CH = E.EXP / "chunks"
ALIGN_MIN = 0.35          # min cosine item<->group to align (else the item is a "no rating" chunk)


def bucket(d: int) -> str:
    return "0" if d <= 0 else "25" if d <= 25 else "50" if d <= 50 else "75-100" if d <= 100 else "125-200" if d <= 200 else "200+"


# --------------------------------------------------------------------------- golden groups
def groups(cid: str) -> dict:
    g = Golden.model_validate_json((E.ROOT / f"data/golden/{cid}.json").read_text())
    ev = json.loads((E.ROOT / f"data/source/{cid}/evidence.json").read_text())
    truth = json.loads((E.ROOT / f"data/truth/{cid}.json").read_text())
    ref = {f["fact_id"]: f.get("truth_ref") for f in ev["facts"]}
    conds = truth["conditions"]
    lines = json.loads((E.ROOT / f"data/notes/{cid}.lines.json").read_text())
    by_step = defaultdict(list)
    for ln in lines:
        by_step[ln["step"]].append(ln["text"])
    out = {}
    for s in g.trace:
        keys = set()
        for f in s.fact_ids:
            m = re.fullmatch(r"conditions\[(\d+)\]", str(ref.get(f)))
            if m and int(m.group(1)) < len(conds):
                keys.add("cond:" + conds[int(m.group(1))]["condition_key"])
        ch = re.match(r"[A-Z]+", s.rule_id).group(0)
        key = sorted(keys)[0] if keys else ("case" if ch in E.MECHANICS else f"ch:{ch}")
        grp = out.setdefault(key, {"label": key, "steps": [], "findings": [], "notes": [], "debits": 0, "cap": None, "fe": 0.0,
                                   "decline": False, "postpone": False, "rated": False, "grey": []})
        e = s.effect
        grp["steps"].append(s.step)
        grp["findings"].append(f"{s.finding} [{s.rule_id}]")
        grp["notes"] += by_step.get(s.step, [])
        grp["debits"] += e.debits - e.credits
        grp["cap"] = e.class_cap or grp["cap"]
        grp["fe"] += e.flat_extra.per_thousand if e.flat_extra else 0
        grp["decline"] |= e.decline
        grp["postpone"] |= bool(e.postpone_months)
        grp["rated"] |= E.rated(e)
        for ga in g.grey_areas:
            if s.rule_id in ga.rule_ids and ga.issue not in grp["grey"]:
                grp["grey"].append(ga.issue)
    return out


def item_text(it: dict) -> str:
    return f"{it.get('category', '')}: {it.get('name', '')}. " + "; ".join(map(str, it.get("evidence", [])))[:1200]


def group_text(gr: dict) -> str:
    return " ".join(gr["findings"])[:1500]


# --------------------------------------------------------------------------- embeddings (cached)
def embed_all(texts: dict[str, str], name: str, cap=0.5) -> dict[str, np.ndarray]:
    p = CH / f"emb_{name}.npz"
    have = dict(np.load(p)) if p.exists() else {}
    todo = [k for k in texts if k not in have]
    if todo:
        batches = [todo[i:i + 64] for i in range(0, len(todo), 64)]
        with llm.Budget(f"phase7-chunk-emb-{name}", cap=cap) as b:
            def f(bt):
                return bt, llm.embed("cohere-embed", [texts[k] for k in bt], budget=b, tag=f"chunkemb:{name}")
            with ThreadPoolExecutor(2) as ex:
                for bt, vecs in ex.map(f, batches):
                    for k, v in zip(bt, vecs):
                        v = np.asarray(v, dtype=np.float32)
                        have[k] = v / (np.linalg.norm(v) + 1e-9)
        CH.mkdir(parents=True, exist_ok=True)
        np.savez(p, **have)
    return have


# --------------------------------------------------------------------------- build index
def build():
    items, gtexts, G = {}, {}, {}
    for cid in E.ids():
        rec = json.loads((E.EXP / f"conditions/{cid}.json").read_text())
        for i, it in enumerate(rec["items"]):
            if isinstance(it, dict) and it.get("name"):
                items[f"{cid}#i{i}"] = item_text(it)
        G[cid] = groups(cid)
        for k, gr in G[cid].items():
            if k != "case":
                gtexts[f"{cid}#{k}"] = group_text(gr)
    IE = embed_all(items, "items")
    GE = embed_all(gtexts, "groups")
    chunks = []
    for cid in E.ids():
        gk = [k for k in G[cid] if k != "case"]
        gm = np.stack([GE[f"{cid}#{k}"] for k in gk]) if gk else None
        for key in [k for k in items if k.startswith(cid + "#")]:
            best, sim = None, 0.0
            if gm is not None:
                s = gm @ IE[key]
                j = int(np.argmax(s))
                best, sim = gk[j], float(s[j])
            gr = G[cid][best] if best and sim >= ALIGN_MIN else None
            chunks.append({"chunk_id": key, "case_id": cid, "item": items[key], "align_sim": round(sim, 3),
                           "label": gr["label"] if gr else "none", "rated": bool(gr and gr["rated"]),
                           "debits": gr["debits"] if gr else 0, "cap": gr["cap"] if gr else None, "fe": gr["fe"] if gr else 0,
                           "decline": bool(gr and gr["decline"]), "postpone": bool(gr and gr["postpone"]),
                           "grey": gr["grey"] if gr else [], "notes": gr["notes"] if gr else [],
                           "findings": gr["findings"] if gr else []})
    CH.mkdir(parents=True, exist_ok=True)
    (CH / "index.json").write_text(json.dumps({"chunks": chunks, "groups": {c: {k: {kk: v for kk, v in g.items() if kk != "notes"}
                                                                                  for k, g in G[c].items()} for c in G}}, ensure_ascii=False))
    return chunks, G, IE


def coarse(L) -> str:
    """Debit-scale band, ladder-agnostic: <=Std (no debits), Standard, T1-2, T3-4, T5-8, T9-16, Decline, Postpone."""
    if L["risk_class"] in ("Decline", "Postpone"):
        return L["risk_class"]
    if L["risk_class"] in ("Table", "Table Tobacco"):
        t = L["table"]
        return "T1-2" if t <= 2 else "T3-4" if t <= 4 else "T5-8" if t <= 8 else "T9-16"
    return "Standard" if L["net"] > 0 else "<=Std"


# --------------------------------------------------------------------------- offline score
def cosine_select(c, pc, PM, IE, k, seed):
    sims = PM @ IE[c["chunk_id"]]
    return [pc[j] for j in np.argsort(-sims)[:k]]


class RerankSelect:
    """Cohere Rerank 3.5 over the top-`cand` cosine candidates (one billed query per item). Cached per (split, item)."""

    def __init__(self, cand=30, cap=4.0):
        self.cand, self.cap = cand, cap
        self.path = CH / "rerank_cache.json"
        self.cache = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.budget = llm.Budget("phase7-rerank", cap=cap)
        self.n_new = 0

    def __call__(self, c, pc, PM, IE, k, seed):
        key = f"{seed}|{c['chunk_id']}"
        byid = {x["chunk_id"]: x for x in pc}
        if key not in self.cache:
            sims = PM @ IE[c["chunk_id"]]
            cands = [pc[j] for j in np.argsort(-sims)[:self.cand]]
            res = llm.rerank("cohere-rerank", c["item"][:1500], [x["item"][:1500] for x in cands], top_n=max(k, 10),
                             budget=self.budget, tag=f"rerank:{seed}")
            self.cache[key] = [cands[i]["chunk_id"] for i, _ in res]
            self.n_new += 1
            if self.n_new % 200 == 0:
                self.save()
        return [byid[x] for x in self.cache[key][:k]]

    def save(self):
        self.path.write_text(json.dumps(self.cache))


def score(chunks, G, IE, k=3, seeds=None, select=cosine_select, limit=None):
    lab = E.labels()
    by_case = defaultdict(list)
    for c in chunks:
        by_case[c["case_id"]].append(c)
    res = defaultdict(list)
    W = np.load(E.EXP / "emb/cohere_whole.npy")
    WP, WPID = {}, {}
    for seed, sp in E.splits().items():
        WPID[seed] = sp["pool"]
        WP[seed] = W[[E.ids().index(c) for c in sp["pool"]]]
    for seed, sp in E.splits().items():
        if seeds and seed not in seeds:
            continue
        pool = set(sp["pool"])
        pc = [c for c in chunks if c["case_id"] in pool]
        PM = np.stack([IE[c["chunk_id"]] for c in pc])
        for q in sp["test"][:limit]:
            L = lab[q]
            sl = E.slice_of(L)
            qch = by_case[q]
            rated = {k_: g for k_, g in G[q].items() if g["rated"] and k_ != "case"}
            aligned = defaultdict(list)
            for c in qch:
                if c["label"] in rated:
                    aligned[c["label"]].append(c)
            r = {}
            if rated:
                r["detect"] = len(aligned) / len(rated)
            pred_net, lab_hits, deb_hits = 0, [], []
            dec_votes = pp_votes = 0
            for c in qch:
                nb = select(c, pc, PM, IE, k, seed)
                d = int(np.median([x["debits"] for x in nb]))
                pred_net += d
                dec_votes += sum(x["decline"] for x in nb) >= 2
                pp_votes += sum(x["postpone"] for x in nb) >= 2
                if c["label"] in rated:
                    gq = rated[c["label"]]
                    lab_hits += [x["label"] == c["label"] for x in nb]
                    deb_hits += [bucket(x["debits"]) == bucket(gq["debits"]) for x in nb]
            if lab_hits:
                r["label@k"] = float(np.mean(lab_hits))
                r["debit@k"] = float(np.mean(deb_hits))
            if dec_votes:
                pband = "Decline"
            elif pp_votes:
                pband = "Postpone"
            elif pred_net <= 0:
                pband = "<=Std"
            elif pred_net <= 25:
                pband = "Standard"
            else:
                kind, t = table_from_net(pred_net, 50)
                pband = "Decline" if kind == "Decline" else E.band(f"Table {t}")
            gb = coarse(L)
            r["vote_coarse"] = float(pband == gb)
            # reference: whole-case Cohere cosine neighbours, majority coarse band (same scale)
            sims = WP[seed] @ W[E.ids().index(q)]
            nbc = [coarse(lab[WPID[seed][j]]) for j in np.argsort(-sims)[:k]]
            r["wholecase_vote_coarse"] = float(max(set(nbc), key=nbc.count) == gb)
            r["net_abs_err"] = abs(pred_net - L["net"]) if L["risk_class"] not in ("Decline", "Postpone") else None
            for m, v in r.items():
                if v is None:
                    continue
                res[(seed, "all", m)].append(v)
                res[(seed, sl, m)].append(v)
    agg = defaultdict(list)
    for (seed, sl, m), v in res.items():
        agg[(sl, m)].append(float(np.mean(v)))
    return {f"{sl}:{m}": (float(np.mean(v)), float(np.std(v))) for (sl, m), v in agg.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--rerank", action="store_true", help="paired comparison cosine vs cosine+Cohere Rerank on --seeds")
    ap.add_argument("--seeds", default="11")
    ap.add_argument("--limit", type=int, default=None, help="first N test cases (pilot)")
    ap.add_argument("--cap", type=float, default=4.0)
    a = ap.parse_args()
    chunks, G, IE = build()
    if a.rerank:
        seeds = set(a.seeds.split(","))
        rs = RerankSelect(cap=a.cap)
        try:
            sr = score(chunks, G, IE, a.k, seeds, rs, a.limit)
        finally:
            rs.save()
            rs.budget.__exit__(None, None, None)
        sc = score(chunks, G, IE, a.k, seeds, cosine_select, a.limit)
        L = [f"# Condition chunks: cosine vs cosine + Cohere Rerank 3.5 (top-30 candidates), k={a.k}, split(s) {a.seeds}"
             + (f", first {a.limit} test cases" if a.limit else ""), "", f"rerank queries billed this run: {rs.n_new} (${rs.budget.spent:.3f})", "",
             "| metric | slice | cosine | + rerank |", "|---|---|---|---|"]
        for m in ["label@k", "debit@k", "vote_coarse", "net_abs_err"]:
            for sl in ["all", "grey", "partial", "clean"]:
                kk = f"{sl}:{m}"
                if kk in sc:
                    L.append(f"| {m} | {sl} | {sc[kk][0]:.3f} | {sr[kk][0]:.3f} |")
        out = E.EXP / ("offline_chunks_rerank_pilot.md" if a.limit else "offline_chunks_rerank.md")
        out.write_text("\n".join(L) + "\n")
        print("\n".join(L))
        return
    al = [c for c in chunks if c["label"] != "none"]
    print(f"chunks {len(chunks)}; aligned to a golden group {len(al)}; rated {sum(c['rated'] for c in chunks)}")
    sc = score(chunks, G, IE, a.k)
    L = [f"# Offline condition-chunk retrieval (U2, Cohere cosine on extracted items, k={a.k}, 3 splits)", "",
         f"chunks {len(chunks)} (aligned {len(al)}, rated {sum(c['rated'] for c in chunks)}); align threshold {ALIGN_MIN}", "",
         "| metric | all | grey | partial | clean |", "|---|---|---|---|---|"]
    for m in ["detect", "label@k", "debit@k", "vote_coarse", "wholecase_vote_coarse", "net_abs_err"]:
        L.append(f"| {m} | " + " | ".join(f"{sc[f'{s}:{m}'][0]:.3f}±{sc[f'{s}:{m}'][1]:.3f}" if f"{s}:{m}" in sc else "-"
                                         for s in ["all", "grey", "partial", "clean"]) + " |")
    (E.EXP / "offline_chunks.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
