"""Phase 4b gate: integrity + content checks over data/source/*/evidence.json."""
import json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from schemas import EvidenceBundle, Truth
from validate import check_evidence
ROOT = Path(__file__).resolve().parents[1]
errs, st = [], Counter()
for d in sorted((ROOT / "data/source").glob("C*")):
    ev = EvidenceBundle.model_validate_json((d / "evidence.json").read_text())
    t = Truth.model_validate_json((ROOT / "data/truth" / f"{d.name}.json").read_text())
    meta = json.loads((d / "content.json").read_text())["meta"]
    errs += [f"{d.name}: {e}" for e in check_evidence(ev)]
    types = Counter(x.doc_type for x in ev.docs)
    # omitted, traceable conditions must be visible outside the application
    for i, c in enumerate(t.conditions):
        if c.irrelevant or c.disclosure != "omitted":
            continue
        ref = f"conditions[{i}]"
        outside = [f for f in ev.facts if f.truth_ref == ref and not f.kind.startswith("app_")]
        if c.details.get("untraceable"):
            st["untraceable"] += 1
            if [f for f in outside if f.kind in ("rx_fill", "mib_code", "aps_finding")]:
                errs.append(f"{d.name}: untraceable {c.condition_key} has record trace")
        else:
            st["omitted_traceable"] += 1
            if not outside:
                errs.append(f"{d.name}: omitted {c.condition_key} has no trace")
            st["trace_sources:" + "+".join(sorted({f.kind for f in outside}))] += 1
    # tobacco ladder -> some tobacco evidence (admission, cotinine+, cessation Rx)
    if t.design["ladder"] == "tobacco":
        tob = [f for f in ev.facts if (f.key == "tobacco" and f.value != "No") or f.key == "varenicline"
               or (f.key in ("cotinine_urine",) and f.value >= 200) or (f.key == "cotinine_saliva" and f.value >= 30)]
        if not tob:
            if t.design["tobacco_disclosure"] == "omitted" and t.design["tobacco"] in ("cig_quit_lt12", "cessation_rx_only"):
                st["hidden_smoker"] += 1     # quit < 12 mo, lied, cotinine already negative: undetectable by design
            else:
                errs.append(f"{d.name}: tobacco ladder with no tobacco evidence")
    # accel path: no fluids
    if meta["requirements"] and list(meta["requirements"]) == ["ACCEL"] and (types["lab_blood"] or types["paramed"]):
        errs.append(f"{d.name}: accel but fluids ordered")
    st["accel"] += list(meta["requirements"]) == ["ACCEL"] or (not types["paramed"] and not types["lab_blood"])
    st["cases"] += 1
    st["facts"] += len(ev.facts); st["relevant"] += sum(f.relevant for f in ev.facts)
    for f in ev.facts:
        if f.note:
            st["note:" + f.note.split(":")[0]] += 1
print(f"cases {st['cases']}  facts/case {st['facts']/st['cases']:.1f}  relevant {100*st['relevant']/st['facts']:.0f}%  accel(no fluids) {st['accel']}")
print(f"omitted traceable {st['omitted_traceable']}  untraceable {st['untraceable']}  hidden smokers {st['hidden_smoker']}")
print("trace sources:", {k[14:]: v for k, v in st.most_common() if k.startswith("trace_sources:")})
print("fact notes:", {k[5:]: v for k, v in st.most_common() if k.startswith("note:")})
for e in errs[:20]: print("ERR", e)
print(f"PHASE 4b GATE: {'PASS' if not errs else 'FAIL'} ({len(errs)} errors)")
