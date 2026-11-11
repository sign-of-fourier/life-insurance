"""Phase 7 LLM runs: application (extracted JSON) -> decision + worksheet, with/without retrieved notes as few-shot.

A setup = examples source x guideline arm, e.g. "B0-G1" (no examples, full guideline), "S1-G2" (cosine whole-case
neighbours, gap guideline), "U2-G1" (condition chunks, full guideline).

Examples sources:
  B0  none                       B1  random k pool cases (control: any worked file vs a similar one)
  S1  cosine on Cohere v4 whole-case embedding (best offline whole-case space)
  S3  VAE (z=16) on Cohere v4 whole-case embedding
  S4C PLS on Cohere v4 (supervised on pool golden outcomes)
  S4R PLS on R2 own field:value TF-IDF tokens (best offline on grey / partial)
  O1  oracle neighbours (golden-trace similarity; upper bound)
  Example form (optional third part of the setup name): N1 noisy notes (default) · N2 clean golden write-up ·
  N3 noisy notes with rule ids and removed-rule wording stripped (gap ablation).
  U2  condition chunks: per extracted item of the test case, top-k pool chunks (cosine on Cohere item embeddings);
      each shows the past item's evidence and the note lines the underwriter wrote for it
Whole-case examples (B1/S1/S4/O1) = the neighbour's full noisy notes (data/notes/<case>.txt), which include the
underwriter's stated worksheet and decision. Never the test case's own notes / golden / truth.

Outputs cached in experiments/runs/<setup>/<case>.json (raw text + usage), so reruns and rescoring are free.

  python src/run_llm.py --setups B0-G1,S1-G1 --n 10 --dry-run     # prompt sizes + cost estimate, no calls
  python src/run_llm.py --setups B0-G1,S1-G1 --n 10 --cap 0.5      # run (pilot) and score
  python src/run_llm.py --score-only --setups ...                   # rescore cached outputs
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import exp_data as E  # noqa: E402
import llm  # noqa: E402
import score_worksheet as W  # noqa: E402

RUNS = E.EXP / "runs"
MODEL = "lite"
TOK_FACTOR = 1.4   # Bedrock-billed input tokens / llm.est_tokens on these prompts (measured on Pro + Lite runs)
K = 3
MAX_OUT = 4000
PROMPT_V = 1

SYSTEM = """You are a life insurance underwriter. Work the application file below under the company guideline and
produce the underwriting decision and the worksheet that supports it. Apply the guideline's rules and tables; cite
rule ids. Return ONLY one JSON object in the required format, no prose before or after it."""

FORMAT = f"""Required output format (JSON; comments explain fields, do not include them):
{W.OUTPUT_SCHEMA}
- items: every finding that changes the outcome (debits, credits, class cap, tobacco ladder, flat extra, postpone,
  decline). Leave out findings with no impact.
- decision.net_debits = sum of item debits minus credits. Table n = n x 25% extra.
- grey_areas: each judgement call you made where the evidence was incomplete or the rules allow a range."""


# --------------------------------------------------------------------------- context pieces
@lru_cache(maxsize=None)
def guideline(arm: str) -> str:
    return (E.EXP / f"guidelines/{arm}.md").read_text()


def notes_text(cid: str) -> str:
    return (E.ROOT / f"data/notes/{cid}.txt").read_text().strip()


RULE_RX = re.compile(r"\[[A-Za-z]{2,4}(?:-\d+(?:\.\d+)*)?\]|\b[A-Za-z]{2,4}-\d+(?:\.\d+)*\b")
GAP_WORDING = [(r"\(?\s*default\s*-\s*attributes not documented\s*\)?", ""), (r"\bdefault\s+profile\b", "profile"),
               (r"\bdefault\b", ""), (r"\bMIB not corroborated\b", "MIB"), (r"\bnot corroborated\b", ""),
               (r"\bleast severe\b", ""), (r"\bnext worse\b", ""), (r"\bworst documented\b", "")]


def strip_rules(text: str) -> str:
    """N3: example notes with every rule id and the removed rules' wording taken out (gap ablation)."""
    t = RULE_RX.sub("", text)
    for pat, rep in GAP_WORDING:
        t = re.sub(pat, rep, t, flags=re.I)
    return re.sub(r"[ \t]{2,}", " ", t)


def golden_text(cid: str) -> str:
    """N2: the clean golden write-up (exists only in the synthetic world; measures the cost of noisy notes)."""
    t = (E.ROOT / f"data/golden/{cid}.md").read_text()
    t = re.sub(r"\s*\[F\d{3}(?:, F\d{3})*\]", "", t)          # fact-id tags
    return re.sub(r"^# .*\n", "", t).strip()


def example_text(cid: str, form: str) -> str:
    if form.startswith("N4"):
        return rewrite_text(cid, form[2:])
    return {"N1": notes_text, "N2": golden_text, "N3": lambda c: strip_rules(notes_text(c))}[form](cid)


