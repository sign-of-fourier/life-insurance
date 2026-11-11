"""Clean-notes generator, option A (prompt-only rewrite; see SCOPING_NOTES_GENERATOR.md).

For each past case: Nova Lite rewrites the case's noisy UW notes into the clean write-up format, given the guideline,
the case's application, and 2 worked examples (noisy notes -> clean write-up) from a small "expert-reviewed" sample.
- Expert sample: 150 cases drawn (fixed seed) from the 510 cases that are in no test split; it is the only place
  golden write-ups are used, as rewrite examples. Examples = the 2 cosine-nearest expert cases (never the case itself).
- The rewrite never sees the golden of the case it rewrites.
Output: experiments/rewrites/<cid>.md; used as example form N4 in run_llm (e.g. S1-G1-N4).

  python src/rewrite_notes.py --space S1 --seed 11 [--n 5] [--cap 1.0] [--model lite] [--dry-run]
  python src/rewrite_notes.py --space S1 --seed 11 --export experiments/rewrite_prompts_S1_s11.jsonl   # run elsewhere
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import exp_data as E  # noqa: E402
import llm  # noqa: E402
import run_llm as R  # noqa: E402

OUT = E.EXP / "rewrites"          # lite; other models write to rewrites_<model>/ (form N4<model> in run_llm)
N_EXPERT, N_SHOT, MAX_OUT, MODEL = 150, 2, 4000, "lite"

SYSTEM = """You are a senior life insurance underwriter cleaning up a colleague's file notes. The notes are terse,
full of shorthand and sometimes skip steps or contain slips. Rewrite them as a clean, complete write-up of how the
file was worked, in exactly the format of the examples: applicant line, decision, worksheet table (item, rule, effect),
then how the file was worked, step by step. Use the application and the guideline to fill gaps and correct slips;
where the notes and the evidence disagree, follow the evidence and the guideline. Return only the write-up."""


@lru_cache(maxsize=1)
def expert_sample() -> list[str]:
    in_test = set().union(*[set(s["test"]) for s in E.splits().values()])
    free = sorted(c for c in E.labels() if c not in in_test)
    return sorted(np.random.default_rng(7).choice(free, N_EXPERT, replace=False).tolist())


@lru_cache(maxsize=1)
def _emb():
    import retrieval as RT
    return RT.l2(RT.rep_r1("cohere_whole")), RT.IDX


def shots(cid: str) -> list[str]:
    X, idx = _emb()
    ex = [c for c in expert_sample() if c != cid]
    sims = X[[idx[c] for c in ex]] @ X[idx[cid]]
    sims = np.asarray(sims).ravel()
    return [ex[i] for i in np.argsort(-sims)[:N_SHOT]]


def prompt(cid: str) -> str:
    parts = ["# Company underwriting guideline\n\n" + R.guideline("G1")]
    for i, e in enumerate(shots(cid), 1):
        parts.append(f"# Worked example {i}\n\n## Colleague's notes\n{R.notes_text(e)}\n\n## Clean write-up\n{R.golden_text(e)}")
    parts.append("# File to clean up\n\n## Application file (extracted documents)\n" + E.case_text(cid)
                 + "\n\n## Colleague's notes\n" + R.notes_text(cid) + "\n\n## Clean write-up\n")
    return "\n\n---\n\n".join(parts)


def looping(text: str) -> bool:
    from collections import Counter
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return bool(lines) and Counter(lines).most_common(1)[0][1] > 15


def collapse(text: str) -> str:
    """Drop runs of identical consecutive lines (keeps the first) - safety net after a looping retry."""
    out = []
    for l in text.splitlines():
        if not (out and l.strip() and l.strip() == out[-1].strip()):
            out.append(l)
    return "\n".join(out)


def ok(text: str) -> bool:
    return bool(text) and "Decision" in text and "|" in text and len(text) < 30000 and not looping(text)


def out_dir(model: str) -> Path:
    return OUT if model == "lite" else E.EXP / f"rewrites_{model}"


def rewrite(cid: str, budget, model: str = MODEL) -> str:
    p = out_dir(model) / f"{cid}.md"
    if p.exists():
        return p.read_text()
    pr = prompt(cid)
    text = llm.call(model, SYSTEM, pr, max_tokens=MAX_OUT, temperature=0.0, budget=budget, tag=f"rewrite:{cid}")
    if not ok(text):
        text = llm.call(model, SYSTEM, pr, max_tokens=MAX_OUT, temperature=0.3, budget=budget, tag=f"rewrite:{cid}:retry")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(collapse(text).strip() + "\n")
    return text


def targets(space: str, seed: str, n: int) -> list[str]:
    nb = R.neighbours(space, seed)
    cases = R.pilot_cases(seed, n) if n else E.splits()[seed]["test"]
    return sorted({p for c in cases for p in nb[c]})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--space", default="S1")
    ap.add_argument("--seed", default="11")
    ap.add_argument("--n", type=int, default=0, help="only neighbours of n stratified test cases (0 = all 200)")
    ap.add_argument("--cap", type=float, default=1.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--model", default=MODEL, help="key in llm.PRICES (lite, pro, or one added there)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--export", default="", help="write prompts as JSONL to this path and exit (no LLM calls)")
    a = ap.parse_args()
    if a.export:                       # prompts for running the rewrite elsewhere (no Bedrock needed)
        out = Path(a.export)
        with out.open("w") as f:
            for c in targets(a.space, a.seed, a.n):
                f.write(json.dumps({"case_id": c, "system": SYSTEM, "prompt": prompt(c), "max_tokens": MAX_OUT,
                                    "temperature": 0.0, "save_as": f"experiments/rewrites_<model>/{c}.md"}) + "\n")
        print(f"wrote {out}")
        return
    todo = [c for c in targets(a.space, a.seed, a.n) if not (out_dir(a.model) / f"{c}.md").exists()]
    est = sum(llm.cost(a.model, int(R.TOK_FACTOR * llm.est_tokens(SYSTEM + prompt(c))), 2000) for c in todo)
    print(f"{len(todo)} rewrites to make, est ${est:.3f}; spent so far ${llm.global_spent():.2f}")
    (E.EXP / "rewrites_expert_sample.json").write_text(json.dumps(expert_sample()))
    if a.dry_run:
        return
    with llm.Budget(f"phase7-rewrite-{a.space}" + ("" if a.model == "lite" else f"-{a.model}"), cap=a.cap) as b:
        with ThreadPoolExecutor(a.workers) as ex:
            list(ex.map(lambda c: rewrite(c, b, a.model), todo))
        print(f"spent this batch ${b.spent:.3f} over {b.calls} calls")


if __name__ == "__main__":
    main()
