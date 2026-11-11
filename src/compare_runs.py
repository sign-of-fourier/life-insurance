"""Paired comparisons between LLM-run setups (same cases, per-case differences, bootstrap 95% CI).

  python src/compare_runs.py --n 0 --pairs S1-G1:B0-G1,B1-G1:B0-G1 [--seed 11] [--out experiments/runs_paired.md]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import exp_data as E  # noqa: E402
import run_llm as R  # noqa: E402
import score_worksheet as W  # noqa: E402

KEYS = ["decision", "coarse", "derived_coarse", "worksheet", "item_recall", "item_precision", "debit_close",
        "rule_acc", "arith_ok", "class_follows", "fe_recall", "grey_recall", "overrate_partial", "net_abs_err"]


def scores(setup, cases, seed="11"):
    out = {}
    for c in cases:
        p = R.out_path(setup, c, seed)
        if p.exists():
            out[c] = W.score(c, json.loads(p.read_text())["output"])
    return out


def diff(A, B, cases, k, rng):
    d = np.array([A[c][k] - B[c][k] for c in cases if c in A and c in B and k in A[c] and k in B[c]])
    if len(d) < 5:
        return None
    bs = rng.choice(d, (4000, len(d))).mean(axis=1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return d.mean(), lo, hi, len(d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--seed", default="11")
    ap.add_argument("--n", type=int, default=0)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    cases = R.pilot_cases(a.seed, a.n) if a.n else E.splits()[a.seed]["test"]
    lab = E.labels()
    sl = {c: E.slice_of(lab[c]) for c in cases}
    rng = np.random.default_rng(0)
    cache = {}
    lines = [f"# Paired differences A - B (seed {a.seed}, {len(cases)} cases; mean [95% bootstrap CI], * = CI excludes 0)", ""]
    for pair in a.pairs.split(","):
        x, y = pair.split(":")
        for s in (x, y):
            cache.setdefault(s, scores(s, cases, a.seed))
        A, B = cache[x], cache[y]
        lines += [f"## {x} vs {y}", "", "| metric | all | grey | partial | clean |", "|---|---|---|---|---|"]
        for k in KEYS:
            row = []
            for s in ["all", "grey", "partial", "clean"]:
                cs = [c for c in cases if s == "all" or sl[c] == s]
                r = diff(A, B, cs, k, rng)
                row.append("-" if r is None else f"{r[0]:+.3f} [{r[1]:+.2f}, {r[2]:+.2f}]{'*' if r[1] > 0 or r[2] < 0 else ''} n={r[3]}")
            lines.append(f"| {k} | " + " | ".join(row) + " |")
        lines.append("")
    text = "\n".join(lines)
    out = Path(a.out) if a.out else E.EXP / f"runs_paired_n{len(cases)}_s{a.seed}.md"
    out.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