def rewrite_text(cid: str, model: str = "") -> str:
    """N4: noisy notes rewritten into the clean format (src/rewrite_notes.py; never sees the golden of this case).
    N4 = Nova Lite rewrites (experiments/rewrites/); N4<model>, e.g. N4sonnet = experiments/rewrites_<model>/."""
    d = "rewrites" if model in ("", "lite") else f"rewrites_{model}"
    return re.sub(r"^# .*\n", "", (E.EXP / f"{d}/{cid}.md").read_text()).strip()


LATENT = {"S3": ("vae", "cohere_whole"), "S4C": ("pls", "cohere_whole"), "S4R": ("pls", "r2")}


@lru_cache(maxsize=None)
def neighbours(space: str, seed: str) -> dict:
    """test case -> [pool case ids] for whole-case spaces (k=K)."""
    import retrieval as R
    sp = E.splits()[seed]
    test, pool = sp["test"], sp["pool"]
    if space == "B1":
        nb = R.random_nb(test, pool, K, int(seed))
    elif space == "S1":
        nb = R.neighbours(R.sp_cosine(R.rep_r1("cohere_whole"), pool), test, pool, K)
    elif space in LATENT:
        name, rep = LATENT[space]                       # identical calls to the offline run (retrieval.main)
        X = R.rep_r2(pool) if rep == "r2" else R.rep_r1(rep)
        nb = R.neighbours(R.SPACES[name](X, list(pool), seed=int(seed)), test, pool, K)
    elif space == "O1":
        nb = R.oracle(test, pool, K)
    else:
        raise ValueError(space)
    return {q: [p for p, _ in v] for q, v in nb.items()}


@lru_cache(maxsize=1)
def chunk_index():
    idx = json.loads((E.EXP / "chunks/index.json").read_text())["chunks"]
    IE = dict(np.load(E.EXP / "chunks/emb_items.npz"))
    return idx, IE


@lru_cache(maxsize=None)
def chunk_pool(seed: str):
    idx, IE = chunk_index()
    pool = set(E.splits()[seed]["pool"])
    pc = [c for c in idx if c["case_id"] in pool and c["notes"]]       # chunks with note lines to show
    return pc, np.stack([IE[c["chunk_id"]] for c in pc])


def chunk_examples(cid: str, seed: str) -> str:
    idx, IE = chunk_index()
    pc, PM = chunk_pool(seed)
    out = []
    for q in [c for c in idx if c["case_id"] == cid]:
        sims = PM @ IE[q["chunk_id"]]
        top = [pc[j] for j in np.argsort(-sims)[:K]]
        name = q["item"].split(". ")[0]
        block = [f"### Item in this application: {name}"]
        for i, c in enumerate(top, 1):
            block.append(f"Past case {i} - item: {c['item'][:400]}\n  notes: " + " | ".join(c["notes"]))
        out.append("\n".join(block))
    return "\n\n".join(out)


def examples(space: str, cid: str, seed: str, form: str = "N1") -> str:
    if space == "B0":
        return ""
    if space == "U2":
        body = chunk_examples(cid, seed)
        return ("## Notes from past cases with similar items\nFor each risk item found in this application, the notes "
                "this office's underwriters wrote on similar items in past files.\n\n" + body) if body else ""
    nb = neighbours(space, seed)[cid]
    body = "\n\n".join(f"### Past case {i}\n{example_text(p, form)}" for i, p in enumerate(nb, 1))
    return "## Notes from similar past cases\nUnderwriter notes and worksheets from past files worked by this office.\n\n" + body


def model_of(setup: str) -> str:
    """'S1-G1' -> lite (default); 'S1-G1@pro' -> pro (outputs cached under runs/S1-G1@pro/)."""
    return setup.split("@", 1)[1] if "@" in setup else MODEL


def prompt(setup: str, cid: str, seed: str) -> str:
    space, arm, *rest = setup.split("@")[0].split("-")              # e.g. S1-G1 (noisy notes) / S1-G1-N2 (golden) / S1-G2-N3 (stripped)
    form = rest[0] if rest else "N1"
    parts = ["# Company underwriting guideline\n\n" + guideline(arm)]
    ex = examples(space, cid, seed, form)
    if ex:
        parts.append(ex)
    parts.append("# Application file (extracted documents)\n\n" + E.case_text(cid))
    parts.append(FORMAT)
    return "\n\n---\n\n".join(parts)


# --------------------------------------------------------------------------- run / score
def out_path(setup: str, cid: str, seed: str = "11") -> Path:
    return RUNS / (setup if seed == "11" else f"{setup}@s{seed}") / f"{cid}.json"


