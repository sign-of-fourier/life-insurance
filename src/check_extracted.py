"""Phase 4 final gate: extracted JSON integrity + loss rates + APS LLM verification summary."""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from schemas import EvidenceBundle, ExtractedDoc
from validate import check_extracted
ROOT = Path(__file__).resolve().parents[1]
errs, st, by_type = [], Counter(), defaultdict(Counter)
for f in sorted((ROOT / "data/extracted").glob("C*.json")):
    ev = EvidenceBundle.model_validate_json((ROOT / "data/source" / f.stem / "evidence.json").read_text())
    xs = [ExtractedDoc.model_validate(x) for x in json.loads(f.read_text())]
    errs += [f"{f.stem}: {e}" for e in check_extracted(ev, xs)]
    if {x.doc_id for x in xs} != {d.doc_id for d in ev.docs}:
        errs.append(f"{f.stem}: extracted docs != source docs")
    rel = {x.fact_id for x in ev.facts if x.relevant}
    lost = {l.fact_id for x in xs for l in x.losses if l.fact_id and l.kind in ("dropped", "truncated_page")}
    st["relevant"] += len(rel); st["relevant_lost"] += len(rel & lost)
    for x in xs:
        by_type[x.doc_type]["docs"] += 1
        for l in x.losses:
            by_type[x.doc_type][l.kind] += 1
    st["cases"] += 1
print(f"cases {st['cases']}; relevant facts {st['relevant']}, dropped/truncated in extraction {st['relevant_lost']} "
      f"({100 * st['relevant_lost'] / max(1, st['relevant']):.1f}%)")
for t, c in sorted(by_type.items()):
    n = c.pop("docs")
    print(f"  {t:10} docs {n:5}  losses/doc {sum(c.values()) / n:5.2f}  " + ", ".join(f"{k} {v}" for k, v in c.most_common(5)))
log = ROOT / "qa/phase4c_aps_llm.jsonl"
if log.exists():
    rows = [json.loads(l) for l in log.read_text().splitlines()]
    s = Counter(r["status"].split(":try")[0] for r in rows)
    print("APS rendering:", dict(s), "| retries:", sum(r["status"].endswith("try2") for r in rows))
for e in errs[:15]: print("ERR", e)
print("PHASE 4 GATE:", "PASS" if not errs else f"FAIL ({len(errs)})")
