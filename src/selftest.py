"""Phase 0 gate: build one hand-written case through every layer, round-trip it through JSON,
run integrity checks, verify the checks catch planted errors, and verify the budget guard
refuses an over-cap call without touching the network.

Rule ids are real ids from reference/guidelines.md and are checked to exist.
Run: python src/selftest.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schemas import *  # noqa: E402,F403
from validate import check_evidence, check_extracted, check_golden, check_notes  # noqa: E402
import llm  # noqa: E402

C = "EX0001"
dt = lambda s: datetime.fromisoformat(s)  # noqa: E731


def build():
    truth = Truth(
        case_id=C, seed=1, app_date=date(2026, 10, 1), design={"complexity": "moderate", "disclosure": "minimized"},
        person=Person(first_name="Dale", last_name="Rourke", sex="M", dob=date(1980, 3, 2), age=46, address_state="OH",
                      occupation="HVAC technician", occupation_class="3A", annual_income=78000, net_worth=210000,
                      marital_status="married", dependents=2),
        coverage=Coverage(face_amount=500000, product="Term 20", riders_requested=["WP"]),
        height_in=70, weight_lb=208, bp_systolic=136, bp_diastolic=86, pulse=78,
        tobacco=[TobaccoUse(product="cigarette", status="current", frequency="1/2 ppd", start=date(1998, 1, 1),
                            disclosure="minimized")],
        conditions=[Condition(condition_key="hypertension", label="Essential hypertension", onset=date(2021, 5, 1),
                              status="controlled", severity="mild",
                              meds=[MedUse(drug="lisinopril", dose="10 mg", start=date(2021, 5, 10), indication="HTN")]),
                    Condition(condition_key="seasonal_allergy", label="Allergic rhinitis", onset=date(2015, 4, 1),
                              status="controlled", severity="mild", irrelevant=True,
                              meds=[MedUse(drug="fluticasone nasal", dose="50 mcg", start=date(2015, 4, 1))])],
        true_labs={"cotinine_urine": 1500, "tc": 212, "hdl": 41},
    )
    F = lambda n: f"{C}-F{n:03d}"  # noqa: E731
    D = lambda n: f"{C}-D{n:02d}"  # noqa: E731
    facts = [
        EvidenceFact(fact_id=F(1), doc_id=D(1), kind="app_answer", key="tobacco_12mo", value="No - quit 2024",
                     truth_ref="tobacco[0]", note="minimized"),
        EvidenceFact(fact_id=F(2), doc_id=D(1), kind="app_answer", key="htn_treated", value="Yes, lisinopril",
                     truth_ref="conditions[0]"),
        EvidenceFact(fact_id=F(3), doc_id=D(2), kind="rx_fill", key="varenicline", value="0.5 mg x56", as_of=date(2026, 6, 3),
                     truth_ref="tobacco[0]", note="contradicts app tobacco answer"),
        EvidenceFact(fact_id=F(4), doc_id=D(2), kind="rx_fill", key="fluticasone nasal", value="50 mcg",
                     as_of=date(2026, 8, 1), relevant=False, truth_ref="conditions[1]"),
        EvidenceFact(fact_id=F(5), doc_id=D(3), kind="lab_value", key="cotinine_urine", value=1500, unit="ng/mL",
                     as_of=date(2026, 10, 12), truth_ref="true_labs.cotinine_urine"),
        EvidenceFact(fact_id=F(6), doc_id=D(4), kind="paramed", key="build", value="5'10\" 208 lb", as_of=date(2026, 10, 12)),
        EvidenceFact(fact_id=F(7), doc_id=D(4), kind="paramed", key="bp", value="136/86", as_of=date(2026, 10, 12)),
    ]
    docs = [
        SourceDoc(doc_id=D(1), case_id=C, doc_type="app_part1", vendor_id="app_v1", received_at=dt("2026-10-01T09:00"),
                  text_path=f"data/source/{C}/{D(1)}.txt", fact_ids=[F(1), F(2)]),
        SourceDoc(doc_id=D(2), case_id=C, doc_type="rx", vendor_id="rx_vendorA", ordered_at=dt("2026-10-01T09:05"),
                  received_at=dt("2026-10-01T09:20"), order_reason="auto", text_path=f"data/source/{C}/{D(2)}.txt",
                  fact_ids=[F(3), F(4)]),
        SourceDoc(doc_id=D(3), case_id=C, doc_type="lab_urine", vendor_id="lab_B", ordered_at=dt("2026-10-02T10:00"),
                  received_at=dt("2026-10-14T16:00"), order_reason="REQ-1 age/amount", text_path=f"data/source/{C}/{D(3)}.txt",
                  fact_ids=[F(5)]),
        SourceDoc(doc_id=D(4), case_id=C, doc_type="paramed", vendor_id="pm_A", ordered_at=dt("2026-10-02T10:00"),
                  received_at=dt("2026-10-13T12:00"), text_path=f"data/source/{C}/{D(4)}.txt", fact_ids=[F(6), F(7)]),
    ]
    ev = EvidenceBundle(case_id=C, facts=facts, docs=docs)
    xs = [ExtractedDoc(doc_id=D(3), case_id=C, doc_type="lab_urine", vendor_schema="lab_B.v2",
                       payload={"panel": "UA/NIC", "results": [{"test": "COTININE", "val": "15OO", "units": None}]},
                       losses=[ExtractionLoss(fact_id=F(5), kind="misread_digit", original="1500", extracted="15OO"),
                               ExtractionLoss(fact_id=F(5), kind="unit_lost", original="ng/mL")])]
    trace = [
        TraceStep(step=1, stage="application", at=dt("2026-10-01T09:30"), fact_ids=[F(1)], rule_id="TOB-1",
                  finding="App states no tobacco in 12 months; quit 2024.", effect=Effect()),
        TraceStep(step=2, stage="third_party", at=dt("2026-10-01T09:35"), fact_ids=[F(3)], rule_id="TOB-5",
                  finding="Varenicline filled 06/2026 contradicts quit date; treat as tobacco use within 12 months pending cotinine.",
                  effect=Effect(class_cap="Standard Tobacco", ladder="tobacco")),
        TraceStep(step=3, stage="third_party", at=dt("2026-10-01T09:36"), fact_ids=[F(4)], rule_id="MISC-1",
                  finding="Fluticasone nasal for allergies; no impact.", effect=Effect(no_impact=True)),
        TraceStep(step=4, stage="application", at=dt("2026-10-01T09:40"), fact_ids=[F(2)], rule_id="HTN-5",
                  finding="Treated HTN, single agent; final debits depend on paramed BP.", effect=Effect()),
        TraceStep(step=5, stage="labs", at=dt("2026-10-14T16:30"), fact_ids=[F(5)], rule_id="TOB-4.2",
                  finding="Cotinine 1500 ng/mL positive; confirms tobacco ladder, best class Standard Tobacco.",
                  effect=Effect(class_cap="Standard Tobacco", ladder="tobacco")),
        TraceStep(step=6, stage="labs", at=dt("2026-10-14T16:35"), fact_ids=[F(6)], rule_id="BLD-1",
                  finding="Build 5'10\" 208 lb (BMI 29.8) within Standard on build chart.", effect=Effect()),
        TraceStep(step=7, stage="labs", at=dt("2026-10-14T16:36"), fact_ids=[F(7)], rule_id="HTN-1",
                  finding="Treated BP 136/86, controlled on one agent: +25.", effect=Effect(debits=25)),
        TraceStep(step=8, stage="final", at=dt("2026-10-14T16:45"), fact_ids=[], rule_id="CLS-3.3",
                  finding="Net +25 on tobacco ladder = Standard Tobacco. WP approved.",
                  effect=Effect(rider_action=RiderAction(code="WP", status="approved", reason="Std Tobacco eligible"))),
    ]
    golden = Golden(case_id=C, trace=trace,
                    decision=Decision(ladder="tobacco", risk_class="Standard Tobacco", net_debits=25,
                                      preliminary_class="Standard Plus",
                                      riders=[RiderAction(code="WP", status="approved", reason="Std Tobacco eligible")]),
                    requirements_ordered=[D(3), D(4)])
    notes = Notes(case_id=C, persona_id="uw_07",
                  observations=[NoteEntry(at=dt("2026-10-01T09:40"), text="46M 500k T20. app sez quit cigs '24. Rx - chantix 6/26?? ord u/a + PM"),
                                NoteEntry(at=dt("2026-10-14T16:40"), text="cot 1500 pos. 5.10.208 ok. bp 136/86 on lisin")],
                  worksheet_format="debit_list", worksheet="HTN tx ctrl +25\nbld 0\ncot+ -> STD TOB\nnet +25  STD TOB  WP ok",
                  stated_decision="Standard Tobacco",
                  corruptions=[Corruption(kind="abbrev_t2", fact_id=F(6), detail="build written as 5.10.208"),
                               Corruption(kind="omitted_step", step=3, detail="fluticasone dismissal not written")])
    return truth, ev, xs, golden, notes


def roundtrip(obj):
    cls = type(obj)
    back = cls.model_validate_json(obj.model_dump_json())
    assert back == obj, f"round-trip mismatch for {cls.__name__}"
    return back


def main():
    ok = True
    truth, ev, xs, golden, notes = build()
    for o in (truth, ev, *xs, golden, notes):
        roundtrip(o)
    print("round-trip: OK (Truth, EvidenceBundle, ExtractedDoc, Golden, Notes)")

    errs = check_evidence(ev) + check_extracted(ev, xs) + check_golden(ev, golden) + check_notes(ev, golden, notes)
    print("integrity:", "OK" if not errs else errs)
    ok &= not errs

    import re
    md = (Path(__file__).resolve().parents[1] / "reference/guidelines.md").read_text()
    defined = set(re.findall(r"(?:^|\n)(?:\s*- |\*\*|\| |#+ )([A-Z]{2,4}-\d+(?:\.\d+)?)", md))
    bad = [s.rule_id for s in golden.trace if s.rule_id not in defined]
    print("trace rule ids exist in guideline:", "OK" if not bad else f"FAIL {bad}")
    ok &= not bad

    # planted errors must be caught
    bad = golden.model_copy(deep=True)
    bad.decision.net_debits = 50
    bad.trace[2].fact_ids = [f"{C}-F999"]
    bad_notes = notes.model_copy(update={"stated_decision": "Preferred Tobacco", "corruptions": []})
    caught = check_golden(ev, bad) + check_notes(ev, golden, bad_notes)
    expect = ["net_debits", "missing fact", "stated"]
    hit = all(any(e in c for c in caught) for e in expect)
    print("planted errors caught:", "OK" if hit else f"FAIL {caught}")
    ok &= hit

    # budget guard refuses before any network call
    llm._bedrock = lambda: (_ for _ in ()).throw(AssertionError("network touched"))  # noqa: E731
    try:
        with llm.Budget("selftest", cap=0.001) as b:
            llm.call("pro", "", "x" * 4000, max_tokens=8000, budget=b)
        print("budget guard: FAIL (call not refused)"); ok = False
    except llm.BudgetExceeded as e:
        print("budget guard: OK ->", e)

    out = Path(__file__).resolve().parents[1] / "qa" / "selftest_example.json"
    out.write_text(json.dumps({"truth": truth.model_dump(mode="json"), "evidence": ev.model_dump(mode="json"),
                               "extracted": [x.model_dump(mode="json") for x in xs],
                               "golden": golden.model_dump(mode="json"), "notes": notes.model_dump(mode="json")}, indent=1))
    print("example written:", out.relative_to(out.parents[1]))
    print("PHASE 0 GATE:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
