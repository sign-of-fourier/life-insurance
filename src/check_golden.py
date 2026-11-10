"""Phase 5 gate: golden decisions are valid, deterministic, and their divergence from the design target is explained.

- validate.check_golden on every case (trace integrity, all relevant facts cited, net == trace sum, decision sanity)
- every trace rule_id exists in guidelines.md
- determinism: re-run a sample and compare JSON byte-for-byte
- target vs engine: outcome-band agreement + mismatch categories (reads truth/design ONLY here, for QA)
Run: python src/check_golden.py [--sample 25]  -> qa/phase5_golden.md
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from engine import RULE_IDS, run_case  # noqa: E402
from schemas import EvidenceBundle, Golden  # noqa: E402
from validate import check_golden  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def band(label: str) -> str:
    if label.startswith("Table Tobacco"):
        t = int(label.split()[2])
        return "TT1-4" if t <= 4 else "TT5-16"
    if label.startswith("Table"):
        t = int(label.split()[1])
        return "T1-2" if t <= 2 else "T3-4" if t <= 4 else "T5-8" if t <= 8 else "T9-16"
    return label


TGT = {"Table 1-2": "T1-2", "Table 3-4": "T3-4", "Table 5-8": "T5-8", "Table 9-16": "T9-16", "Table Tobacco 1-4": "TT1-4",
       "Table Tobacco 5-16": "TT5-16"}


def explain(t, g: Golden, design) -> list[str]:
    """Heuristic categories for a target/engine mismatch (QA only: uses truth)."""
    cats = []
    items = design["items"]
    if any(i["disclosure"] == "omitted_untraceable" or (i["disclosure"] == "omitted" and i["kind"] == "med") for i in items):
        if any(c["details"].get("untraceable") for c in t["conditions"]):
            cats.append("untraceable condition (no evidence)")
    if design["tobacco_disclosure"] in ("omitted", "minimized") and g.decision.ladder != design["ladder"]:
        cats.append("hidden tobacco not provable")
    log = " ".join(design.get("_extra", {}).get("log", []))
    if "cad modifier" in log:
        cats.append("CAD modifier (EF/angina/vessels)")
    steps = " ".join(s.finding for s in g.trace)
    if "non-compliance" in steps:
        cats.append("APS non-compliance +25")
    if "Credit -" in steps:
        cats.append("CLS-6 credits")
    if "insulin True +25" in steps or "smoker True +50" in steps:
        cats.append("chapter add-on modifiers")
    if "MISREP" in steps or "misrepresentation" in steps:
        cats.append("misrepresentation finding")
    if "stale" in steps:
        cats.append("stale APS")
    if "default - attributes not documented" in steps:
        cats.append("no APS detail -> default profile")
    if "RX-2.4" in [s.rule_id for s in g.trace]:
        cats.append("Rx-only condition (RX-2.4)")
    if "unexplained" in steps:
        cats.append("unexplained lab finding")
    if "counter-offer" in steps:
        cats.append("FIN counter-offer")
    if "fluids Preferred Plus" in steps and design["target"] == "Elite":
        cats.append("accelerated path: Elite requires fluids (REQ-3)")
    if any(s.rule_id in ("FIN-2.4", "CLS-8.8") for s in g.trace) and design["target"] != "Decline":
        cats.append("FIN over-insurance decline (incl. in-force coverage)")
    if "fails Preferred on" in steps and "nicotine Standard Plus" in steps:
        cats.append("nicotine row counts toward CLS-5.2")
    if "age 70+ one column more lenient" in steps or ("build Standard Plus" in steps and t["person"]["age"] >= 70):
        cats.append("BLD-1.8 age 70+ build leniency")
    if "normal stress 12mo True -25" in steps:
        cats.append("CV-1.2 LDL/stress modifier")
    if "fluids Preferred Plus" in steps and design["matrix"]["fails"]:
        cats.append("accelerated path: matrix rows not measured")
    if "relapse" in steps:
        cats.append("ALC relapse row by documented abstinence")
    if "CLS-8.6" in [s.rule_id for s in g.trace]:
        cats.append("signed outside US (CLS-8.6)")
    if any(r == "mvr" for r, _ in design["matrix"]["fails"]) and "mvr Standard" not in steps:
        cats.append("generator: MVR row realized better than intended")
    if any(i["key"] == "nm_financial" for i in items) and not any(s.rule_id.startswith(("FIN-2.2", "FIN-2.4")) for s in g.trace):
        cats.append("generator: FIN intent not realized (income floor)")
    if "TOB-4.2" in [s.rule_id for s in g.trace]:
        cats.append("undisclosed nicotine caught by cotinine (TOB-4.2)")
    if "GEN-2.3" in [s.rule_id for s in g.trace]:
        cats.append("GEN-2.3 multiple misrepresentation")
    return cats or ["unexplained"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=25)
    a = ap.parse_args()
    gold = sorted((ROOT / "data/golden").glob("C*.json"))
    errs, agree, conf, cats, bad_rules = [], 0, Counter(), defaultdict(list), Counter()
    rows = []
    for gp in gold:
        cid = gp.stem
        g = Golden.model_validate_json(gp.read_text())
        ev = EvidenceBundle.model_validate_json((ROOT / f"data/source/{cid}/evidence.json").read_text())
        e = check_golden(ev, g)
        if e:
            errs.append(f"{cid}: {e[:3]}")
        for s in g.trace:
            if s.rule_id not in RULE_IDS:
                bad_rules[s.rule_id] += 1
        t = json.loads((ROOT / f"data/truth/{cid}.json").read_text())
        d = t["design"]
        tb = TGT.get(d["target"], d["target"])
        eb = band(g.decision.label())
        conf[(tb, eb)] += 1
        if tb == eb:
            agree += 1
        else:
            for c in explain(t, g, d):
                cats[c].append(cid)
            rows.append((cid, tb, eb, explain(t, g, d)))
    random.seed(5)
    det = []
    for cid in random.sample([p.stem for p in gold], min(a.sample, len(gold))):
        if run_case(cid).model_dump_json(indent=1) != (ROOT / f"data/golden/{cid}.json").read_text():
            det.append(cid)
    n = len(gold)
    targets = sorted({k[0] for k in conf})
    outs = sorted({k[1] for k in conf})
    lines = ["# Phase 5 golden check", "", f"cases {n}; validation errors {len(errs)}; unknown rule ids {dict(bad_rules)}; "
             f"non-deterministic {det}", "", f"target band == engine band: {agree}/{n} ({agree / n:.0%})", "",
             "## Mismatch categories (a case can have several)", ""]
    for c, ids in sorted(cats.items(), key=lambda x: -len(x[1])):
        lines.append(f"- {c}: {len(ids)}  e.g. {', '.join(ids[:6])}")
    lines += ["", "## Engine outcome distribution", ""]
    oc = Counter(k[1] for k in conf.elements())
    lines += [f"- {k}: {v}" for k, v in sorted(oc.items(), key=lambda x: -x[1])]
    lines += ["", "## Confusion (target -> engine, off-diagonal only)", ""]
    for tb in targets:
        off = {o: conf[(tb, o)] for o in outs if conf[(tb, o)] and o != tb}
        if off:
            lines.append(f"- {tb} ({sum(conf[(tb, o)] for o in outs)}): " + ", ".join(f"{o} {v}" for o, v in sorted(off.items(), key=lambda x: -x[1])))
    lines += ["", "## Validation errors", "", *[f"- {e}" for e in errs[:40]], "", "## Mismatches", ""]
    lines += [f"- {cid}: {tb} -> {eb}  [{'; '.join(c)}]" for cid, tb, eb, c in rows]
    (ROOT / "qa/phase5_golden.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:40]))
    ok = not errs and not bad_rules and not det
    print("PHASE 5 GATE (integrity):", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
