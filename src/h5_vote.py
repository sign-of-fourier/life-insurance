"""H5: does the LLM add anything over a free vote of the same neighbours?

For each split and each whole-case space, the vote = majority of the 3 neighbours' golden outcomes (ties -> the
nearest neighbour's). Scored on the same scale as the LLM: exact decision label and class band (coarse_of).
Compared per case with the LLM run that saw the SAME neighbours' notes (and with B0, no notes). Unparsed LLM
outputs count as wrong. No LLM calls.

  python src/h5_vote.py   -> experiments/h5_vote.md
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import exp_data as E  # noqa: E402
import run_llm as R  # noqa: E402
import score_worksheet as W  # noqa: E402

SEEDS = {"11": ["B1", "S1", "S3", "S4C", "S4R", "O1"], "22": ["B1", "S1", "S4R", "O1"], "33": ["B1", "S1", "S4R", "O1"]}


def gold(c):
    d = W.golden(c).decision
    return d.label(), W.coarse_of(d.risk_class, d.table or 0)


def vote(ns, i):
    cnt = Counter(gold(p)[i] for p in ns)
    top = max(cnt.values())
    return next(gold(p)[i] for p in ns if cnt[gold(p)[i]] == top)   # tie -> nearest


def llm(setup, c, seed):
    p = R.out_path(setup, c, seed)
    if not p.exists():
        return None
    s = W.score(c, json.loads(p.read_text())["output"])
    return s.get("decision", 0.0), s.get("coarse", 0.0), s


def ci(d, rng):
    d = np.asarray(d, float)
    bs = rng.choice(d, (4000, len(d))).mean(axis=1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return f"{d.mean():+.3f} [{lo:+.2f}, {hi:+.2f}]{'*' if lo > 0 or hi < 0 else ''}"


def main():
    rng = np.random.default_rng(0)
    lab = E.labels()
    L = ["# H5 - LLM vs free neighbour vote (same 3 neighbours, 200 test cases per split)", "",
         "vote = majority golden outcome of the 3 neighbours (tie -> nearest). LLM = Nova Lite with those neighbours' "
         "noisy notes, full guideline. agree = LLM band equals the vote band. * = 95% paired bootstrap CI excludes 0.", ""]
    for seed, spaces in SEEDS.items():
        test = E.splits()[seed]["test"]
        b0 = {c: llm("B0-G1", c, seed) for c in test}
        L += [f"## Seed {seed}", "",
              "| space | vote exact | LLM exact | vote band | LLM band | B0 band | LLM-vote band (all) | grey | partial | clean | agree | LLM right when it disagrees |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for sp in spaces:
            nb = R.neighbours(sp, seed)
            rows = []
            for c in test:
                r = llm(f"{sp}-G1", c, seed)
                if r is None:
                    continue
                g_lab, g_band = gold(c)
                v_lab, v_band = vote(nb[c], 0), vote(nb[c], 1)
                rows.append(dict(c=c, sl=E.slice_of(lab[c]), ve=float(v_lab == g_lab), vb=float(v_band == g_band),
                                 le=r[0], lb=r[1], b0=(b0[c][1] if b0.get(c) else 0.0)))
            # agreement needs the LLM's own band: recompute from output
            agree, right_dis = [], []
            for x in rows:
                out = W.parse(json.loads(R.out_path(f"{sp}-G1", x["c"], seed).read_text())["output"])
                d = (out or {}).get("decision") if isinstance(out, dict) else None
                mb = W.coarse_of(str(d.get("risk_class")), W.num(d.get("table"))) if isinstance(d, dict) else None
                vb = vote(nb[x["c"]], 1)
                agree.append(float(mb == vb))
                if mb != vb:
                    right_dis.append(x["lb"])
            def m(k, sl=None):
                return np.mean([x[k] for x in rows if sl is None or x["sl"] == sl])
            diffs = {sl: [x["lb"] - x["vb"] for x in rows if sl is None or x["sl"] == sl] for sl in [None, "grey", "partial", "clean"]}
            L.append(f"| {sp} | {m('ve'):.2f} | {m('le'):.2f} | {m('vb'):.2f} | {m('lb'):.2f} | {m('b0'):.2f} | "
                     + " | ".join(ci(diffs[s], rng) for s in [None, "grey", "partial", "clean"])
                     + f" | {np.mean(agree):.2f} | {np.mean(right_dis) if right_dis else float('nan'):.2f} (n={len(right_dis)}) |")
        L.append("")
    text = "\n".join(L)
    (E.EXP / "h5_vote.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
