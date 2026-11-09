"""Frozen data contracts for every layer of a case.

Layering (generated strictly in this order):
    Truth  ->  EvidenceFacts + SourceDocs  ->  ExtractedDocs  ->  Golden  ->  Notes

Traceability backbone: every atomic piece of evidence is an EvidenceFact with a fact_id
("<case>-F###"). Source docs render facts, extracted docs log which facts were lost or
garbled, golden trace steps cite fact_ids, and note corruptions cite fact_ids / step numbers.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


# --------------------------------------------------------------------------- enums
class Sex(str, Enum):
    M = "M"
    F = "F"


class Disclosure(str, Enum):
    honest = "honest"              # disclosed accurately on the app
    omitted = "omitted"            # not disclosed at all
    minimized = "minimized"        # disclosed but understated (e.g. "occasional" smoker)
    misremembered = "misremembered"  # disclosed with wrong dates/details, no intent
    na = "na"                      # nothing to disclose (e.g. app question not asked)


class ConditionStatus(str, Enum):
    active = "active"
    controlled = "controlled"
    resolved = "resolved"
    in_workup = "in_workup"        # pending diagnosis -> often Postpone


class DocType(str, Enum):
    app_part1 = "app_part1"
    app_part2 = "app_part2"
    mvr = "mvr"
    rx = "rx"
    mib = "mib"
    paramed = "paramed"            # vitals/build measured by examiner
    lab_blood = "lab_blood"
    lab_urine = "lab_urine"
    lab_saliva = "lab_saliva"
    ekg = "ekg"
    aps = "aps"
    other = "other"                # financial supplement, aviation questionnaire, etc.


class Stage(str, Enum):
    application = "application"
    third_party = "third_party"
    requirements = "requirements"  # deciding what to order
    labs = "labs"
    aps = "aps"
    final = "final"


class LadderKind(str, Enum):
    non_tobacco = "non_tobacco"
    tobacco = "tobacco"


# Class order matters: lower index = better. Table classes are expressed via `table`.
NON_TOBACCO_CLASSES = ["Elite", "Preferred Plus", "Preferred", "Standard Plus", "Standard"]
TOBACCO_CLASSES = ["Preferred Tobacco", "Standard Tobacco"]
TERMINAL_OUTCOMES = ["Postpone", "Decline"]
RiskClass = Literal[
    "Elite", "Preferred Plus", "Preferred", "Standard Plus", "Standard",
    "Preferred Tobacco", "Standard Tobacco",
    "Table", "Table Tobacco",
    "Postpone", "Decline",
]


# --------------------------------------------------------------------------- truth layer
class Provider(Model):
    provider_id: str
    name: str
    specialty: str
    practice: str
    aps_style: str                  # key into reference/vendors.yaml aps styles
    country: str = "US"


class MedUse(Model):
    drug: str                       # generic name, key into reference/rx_map.yaml
    dose: str
    start: date
    stop: Optional[date] = None
    prescriber_id: Optional[str] = None
    indication: Optional[str] = None  # TRUE indication (Rx report won't show it)


class Condition(Model):
    condition_key: str              # key into rules/impairments.yaml
    label: str
    onset: date
    status: ConditionStatus
    severity: Literal["mild", "moderate", "severe"]
    details: dict[str, Any] = Field(default_factory=dict)  # e.g. {"a1c_last": 7.4, "ef": 45}
    meds: list[MedUse] = Field(default_factory=list)
    procedures: list[dict[str, Any]] = Field(default_factory=list)  # {"name","date"}
    treating_provider_ids: list[str] = Field(default_factory=list)
    disclosure: Disclosure = Disclosure.honest
    in_mib: bool = False            # whether a prior MIB code exists for it
    irrelevant: bool = False        # medically present but no UW impact (distractor)


class TobaccoUse(Model):
    product: Literal["cigarette", "cigar", "pipe", "chew", "vape", "nicotine_gum_patch", "marijuana"]
    status: Literal["current", "former"]
    frequency: str                  # "1 ppd", "2 cigars/yr", ...
    start: Optional[date] = None
    quit: Optional[date] = None
    disclosure: Disclosure = Disclosure.honest


class FamilyHistoryItem(Model):
    relation: Literal["father", "mother", "brother", "sister"]
    condition: str
    age_at_onset: Optional[int] = None
    age_at_death: Optional[int] = None
    living: bool = True


class MvrEvent(Model):
    date: date
    code: str                       # key into reference/mvr_codes.yaml
    disclosure: Disclosure = Disclosure.honest


class Avocation(Model):
    activity: str                   # key into rules (scuba, skydiving, private_pilot, ...)
    details: dict[str, Any] = Field(default_factory=dict)
    disclosure: Disclosure = Disclosure.honest


class Travel(Model):
    country: str
    weeks_per_year: float
    purpose: str
    disclosure: Disclosure = Disclosure.honest


class PriorApplication(Model):
    year: int
    company: str
    outcome: str                    # "issued Standard", "declined", "postponed"...


class Person(Model):
    first_name: str
    last_name: str
    sex: Sex
    dob: date
    age: int                        # insurance age at app date
    address_state: str
    country_of_residence: str = "US"
    citizenship: str = "US"
    years_in_us: Optional[float] = None
    visa_type: Optional[str] = None
    occupation: str
    occupation_class: str           # key into rules
    annual_income: int
    net_worth: int
    marital_status: str
    dependents: int


class Coverage(Model):
    face_amount: int
    product: str                    # "Term 10", "Term 20", "Term 30", "UL", ...
    riders_requested: list[str] = Field(default_factory=list)  # codes from reference/riders.yaml
    existing_coverage: int = 0
    replacement: bool = False
    beneficiary_relation: str = "spouse"


class Truth(Model):
    """Latent ground truth. Never shown to the UW directly."""
    case_id: str
    seed: int
    app_date: date
    design: dict[str, Any]          # the coverage-matrix row that produced this case
    person: Person
    coverage: Coverage
    height_in: float
    weight_lb: float
    bp_systolic: int
    bp_diastolic: int
    pulse: int
    tobacco: list[TobaccoUse] = Field(default_factory=list)
    alcohol_drinks_per_week: float = 0
    alcohol_treatment: bool = False
    drug_use: list[dict[str, Any]] = Field(default_factory=list)
    conditions: list[Condition] = Field(default_factory=list)
    family_history: list[FamilyHistoryItem] = Field(default_factory=list)
    mvr: list[MvrEvent] = Field(default_factory=list)
    avocations: list[Avocation] = Field(default_factory=list)
    travel: list[Travel] = Field(default_factory=list)
    prior_apps: list[PriorApplication] = Field(default_factory=list)
    providers: list[Provider] = Field(default_factory=list)
    true_labs: dict[str, float] = Field(default_factory=dict)  # analyte key -> value (canonical units)


# --------------------------------------------------------------------------- evidence layer
class EvidenceFact(Model):
    """One atomic, citable piece of evidence as it appears in a source document."""
    fact_id: str                    # "<case>-F001"
    doc_id: str
    kind: str                       # "app_answer", "rx_fill", "mib_code", "lab_value", "mvr_violation", "aps_finding", ...
    key: str                        # e.g. "tobacco_12mo", "metformin", "A1C", "100A2C"
    value: Any
    unit: Optional[str] = None
    as_of: Optional[date] = None
    relevant: bool = True           # False = distractor the UW should dismiss
    truth_ref: Optional[str] = None  # pointer into Truth, e.g. "conditions[1]" / "tobacco[0]"
    note: Optional[str] = None      # e.g. "contradicts app Q12"


class SourceDoc(Model):
    """The 'PDF' the underwriter actually reads (stored as rendered text)."""
    doc_id: str                     # "<case>-D01"
    case_id: str
    doc_type: DocType
    vendor_id: str                  # key into reference/vendors.yaml (layout/flagging/panel style)
    ordered_at: Optional[datetime] = None
    received_at: datetime
    order_reason: Optional[str] = None   # rule id or "age/amount grid"
    pages: int = 1
    text_path: str                  # data/source/<case>/<doc_id>.txt
    fact_ids: list[str] = Field(default_factory=list)


class ExtractionLoss(Model):
    fact_id: Optional[str]
    kind: Literal["dropped", "misread_digit", "unit_lost", "unit_wrong", "flag_lost",
                  "merged_cells", "split_field", "truncated_page", "header_noise", "date_garbled"]
    original: Optional[str] = None
    extracted: Optional[str] = None


class ExtractedDoc(Model):
    """What the downstream model gets: noisy, vendor-specific JSON from OCR/LLM extraction."""
    doc_id: str
    case_id: str
    doc_type: DocType
    vendor_schema: str              # schema family id; payload shape differs per vendor
    payload: dict[str, Any]
    losses: list[ExtractionLoss] = Field(default_factory=list)


class EvidenceBundle(Model):
    case_id: str
    facts: list[EvidenceFact]
    docs: list[SourceDoc]


# --------------------------------------------------------------------------- golden layer
class Effect(Model):
    debits: int = 0
    credits: int = 0
    class_cap: Optional[str] = None     # best class still attainable, e.g. "Standard Tobacco"
    ladder: Optional[LadderKind] = None  # set when a fact moves the case to the tobacco ladder
    flat_extra: Optional["FlatExtra"] = None
    postpone_months: Optional[int] = None
    decline: bool = False
    order_requirement: Optional[str] = None  # DocType value
    rider_action: Optional["RiderAction"] = None
    no_impact: bool = False             # fact reviewed and dismissed as irrelevant


class FlatExtra(Model):
    per_thousand: float
    years: Optional[int] = None         # None = permanent
    reason: str


class RiderAction(Model):
    code: str
    status: Literal["approved", "declined", "modified"]
    reason: str


class TraceStep(Model):
    step: int
    stage: Stage
    at: datetime
    fact_ids: list[str]
    rule_id: str                        # id from guidelines/rules, e.g. "TOB-2.1"
    finding: str                        # one plain sentence
    effect: Effect = Field(default_factory=Effect)


class GreyArea(Model):
    issue: str
    rule_ids: list[str]
    chosen: str                         # e.g. "Table 2"
    alternatives: list[str]             # other defensible outcomes, e.g. ["Standard", "Table 3"]
    rationale: str


class Decision(Model):
    ladder: LadderKind
    risk_class: RiskClass
    table: int = 0                      # 0, or 1..16 when risk_class in (Table, Table Tobacco)
    flat_extras: list[FlatExtra] = Field(default_factory=list)
    riders: list[RiderAction] = Field(default_factory=list)
    postpone_months: Optional[int] = None
    decline_reason: Optional[str] = None
    net_debits: int = 0
    preliminary_class: Optional[str] = None  # class indicated from app alone
    approved_face_amount: Optional[int] = None  # set when financial rules cut the amount (counter-offer)
    exclusions: list[str] = Field(default_factory=list)  # e.g. aviation exclusion endorsement

    def label(self) -> str:
        if self.risk_class in ("Table", "Table Tobacco"):
            return f"{self.risk_class} {self.table} (+{25 * self.table}%)"
        return self.risk_class


class Golden(Model):
    case_id: str
    trace: list[TraceStep]
    decision: Decision
    grey_areas: list[GreyArea] = Field(default_factory=list)
    requirements_ordered: list[str] = Field(default_factory=list)  # doc_ids ordered by UW
    narrative_path: Optional[str] = None  # data/golden/<case>.md


# --------------------------------------------------------------------------- noisy notes layer
class NoteEntry(Model):
    at: datetime
    text: str


class Corruption(Model):
    kind: Literal["abbrev_t1", "abbrev_t2", "abbrev_t3", "omitted_step", "unstated_assumption",
                  "typo", "arithmetic_error", "wrong_final", "grey_divergence", "rider_code",
                  "fact_not_in_extraction", "reordered", "fragment"]
    step: Optional[int] = None
    fact_id: Optional[str] = None
    detail: str


class Notes(Model):
    case_id: str
    persona_id: str
    observations: list[NoteEntry]
    worksheet_format: str
    worksheet: str
    stated_decision: str                # what the UW wrote (may differ from golden on purpose)
    corruptions: list[Corruption] = Field(default_factory=list)


Effect.model_rebuild()
