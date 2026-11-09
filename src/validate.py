"""Cross-layer integrity checks. Returns a list of error strings (empty = OK)."""
from __future__ import annotations

from schemas import (Decision, EvidenceBundle, ExtractedDoc, Golden, Notes, TERMINAL_OUTCOMES)


def check_evidence(ev: EvidenceBundle) -> list[str]:
    errs = []
    fact_ids = [f.fact_id for f in ev.facts]
    if len(fact_ids) != len(set(fact_ids)):
        errs.append("duplicate fact_ids")
    doc_ids = {d.doc_id for d in ev.docs}
    fset = set(fact_ids)
    for f in ev.facts:
        if f.doc_id not in doc_ids:
            errs.append(f"{f.fact_id}: unknown doc {f.doc_id}")
        if not f.fact_id.startswith(ev.case_id):
            errs.append(f"{f.fact_id}: wrong case prefix")
    for d in ev.docs:
        for fid in d.fact_ids:
            if fid not in fset:
                errs.append(f"{d.doc_id}: references missing fact {fid}")
        if d.ordered_at and d.received_at < d.ordered_at:
            errs.append(f"{d.doc_id}: received before ordered")
    return errs


def check_extracted(ev: EvidenceBundle, xs: list[ExtractedDoc]) -> list[str]:
    errs, fset, dset = [], {f.fact_id for f in ev.facts}, {d.doc_id for d in ev.docs}
    for x in xs:
        if x.doc_id not in dset:
            errs.append(f"extracted {x.doc_id}: no source doc")
        for l in x.losses:
            if l.fact_id and l.fact_id not in fset:
                errs.append(f"extracted {x.doc_id}: loss cites missing fact {l.fact_id}")
    return errs


def check_decision(d: Decision) -> list[str]:
    errs = []
    tabled = d.risk_class in ("Table", "Table Tobacco")
    if tabled and not 1 <= d.table <= 16:
        errs.append(f"{d.risk_class} requires table 1..16, got {d.table}")
    if not tabled and d.table:
        errs.append(f"table={d.table} set on non-table class {d.risk_class}")
    if d.ladder == "tobacco" and d.risk_class in ("Elite", "Preferred Plus", "Preferred", "Standard Plus", "Standard", "Table"):
        errs.append(f"tobacco ladder but non-tobacco class {d.risk_class}")
    if d.ladder == "non_tobacco" and d.risk_class in ("Preferred Tobacco", "Standard Tobacco", "Table Tobacco"):
        errs.append(f"non-tobacco ladder but tobacco class {d.risk_class}")
    if d.risk_class == "Postpone" and not d.postpone_months:
        errs.append("Postpone without postpone_months")
    if d.risk_class == "Decline" and not d.decline_reason:
        errs.append("Decline without reason")
    if d.risk_class in TERMINAL_OUTCOMES and (d.flat_extras or d.riders and any(r.status == "approved" for r in d.riders)):
        errs.append("terminal outcome with flat extras / approved riders")
    return errs


def check_golden(ev: EvidenceBundle, g: Golden) -> list[str]:
    errs, fset = [], {f.fact_id for f in ev.facts}
    steps = [s.step for s in g.trace]
    if steps != list(range(1, len(steps) + 1)):
        errs.append("trace steps not 1..n")
    for s in g.trace:
        for fid in s.fact_ids:
            if fid not in fset:
                errs.append(f"step {s.step}: missing fact {fid}")
    if any(g.trace[i].at > g.trace[i + 1].at for i in range(len(g.trace) - 1)):
        errs.append("trace timestamps not monotonic")
    cited = {fid for s in g.trace for fid in s.fact_ids}
    uncited_relevant = [f.fact_id for f in ev.facts if f.relevant and f.fact_id not in cited]
    if uncited_relevant:
        errs.append(f"relevant facts never addressed in trace: {uncited_relevant}")
    net = sum(s.effect.debits - s.effect.credits for s in g.trace)
    if net != g.decision.net_debits:
        errs.append(f"net_debits {g.decision.net_debits} != trace sum {net}")
    errs += check_decision(g.decision)
    return errs


def check_notes(ev: EvidenceBundle, g: Golden, n: Notes) -> list[str]:
    errs, fset, steps = [], {f.fact_id for f in ev.facts}, {s.step for s in g.trace}
    for c in n.corruptions:
        if c.fact_id and c.fact_id not in fset:
            errs.append(f"corruption cites missing fact {c.fact_id}")
        if c.step and c.step not in steps:
            errs.append(f"corruption cites missing step {c.step}")
    wrong = any(c.kind in ("wrong_final", "grey_divergence") for c in n.corruptions)
    if n.stated_decision.strip() != g.decision.label() and not wrong:
        errs.append(f"stated '{n.stated_decision}' != golden '{g.decision.label()}' with no wrong_final/grey_divergence logged")
    return errs