def pilot_cases(seed: str, n: int) -> list[str]:
    """Stratified subset of the seed's test split, deterministic (grey / partial / clean in proportion)."""
    lab = E.labels()
    test = E.splits()[seed]["test"]
    by = defaultdict(list)
    for c in test:
        by[E.slice_of(lab[c])].append(c)
    want = {"grey": round(n * 0.4), "partial": round(n * 0.3)}
    want["clean"] = n - want["grey"] - want["partial"]
    rng = np.random.default_rng(int(seed))
    out = []
    for s, m in want.items():
        v = sorted(by[s])
        out += [v[i] for i in sorted(rng.choice(len(v), min(m, len(v)), replace=False))]
    return sorted(out)


def ok(text: str) -> bool:
    o = W.parse(text)
    return bool(o and isinstance(o.get("decision"), dict))


def run_one(setup, cid, seed, budget):
    p = out_path(setup, cid, seed)
    if p.exists():
        rec = json.loads(p.read_text())
        if rec.get("prompt_v") == PROMPT_V and rec.get("seed") == seed and (ok(rec["output"]) or "retried" in rec):
            return rec
    pr = prompt(setup, cid, seed)
    text = llm.call(model_of(setup), SYSTEM, pr, max_tokens=MAX_OUT, temperature=0.0, budget=budget, tag=f"run:{setup}:{cid}")
    retried = False
    if not ok(text):                                  # one retry (same policy for every setup): loops / runaway lists
        text = llm.call(model_of(setup), SYSTEM, pr, max_tokens=MAX_OUT, temperature=0.3, budget=budget, tag=f"run:{setup}:{cid}:retry")
        retried = True
    rec = {"retried": retried, "case_id": cid, "setup": setup, "seed": seed, "prompt_v": PROMPT_V, "model": model_of(setup),
           "prompt_tokens_est": llm.est_tokens(SYSTEM + pr), "output": text}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    return rec


def summarize(setups, cases, out_md: Path, seed: str = "11"):
    lab = E.labels()
    keys = ["parsed", "decision", "coarse", "derived_coarse", "ladder", "net_abs_err", "derived_net_err", "item_recall", "item_precision", "rule_acc",
            "debit_close", "arith_ok", "class_follows", "fe_recall", "grey_recall", "overrate_partial", "worksheet"]
    lines = [f"# LLM runs ({MODEL}, k={K}, prompt v{PROMPT_V}) - {len(cases)} cases", "",
             "| setup | slice | n | " + " | ".join(keys) + " |", "|---|---|---|" + "---|" * len(keys)]
    allrows = {}
    for s in setups:
        rows = []
        for c in cases:
            p = out_path(s, c, seed)
            if p.exists():
                r = W.score(c, json.loads(p.read_text())["output"])
                r["slice"] = E.slice_of(lab[c])
                rows.append(r)
        allrows[s] = rows
        for sl in ["all", "grey", "partial", "clean"]:
            rr = [r for r in rows if sl == "all" or r["slice"] == sl]
            if not rr:
                continue
            a = W.aggregate(rr, keys)
            lines.append(f"| {s} | {sl} | {len(rr)} | " + " | ".join(f"{a[k]:.2f}" if k in a else "-" for k in keys) + " |")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return allrows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setups", required=True)
    ap.add_argument("--seed", default="11")
    ap.add_argument("--n", type=int, default=10, help="stratified subset of the test split (0 = all 200)")
    ap.add_argument("--cap", type=float, default=0.5)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--score-only", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    setups = a.setups.split(",")
    cases = pilot_cases(a.seed, a.n) if a.n else E.splits()[a.seed]["test"]
    out_md = Path(a.out) if a.out else E.EXP / f"runs_n{len(cases)}_s{a.seed}.md"
    if not a.score_only:
        def cached(s, c):
            p = out_path(s, c, a.seed)
            if not p.exists():
                return False
            rec = json.loads(p.read_text())
            return rec.get("seed") == a.seed and (ok(rec["output"]) or "retried" in rec)
        todo = [(s, c) for s in setups for c in cases if not cached(s, c)]
        toks = {s: [llm.est_tokens(SYSTEM + prompt(s, c, a.seed)) for c in cases] for s in setups}
        for s in setups:
            print(f"{s}: prompt ~{int(np.mean(toks[s])):,} tok mean, max {max(toks[s]):,}")
        est = sum(llm.cost(model_of(s), int(TOK_FACTOR * llm.est_tokens(SYSTEM + prompt(s, c, a.seed))), 1500) for s, c in todo)
        print(f"{len(todo)} calls to make (of {len(setups) * len(cases)}), est ${est:.3f} (1.5K out each); "
              f"spent so far ${llm.global_spent():.2f}")
        if a.dry_run:
            return
        with llm.Budget(f"phase7-run-{a.setups}", cap=a.cap) as b:
            with ThreadPoolExecutor(a.workers) as ex:
                list(ex.map(lambda sc: run_one(sc[0], sc[1], a.seed, b), todo))
            print(f"spent this batch ${b.spent:.3f} over {b.calls} calls")
    summarize(setups, cases, out_md, a.seed)


if __name__ == "__main__":
    main()
