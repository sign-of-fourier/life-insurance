"""Phase 5: render data/golden/<case>.json -> data/golden/<case>.md (clean, templated; no LLM, no new facts).

Sections: decision summary; CLS-4 worksheet (10 steps); evidence walk-through by stage with fact ids and rule ids;
grey areas with the alternatives a competent underwriter could defend; evidence reviewed and dismissed.
Run: python src/render_golden.py [--ids C0001,...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schemas import Golden  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STAGE_TITLE = {"application": "Application (Part 1 / Part 2)", "third_party": "Third-party data (Rx, MIB, MVR)",
               "requirements": "Requirements ordered", "labs": "Exam and laboratory results", "aps": "Medical records and questionnaires",
               "final": "Final worksheet"}


def fe_txt(f):
    return f"FE ${f.per_thousand:g}/1000 " + (f"for {f.years} yrs" if f.years else "permanent") + f" ({f.reason})"


def effect_txt(e):
    out = []
    if e.debits:
        out.append(f"+{e.debits}")
    if e.credits:
        out.append(f"-{e.credits}")
    if e.class_cap:
        out.append(f"best {e.class_cap}")
    if e.ladder:
        out.append("tobacco ladder")
    if e.flat_extra:
        out.append(fe_txt(e.flat_extra))
    if e.postpone_months:
        out.append(f"postpone {e.postpone_months} mo")
    if e.decline:
        out.append("DECLINE")
    if e.order_requirement:
        out.append(f"order {e.order_requirement}")
    if e.rider_action:
        out.append(f"rider {e.rider_action.code} {e.rider_action.status}")
    return ", ".join(out) or "no impact"


def render(g: Golden, content: dict) -> str:
    p1 = next(c for c in content["docs"].values() if isinstance(c, dict) and "dob" in c and "signed" in c)
    d = g.decision
    L = [f"# {g.case_id} - golden underwriting decision", ""]
    L += [f"**Applicant:** {p1['sex']}, DOB {p1['dob']}, signed {p1['signed']} - {p1['occupation']} - {p1['product']} ${p1['face']:,}"
          + (f" - riders requested: {', '.join(p1['riders'])}" if p1["riders"] else ""), ""]
    L += [f"**Decision: {d.label()}**" + (f" (reconsider in {d.postpone_months} months)" if d.postpone_months else ""), ""]
    bits = [f"ladder: {d.ladder.value if hasattr(d.ladder, 'value') else d.ladder}", f"net debits: {d.net_debits:+d}"]
    if d.preliminary_class:
        bits.append(f"indicated from application alone: {d.preliminary_class}")
    L += ["- " + "; ".join(bits)]
    if d.flat_extras:
        L += ["- flat extras: " + "; ".join(fe_txt(f) for f in d.flat_extras)]
    if d.approved_face_amount:
        L += [f"- amount: counter-offer ${d.approved_face_amount:,}"]
    if d.exclusions:
        L += ["- exclusions: " + "; ".join(d.exclusions)]
    if d.riders:
        L += ["- riders: " + "; ".join(f"{r.code} {r.status}" + (f" ({r.reason})" if r.status != "approved" else "") for r in d.riders)]
    if d.decline_reason:
        L += [f"- reason: {d.decline_reason}"]
    L += [""]
    # worksheet
    rated = [s for s in g.trace if str(getattr(s.stage, "value", s.stage)) != "requirements" and (s.effect.debits or s.effect.class_cap or s.effect.flat_extra or
                                                                       s.effect.postpone_months or s.effect.decline or s.effect.ladder)]
    L += ["## Worksheet (CLS-4)", "", "| # | Item | Rule | Effect |", "|---|---|---|---|"]
    for s in rated:
        L.append(f"| {s.step} | {s.finding.replace('|', '/')} | {s.rule_id} | {effect_txt(s.effect)} |")
    cr = [s for s in g.trace if s.effect.credits]
    for s in cr:
        if s not in rated:
            L.append(f"| {s.step} | {s.finding.replace('|', '/')} | {s.rule_id} | -{s.effect.credits} |")
    fin = [s for s in g.trace if str(getattr(s.stage, "value", s.stage)) == "final" and s not in rated and s not in cr and not s.effect.rider_action]
    for s in fin:
        L.append(f"| {s.step} | {s.finding.replace('|', '/')} | {s.rule_id} | {effect_txt(s.effect)} |")
    L += [""]
    # walk-through
    L += ["## How the file was worked", ""]
    cur = None
    for s in g.trace:
        if s.effect.no_impact and len(s.fact_ids) > 3:
            continue          # bulk dismissals listed below
        st = str(getattr(s.stage, "value", s.stage))
        if st != cur:
            L += ["", f"### {STAGE_TITLE[st]} - {s.at:%Y-%m-%d}", ""]
            cur = st
        cite = f" [{', '.join(f.split('-')[1] for f in s.fact_ids)}]" if s.fact_ids else ""
        eff = effect_txt(s.effect)
        L.append(f"{s.step}. {s.finding} *({s.rule_id}; {eff})*{cite}")
    if g.grey_areas:
        L += ["", "## Grey areas (documented discretion)", ""]
        for ga in g.grey_areas:
            L.append(f"- **{ga.issue}** ({', '.join(ga.rule_ids)}): chose *{ga.chosen}*; defensible alternatives: {', '.join(ga.alternatives)}. {ga.rationale}")
    bulk = [s for s in g.trace if s.effect.no_impact and len(s.fact_ids) > 3]
    if bulk:
        L += ["", "## Reviewed, no impact", ""]
        for s in bulk:
            L.append(f"- {s.finding} ({s.rule_id}; {len(s.fact_ids)} items)")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    a = ap.parse_args()
    files = sorted((ROOT / "data/golden").glob("C*.json"))
    if a.ids:
        files = [f for f in files if f.stem in set(a.ids.split(","))]
    for f in files:
        g = Golden.model_validate_json(f.read_text())
        content = json.loads((ROOT / f"data/source/{g.case_id}/content.json").read_text())
        (ROOT / f"data/golden/{g.case_id}.md").write_text(render(g, content))
    print(f"rendered {len(files)} golden narratives")


if __name__ == "__main__":
    main()
