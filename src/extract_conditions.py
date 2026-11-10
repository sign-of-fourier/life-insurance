"""Phase 7 (U2 chunking): LLM lists the conditions / risk items an application implies, from its extracted JSON only.

Same step for every case (pool and test), so query-side and index-side chunks are represented the same way.
No guideline, no ratings, no decisions: extraction only. Verified: valid JSON, known category, every drug name the
output mentions occurs in the input (rx_map vocabulary). Retry once with the problems listed.
Output: experiments/conditions/<case>.json ; usage tag cond:<case>.

  python src/extract_conditions.py --dry-run
  python src/extract_conditions.py --pilot 10 --cap 0.05
  python src/extract_conditions.py --all --cap 1.0 --workers 4
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import exp_data as E  # noqa: E402
import llm  # noqa: E402
from rules import load  # noqa: E402

OUT = E.EXP / "conditions"
MODEL = "lite"
RXN = sorted({d.lower() for d in load("rx_map")["drugs"]} |
             {b.split(" / ")[0].lower() for b, *_ in load("rx_map")["drugs"].values()}, key=len, reverse=True)
CATS = ["cardiovascular", "diabetes_glucose", "cancer", "mental_health", "respiratory", "digestive_liver", "kidney",
        "neurological", "endocrine", "musculoskeletal", "blood", "immune_infectious", "womens_health", "older_age_frailty",
        "alcohol", "drugs", "tobacco_nicotine", "build", "blood_pressure", "lipids", "family_history", "driving",
        "aviation_avocation", "occupation", "travel_residency", "financial", "other"]

SYSTEM = ("You read life-insurance application files for a synthetic research dataset and list the risk items the "
          "evidence implies. You only extract; you never rate, classify, or decide. You never add facts that are not in "
          "the file. You return JSON only.")


def prompt(cid: str) -> str:
    return ("Below is one applicant's file: machine-extracted JSON from several vendors (application parts 1 and 2, "
            "prescription history, MIB codes, motor vehicle report, paramedical exam, labs, EKG, questionnaires, attending "
            "physician statements). Extraction is noisy: fields may be garbled, renamed or missing.\n\n"
            "List every risk item the evidence implies, one entry per distinct condition or risk factor, including items "
            "that are NOT disclosed on the application but are implied by prescriptions, MIB codes, labs, MVR, or physician "
            "records. Include non-medical items when present (tobacco/nicotine, build, blood pressure, lipids, family "
            "history, driving record, aviation/hazardous avocations, occupation, foreign travel/residency, finances).\n\n"
            "Return JSON: {\"items\": [{\"name\": \"<specific name as the evidence states it>\", \"category\": "
            f"\"<one of {', '.join(CATS)}>\", \"evidence\": [\"<doc type>: <short detail with values/dates/codes as written>\", ...], "
            "\"disclosed_on_application\": true|false|null, \"physician_records_in_file\": true|false, "
            "\"evidence_gaps\": \"<what is missing or unclear, or empty>\"}]}\n"
            "One entry per condition: group related findings (e.g. several abnormal lipid values, or a drug plus the lab it "
            "treats) under the single condition they suggest. Keep each evidence detail under 25 words. Skip items with nothing notable (e.g. normal labs) unless they are "
            "one of the non-medical items above.\n\nFILE:\n" + E.case_text(cid))


ALIAS = {"liver": "digestive_liver", "digestive": "digestive_liver", "gi": "digestive_liver", "diabetes": "diabetes_glucose",
         "glucose": "diabetes_glucose", "psychiatric": "mental_health", "renal": "kidney", "hematology": "blood",
         "infectious": "immune_infectious", "immune": "immune_infectious", "avocation": "aviation_avocation",
         "aviation": "aviation_avocation", "travel": "travel_residency", "residency": "travel_residency", "tobacco": "tobacco_nicotine",
         "nicotine": "tobacco_nicotine", "substance_use": "drugs", "women's_health": "womens_health", "gynecologic": "womens_health"}


def normalize(out: dict) -> list[str]:
    """Map near-miss categories to the allowed list (unknown -> other). Returns notes on what was remapped."""
    notes = []
    for it in out.get("items", []) if isinstance(out.get("items"), list) else []:
        if isinstance(it, dict) and it.get("category") not in CATS:
            c = str(it.get("category", "")).lower().strip().replace(" ", "_")
            new = c if c in CATS else ALIAS.get(c, "other")
            notes.append(f"{it.get('category')}->{new}")
            it["category"] = new
    return notes


def verify(out: dict, src: str) -> list[str]:
    iss = []
    items = out.get("items")
    if not isinstance(items, list) or not items:
        return ["no items"]
    low = src.lower()
    for i, it in enumerate(items):
        if not isinstance(it, dict) or not it.get("name"):
            iss.append(f"item {i}: missing name")
            continue
        if it.get("category") not in CATS:
            iss.append(f"item {i}: bad category {it.get('category')!r}")
        txt = (it.get("name", "") + " " + " ".join(map(str, it.get("evidence", [])))).lower()
        for d in RXN:
            if len(d) > 4 and re.search(rf"\b{re.escape(d)}\b", txt) and d not in low:
                iss.append(f"item {i}: drug '{d}' not in the file")
    return iss


def one(cid: str, b) -> dict | None:
    p = OUT / f"{cid}.json"
    if p.exists():
        return None
    src = E.case_text(cid)
    pr, issues = prompt(cid), []
    for attempt in range(2):
        q = pr if attempt == 0 else pr + f"\n\nYour previous answer had problems: {issues[:8]}. Fix them."
        raw = llm.call(MODEL, SYSTEM, q, max_tokens=4000, temperature=0.2, budget=b, tag=f"cond:{cid}")
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            out = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            out = {}
        remap = normalize(out)
        issues = verify(out, src)
        if not issues:
            break
    rec = {"case_id": cid, "items": out.get("items", []), "issues": issues, "attempts": attempt + 1, "category_remaps": remap}
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cap", type=float, default=0.05)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    ids = E.ids()
    if a.pilot:
        ids = random.Random(7).sample(ids, a.pilot)
    if a.dry_run:
        tin = sum(llm.est_tokens(SYSTEM + prompt(c)) for c in ids)
        print(f"{len(ids)} cases ~{tin} in tokens; est ${llm.cost(MODEL, tin, 600 * len(ids)):.3f} "
              f"(+ retries; worst x2 ${2 * llm.cost(MODEL, tin, 600 * len(ids)):.3f})")
        return
    if not (a.pilot or a.all):
        ap.error("--pilot N | --all | --dry-run")
    with llm.Budget(f"phase7-conditions-{len(ids)}", cap=a.cap) as b:
        with ThreadPoolExecutor(a.workers) as ex:
            recs = [r for r in ex.map(lambda c: one(c, b), ids) if r]
    bad = [r["case_id"] for r in recs if r["issues"]]
    print(f"done {len(recs)} new; with unresolved issues {len(bad)} {bad[:10]}; items/case "
          f"{sum(len(r['items']) for r in recs) / max(1, len(recs)):.1f}; batch ${b.spent:.4f}")


if __name__ == "__main__":
    main()
