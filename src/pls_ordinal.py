"""Offline test: PLS with the decision as ONE ordinal target (equal steps vs spacing calibrated from the pool).

V0  current pls_targets (class rank 0-10 with all tables = 6, plus table, decline, postpone columns)
V1  ordinal score, equal steps: Elite < PP < P < SP < Std < T1 < ... < T16 < Postpone < Decline (tobacco classes
    mapped to their non-tobacco rung; the ladder stays a separate column)
V2  ordinal score, calibrated (optimal scoring): alternate PLS fit <-> monotone (isotonic) refit of the rung values
    to the PLS-predicted score, so order is fixed but spacing is learned from the pool only
Other columns (chapter debits, net, FE, tobacco ladder, GRY flags) are identical across variants.

  python src/pls_ordinal.py [--reps cohere_whole,r2]   -> experiments/offline_pls_ordinal.md
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.cross_decomposition import PLSRegression
from sklearn.isotonic import IsotonicRegression

sys.path.insert(0, str(Path(__file__).parent))
import exp_data as E  # noqa: E402
import retrieval as R  # noqa: E402

PREF = {"Elite": 0, "Preferred Plus": 1, "Preferred": 2, "Preferred Tobacco": 2, "Standard Plus": 3, "Standard": 4,
        "Standard Tobacco": 4}


def rung(L) -> int:
    rc = L["risk_class"]
    if rc in PREF:
        return PREF[rc]
    if rc in ("Table", "Table Tobacco"):
        return 4 + int(L["table"])          # T1 = 5 ... T16 = 20
    return 21 if rc == "Postpone" else 22   # Decline


def other_cols(cids):
    chs = sorted({ch for c in R.CIDS for ch in R.LAB[c]["chapter_debits"]})
    grys = sorted({g for c in R.CIDS for g in R.LAB[c]["grey"]})
    rows = []
    for c in cids:
        L = R.LAB[c]
        rows.append([L["chapter_debits"].get(ch, 0) for ch in chs] + [max(-50, min(L["net"], 450)), L["fe"], L["fe_perm"],
                    L["ladder"] == "tobacco"] + [g in L["grey"] for g in grys])
    return np.asarray(rows, dtype=float)


def fit_space(D, P, Y):
    keep = Y.std(0) > 0
    m = PLSRegression(n_components=16, scale=True).fit(D[P], Y[:, keep])
    return m, keep


def space(X, pool, variant, seed, iters=8, log=None):
    D = R.dense_base(X, pool, n=512, seed=seed)
    P = [R.IDX[c] for c in pool]
    if variant == "V0":
        m, _ = fit_space(D, P, R.pls_targets(pool))
        return R.l2(m.transform(D))
    O = other_cols(pool)
    r = np.array([rung(R.LAB[c]) for c in pool], dtype=float)
    y = r.copy()
    for _ in range(iters if variant == "V2" else 1):
        Y = np.column_stack([y, O])
        m, keep = fit_space(D, P, Y)
        if variant != "V2":
            break
        pred = m.predict(D[P])[:, 0]                                   # predicted ordinal score (first target column)
        iso = IsotonicRegression(increasing=True).fit(r, pred)         # monotone in rung order, spacing from data
        y_new = iso.predict(r)
        y = (y_new - y_new.mean()) / (y_new.std() + 1e-9) * r.std() + r.mean()   # keep scale comparable to V1
    if log is not None and variant == "V2":
        vals = {int(k): float(v) for k, v in zip(r, y)}
        log.append(vals)
    return R.l2(m.transform(D))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", default="cohere_whole,r2")
    a = ap.parse_args()
    res = defaultdict(list)
    spacing = defaultdict(list)
    for seed, s in E.splits().items():
        test, pool = s["test"], s["pool"]
        for rep in a.reps.split(","):
            X = R.rep_r2(pool) if rep == "r2" else R.rep_r1(rep)
            for v in ["V0", "V1", "V2"]:
                S = space(X, pool, v, int(seed), log=spacing[rep])
                res[(v, rep)].append(R.score(R.neighbours(S, test, pool, 3)))
                print(seed, rep, v, "done", flush=True)
    cols = ["all:coverage", "grey:grey", "partial:partial", "all:band", "all:vote", "grey:vote", "partial:vote", "clean:vote"]
    L = ["# PLS with an ordinal decision target (k=3, mean ± sd over 3 splits)", "",
         "| variant | repr | " + " | ".join(cols) + " |", "|---|---|" + "---|" * len(cols)]
    for (v, rep), lst in sorted(res.items(), key=lambda x: (x[0][1], x[0][0])):
        L.append(f"| {v} | {rep} | " + " | ".join(f"{np.mean([d[c] for d in lst]):.3f}±{np.std([d[c] for d in lst]):.3f}" for c in cols) + " |")
    names = {0: "E", 1: "PP", 2: "P", 3: "SP", 4: "Std", **{4 + t: f"T{t}" for t in range(1, 17)}, 21: "PPN", 22: "DEC"}
    for rep, logs in spacing.items():
        L += ["", f"Calibrated rung values (V2, {rep}, mean over splits; V1 = equal steps 0..22):", ""]
        ks = sorted(set().union(*logs))
        L.append(" ".join(f"{names[k]}={np.mean([lg[k] for lg in logs if k in lg]):.1f}" for k in ks))
    (E.EXP / "offline_pls_ordinal.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
