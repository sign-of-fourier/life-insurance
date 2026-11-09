"""Phase 4c (APS): rewrite template APS into realistic prose with Bedrock Nova, facts constrained + verified.

For each APS doc: prompt = style description + structured spec (compact) + template skeleton + MUST-INCLUDE list.
Verify: every must-include token present (normalized) and no un-specified drug names from rx_map. Retry once,
else keep the template rendering. Writes data/source/<case>/<doc_id>.txt and logs to qa/phase4c_aps_llm.jsonl.

Model routing (cost): Pro for handwritten_scan, hospital_discharge, epic_progress with >=3 problems or pages>=7;
Lite otherwise.  Run:
  python src/render_aps_llm.py --dry-run                # estimate all
  python src/render_aps_llm.py --pilot 10 --cap 0.25    # pilot
  python src/render_aps_llm.py --all --cap 2.0          # full (Budget per batch of 50)
"""
from __future__ import annotations

import argparse
import json
import random
import zlib
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import llm  # noqa: E402
from render import _ints, r_aps  # noqa: E402
from rules import load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VEND = load("vendors")
RXNAMES = set(load("rx_map")["drugs"]) | {b.split(" / ")[0].lower() for b, *_ in load("rx_map")["drugs"].values()}
LOG = ROOT / "qa/phase4c_aps_llm.jsonl"

SYSTEM = ("You produce realistic synthetic medical records (attending physician statements) for training data. "
          "You never invent diagnoses, medications, procedures, or test results beyond those provided. "
          "You may add clinically irrelevant routine content (normal exam findings, vital signs within normal ranges, "
          "unrelated minor complaints, administrative headers) to make the record realistic.")


def model_for(spec) -> str:
    st = spec["style"]
    if st in ("handwritten_scan", "hospital_discharge"):
        return "pro"
    if st == "epic_progress" and (len(spec["problems"]) >= 3 or spec["pages"] >= 7):
        return "pro"
    return "lite"


def must_include(spec) -> list[str]:
    out = []
    for p in spec["problems"]:
        for m in p["meds"]:
            out.append(m.split()[0].lower())
        d = p["details"]
        for k, v in d.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and k in ("a1c_avg", "egfr", "ef", "urine_protein", "fev1_pct", "ahi", "edss", "gleason", "cd4", "size_cm"):
                out.append(str(v))
        if d.get("stage"):
            out.append(f"stage {d['stage']}".lower())
    for s in spec["series"].values():
        out += [str(x["value"]) for x in s]
    if spec["noncompliant"]:
        out.append("non-compliant")
    for ro in spec["rule_outs"]:
        out.append("r/o")
    if spec["legacy_lab"]:
        out += ["fructosamine", str(spec["legacy_lab"]["results"]["fructosamine"])]
    return sorted(set(out))


def compact_spec(spec) -> dict:
    keep = {k: spec[k] for k in ("style", "last_visit", "stale", "series", "noncompliant", "rule_outs", "legacy_lab", "exercise_documented",
                                 "tobacco_documented", "alcohol_dpw", "family_history", "pages")}
    keep["provider"] = {k: spec["provider"][k] for k in ("name", "specialty", "practice")}
    keep["patient"] = spec["patient"]
    keep["problems"] = [{k: p[k] for k in ("dx", "onset", "status", "details", "meds")} for p in spec["problems"]]
    keep["visits"] = spec["visits"]
    return keep


def prompt_for(spec, skeleton, must) -> str:
    st = spec["style"]
    words = min(1800, 260 * spec["pages"])
    return f"""Write the full text of an attending physician statement (medical records sent to a life insurer).

STYLE: {st} - {VEND['aps_styles'][st]['desc']}
Target length: about {words} words. Plain text only (no markdown). Keep headers/page artifacts typical of this style.
{"Simulate a faxed handwritten note transcribed by OCR: terse, abbreviations, occasional [illegible] words, missing punctuation." if st == "handwritten_scan" else ""}
{"Repeat the same assessment paragraph across visits (copy-forward), as EHRs do." if spec.get("copy_forward") else ""}
{"This is a certified English translation of foreign records: metric units, day-first dates, translator notes." if st == "foreign_translated" else ""}

HARD RULES
- Use ONLY the diagnoses, medications, procedures and numeric results in DATA. Do not add any other medication names or diagnoses.
- Every item in MUST_INCLUDE must appear verbatim somewhere in the text.
- Visit dates, BP and weights come from DATA visits. You may add normal exam findings and unrelated minor complaints.
- Do not state any insurance or underwriting conclusion.
- Rewrite any attribute-like fragments (e.g. 'recovered years 4.8') into natural clinical language, keeping the numbers.

DATA (JSON):
{json.dumps(compact_spec(spec), default=str)}

MUST_INCLUDE: {json.dumps(must)}

TEMPLATE SKELETON (facts already placed; rewrite into a realistic record, do not just copy):
{skeleton[:3500]}
"""


def verify(text, must, spec) -> list[str]:
    low = text.lower()
    problems = [f"missing:{m}" for m in must if m.lower() not in low]
    allowed = {m.split()[0].lower() for p in spec["problems"] for m in p["meds"]}
    for w in set(re.findall(r"[a-z][a-z\-]{4,}", low)):
        if w in RXNAMES and w not in allowed and w not in ("aspirin", "insulin"):
            problems.append(f"extra_drug:{w}")
    return problems


def aps_docs(ids=None):
    for cdir in sorted((ROOT / "data/source").glob("C*")):
        if ids and cdir.name not in ids:
            continue
        ev = json.loads((cdir / "evidence.json").read_text())
        content = _ints(json.loads((cdir / "content.json").read_text())["docs"])
        for d in ev["docs"]:
            if d["doc_type"] == "aps":
                yield cdir, d, content[d["doc_id"]]


def estimate(docs):
    tot = {"lite": [0, 0, 0], "pro": [0, 0, 0]}
    for cdir, d, spec in docs:
        r = random.Random(zlib.crc32((d["doc_id"]).encode()))
        sk = r_aps(spec, r)
        p = prompt_for(spec, sk, must_include(spec))
        m = model_for(spec)
        out_tok = min(3500, int(260 * spec["pages"] * 1.4))
        tot[m][0] += 1; tot[m][1] += llm.est_tokens(SYSTEM + p); tot[m][2] += out_tok
    usd = sum(llm.cost(m, v[1], v[2]) for m, v in tot.items())
    return tot, usd


def run(docs, cap, label, workers=1):
    from concurrent.futures import ThreadPoolExecutor
    with llm.Budget(label, cap=cap) as b:
        if workers > 1:
            with ThreadPoolExecutor(workers) as ex:
                return sum(ex.map(lambda x: one(x, b), docs))
        return sum(one(x, b) for x in docs)


def one(x, b):
    cdir, d, spec = x
    if True:
        if True:
            r = random.Random(zlib.crc32((d["doc_id"]).encode()))
            sk = r_aps(spec, r)
            must = must_include(spec)
            m = model_for(spec)
            p = prompt_for(spec, sk, must)
            out_tok = min(3500, int(260 * spec["pages"] * 1.4))
            final, status, issues = sk, "template", []
            for attempt in range(2):
                try:
                    txt = llm.call(m, SYSTEM, p if attempt == 0 else p + f"\n\nYour previous draft had problems: {issues[:8]}. Fix them.",
                                   max_tokens=out_tok, temperature=0.8, budget=b, tag=f"aps:{d['doc_id']}")
                except llm.BudgetExceeded as e:
                    print("BUDGET STOP:", e)
                    return 0
                issues = verify(txt, must, spec)
                if not issues:
                    final, status = txt.strip(), f"llm:{m}:try{attempt + 1}"
                    break
            (ROOT / d["text_path"]).write_text(final + "\n")
            with llm.LOCK:
                with LOG.open("a") as f:
                    f.write(json.dumps({"doc_id": d["doc_id"], "style": spec["style"], "model": m, "status": status, "issues": issues[:10],
                                        "chars": len(final)}) + "\n")
            print(f"{d['doc_id']:12} {spec['style']:20} {m:4} {status:16} chars={len(final):5} issues={issues[:3]}", flush=True)
            return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ids", default="")
    ap.add_argument("--cap", type=float, default=0.25)
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args()
    docs = list(aps_docs(set(a.ids.split(",")) if a.ids else None))
    if a.dry_run:
        tot, usd = estimate(docs)
        print(f"{len(docs)} APS docs: " + ", ".join(f"{m}: {v[0]} docs, {v[1]:,} in / {v[2]:,} out tok" for m, v in tot.items()))
        print(f"estimated worst-case cost (full max_tokens): ${usd:.2f}")
        return
    if a.pilot:
        rng = random.Random(7)
        by_style = {}
        for x in docs:
            by_style.setdefault(x[2]["style"], []).append(x)
        pick = []
        while len(pick) < a.pilot:
            for st in sorted(by_style):
                if len(pick) < a.pilot and by_style[st]:
                    pick.append(by_style[st].pop(rng.randrange(len(by_style[st]))))
        tot, usd = estimate(pick)
        print(f"pilot {len(pick)} docs, worst-case ${usd:.3f}")
        run(pick, a.cap, "aps-pilot", a.workers)
    elif a.all:
        todo = [x for x in docs if not _done(x[1]["doc_id"])]
        for i in range(0, len(todo), 50):
            if run(todo[i:i + 50], a.cap, f"aps-batch-{i // 50:02d}", a.workers) < len(todo[i:i + 50]):
                print("batch incomplete (budget or errors) - stopping"); break


def _done(doc_id, _cache={}):
    if not _cache and LOG.exists():
        for l in LOG.read_text().splitlines():
            j = json.loads(l)
            _cache[j["doc_id"]] = j["status"]
    return _cache.get(doc_id, "").startswith("llm")


if __name__ == "__main__":
    main()
