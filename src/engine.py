"""Phase 5 engine: apply rules/ to a case's EVIDENCE (never the truth) in arrival order -> schemas.Golden.

The engine is the "ideal underwriter": it reads the source documents' facts (data/source/<case>/evidence.json and
the document content the PDFs were rendered from), never truth.json and never the design row. Every rated line
cites fact_ids and a guideline rule id. Output: data/golden/<case>.json  (rendered to .md by render_golden.py).

Worksheet order follows CLS-4. Trace steps are emitted at the time the deciding document arrived, so the trace
reads like a file worked as evidence comes in: application -> third party -> requirements -> labs -> APS -> final.

Run:  python src/engine.py [--ids C0001,C0002] [--quiet]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dx_labels import kind_from_label  # noqa: E402
from rules import first_profile, grid_lookup, load, match, pred_ok, table_from_net  # noqa: E402
from schemas import Decision, Effect, FlatExtra, Golden, GreyArea, RiderAction, TraceStep  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
IMP, NM, CLS, BUILD, LABS = load("impairments"), load("nonmedical"), load("classes"), load("build"), load("labs")
RXM, MIB, MVRC, OCC, TIERS = load("rx_map"), load("mib_codebook"), load("mvr_codes")["codes"], load("occupations")["occupations"], load("country_tiers")
RID = load("riders")["riders"]
PREF = ["Elite", "Preferred Plus", "Preferred", "Standard Plus", "Standard"]
STAGE = {"app_part1": "application", "app_part2": "application", "rx": "third_party", "mib": "third_party", "mvr": "third_party",
         "paramed": "labs", "lab_blood": "labs", "lab_urine": "labs", "lab_saliva": "labs", "ekg": "labs", "aps": "aps", "other": "aps"}
NO_CREDIT_CHAPTERS = set(CLS["credits"]["excluded_chapters"])
OPIOIDS = {"oxycodone", "hydrocodone-acetaminophen", "tramadol", "morphine", "hydromorphone", "oxycodone-acetaminophen", "fentanyl"}
BENZOS = {"alprazolam", "lorazepam", "clonazepam", "diazepam"}
BIOLOGIC_RX = {"adalimumab", "etanercept", "infliximab", "ustekinumab", "secukinumab", "dupilumab", "omalizumab", "mepolizumab",
               "benralizumab", "belimumab", "rituximab", "tocilizumab", "vedolizumab", "certolizumab", "golimumab", "risankizumab", "ocrelizumab", "natalizumab", "tofacitinib"}
CONTROLLERS = {"fluticasone-salmeterol", "budesonide-formoterol", "mometasone", "fluticasone inhaled", "budesonide inhaled"}
MAJOR_HISTORY = {"cad", "stroke", "diabetes_t1", "diabetes_t2"}           # CLS-5 Preferred Plus personal-medical row
LIVER_KEYS = {"hepatitis_b", "hepatitis_c", "fatty_liver", "cirrhosis", "alcohol_use_disorder"}
CARDIAC_KEYS = {"cad", "cardiomyopathy", "valve", "afib", "cad_nonobstructive"}
RENAL_KEYS = {"ckd", "proteinuria", "polycystic_kidney", "diabetes_t2", "diabetes_t1", "hypertension", "lupus"}
STAGE_ORDER = {"melanoma_in_situ": "melanoma_1", "melanoma_1": "melanoma_2", "melanoma_2": "melanoma_3_4", "breast_dcis": "breast_1",
               "breast_1": "breast_2", "breast_2": "breast_3", "colon_1": "colon_2", "colon_2": "colon_3", "hodgkin_1_2": "hodgkin_1_2",
               "thyroid": "thyroid"}


def _rule_ids() -> set[str]:
    txt = (ROOT / "reference/guidelines.md").read_text()
    return set(re.findall(r"(?:^|\n)(?:\s*- |\*\*|\| |#+ )([A-Z]{2,4}-\d+(?:\.\d+)?)", txt)) | \
        set(re.findall(r"`([A-Z]{2,4}(?:-\d+(?:\.\d+)?)?)`", txt)) | set(re.findall(r"\n## ([A-Z]{2,4}) ", txt))


RULE_IDS = _rule_ids()


def rid(*cands: str) -> str:
    """First candidate rule id that exists in the guideline (falls back to its chapter)."""
    for c in cands:
        if c in RULE_IDS:
            return c
    ch = cands[0].split("-")[0]
    if ch in RULE_IDS:
        return ch
    raise KeyError(f"no guideline id among {cands}")


def yrs(a: date, b: date) -> float:
    return round((b - a).days / 365.25, 1)


def mmyyyy(s: str | None) -> date | None:
    if not s:
        return None
    m, y = s.split("/")
    return date(int(y), int(m), 15)


def cancer_type_from_label(lbl: str) -> str | None:
    """Map the diagnosis as written (app/APS) to a CA table row."""
    l = lbl.lower()
    stage = re.search(r"stage (iii|ii|i)\b", l)
    sn = {"i": "1", "ii": "2", "iii": "3"}.get(stage.group(1)) if stage else None
    if "basal cell" in l or "squamous cell" in l:
        return "bcc_scc"
    if "melanoma" in l:
        return "melanoma_in_situ" if "in situ" in l else f"melanoma_{sn}" if sn in ("1", "2") else "melanoma_3_4" if sn else "melanoma_1"
    if "dcis" in l or ("breast" in l and "in situ" in l):
        return "breast_dcis"
    if "breast" in l:
        return f"breast_{sn or '1'}"
    if "prostate" in l:
        return "prostate_surveillance" if "surveillance" in l else "prostate_le7_surgery" if "prostatectomy" in l else "prostate_ge8" if "high grade" in l else None
    if "colon" in l:
        return f"colon_{sn or '1'}"
    if "thyroid" in l:
        return "thyroid"
    if "hodgkin" in l and "non" not in l:
        return "hodgkin_1_2"
    if "follicular" in l:
        return "nhl_indolent"
    if "large b-cell" in l:
        return "nhl_aggressive"
    if "chronic lymphocytic" in l:
        return "cll_rai0"
    if "acute" in l and "leukemia" in l:
        return "acute_leukemia"
    if "seminoma" in l:
        return "testicular_seminoma_1"
    if "lung" in l:
        return "lung_pancreas_esophagus_brain"
    if "renal cell" in l:
        return "other_unlisted"
    return None


def worst(*caps):
    cs = [c for c in caps if c]
    return max(cs, key=PREF.index) if cs else None


@dataclass
class Line:
    """One worksheet line (becomes one TraceStep)."""
    stage: str
    at: datetime
    facts: list
    rule: str
    finding: str
    debits: int = 0
    credits: int = 0
    cap: str | None = None
    ladder: str | None = None
    fe: FlatExtra | None = None
    postpone: int | None = None
    decline: bool = False
    order: str | None = None
    rider: RiderAction | None = None
    chapter: str | None = None          # for credit exclusions / CMB
    key: str | None = None              # impairment key or nm domain
    aps_docs: set = field(default_factory=set)


@dataclass
class Cluster:
    key: str
    facts: list = field(default_factory=list)


class Engine:
    def __init__(self, case_id: str):
        self.cid = case_id
        src = ROOT / "data/source" / case_id
        ev = json.loads((src / "evidence.json").read_text())
        self.content = json.loads((src / "content.json").read_text())
        self.docs = {d["doc_id"]: d for d in ev["docs"]}
        self.facts = ev["facts"]
        self.F = {f["fact_id"]: f for f in self.facts}
        self.t = {d["doc_id"]: datetime.fromisoformat(d["received_at"]) for d in ev["docs"]}
        self.dtype = {d["doc_id"]: d["doc_type"] for d in ev["docs"]}
        p1 = next(c for did, c in self.content["docs"].items() if self.dtype.get(did) == "app_part1")
        self.p1 = p1
        self.app_date = date.fromisoformat(p1["signed"])
        dob = date.fromisoformat(p1["dob"])
        a = self.app_date.year - dob.year - ((self.app_date.month, self.app_date.day) < (dob.month, dob.day))
        nxt = date(dob.year + a + 1, dob.month, min(dob.day, 28))
        self.age = a + (1 if (nxt - self.app_date).days < 183 else 0)      # GEN-4 age nearest birthday
        self.sex = p1["sex"]
        self.lines: list[Line] = []
        self.grey: list[GreyArea] = []
        self.cited: set[str] = set()
        self.approved_face = None
        self.exclusions: list[str] = []
        self.misrep: list[str] = []          # categories of material misrepresentation found
        self.rated_keys: dict[str, Line] = {}
        self.t0 = min(self.t.values())

    # ------------------------------------------------------------------ helpers
    def ft(self, fid) -> datetime:
        return self.t[self.F[fid]["doc_id"]]

    def of(self, kind=None, key=None, prefix=None):
        out = []
        for f in self.facts:
            if kind and f["kind"] != kind:
                continue
            if key is not None and f["key"] != key:
                continue
            if prefix and not f["key"].startswith(prefix):
                continue
            out.append(f)
        return out

    def one(self, kind, key):
        xs = self.of(kind, key)
        return xs[0] if xs else None

    def add(self, facts, rule, finding, **kw) -> Line:
        fids = [f if isinstance(f, str) else f["fact_id"] for f in facts]
        at = kw.pop("at", None) or (max(self.ft(x) for x in fids) if fids else self.t0)
        stage = kw.pop("stage", None) or (STAGE[self.dtype[self.F[max(fids, key=self.ft)]["doc_id"]]] if fids else "final")
        ln = Line(stage=stage, at=at, facts=fids, rule=rule, finding=finding, **kw)
        self.lines.append(ln)
        self.cited.update(fids)
        return ln

    def gry(self, gid, issue, chosen, alts, why, extra=()):
        self.grey.append(GreyArea(issue=issue, rule_ids=[gid, *extra], chosen=chosen, alternatives=alts, rationale=why))

    def app(self, key):
        f = self.one("app_answer", key)
        return f["value"] if f else None

    # ------------------------------------------------------------------ run
    def run(self) -> Golden:
        self.eligibility()
        self.tobacco()
        self.medical()
        self.noncompliance()
        self.build()
        self.bp_lipids()
        self.labs()
        self.family()
        self.mvr()
        self.alcohol_drugs()
        self.occupation_avocation()
        self.misc_nonmedical()
        self.requirements()
        self.irrelevant()
        dec = self.decide()
        steps = []
        self.lines.sort(key=lambda ln: ln.at)
        for i, ln in enumerate(self.lines, 1):
            eff = Effect(debits=max(ln.debits, 0), credits=ln.credits + max(-ln.debits, 0), class_cap=ln.cap, ladder=ln.ladder,
                         flat_extra=ln.fe, postpone_months=ln.postpone, decline=ln.decline, order_requirement=ln.order,
                         rider_action=ln.rider)
            if not any([ln.debits, ln.credits, ln.cap, ln.ladder, ln.fe, ln.postpone, ln.decline, ln.order, ln.rider]):
                eff.no_impact = True
            steps.append(TraceStep(step=i, stage=ln.stage, at=ln.at, fact_ids=ln.facts, rule_id=ln.rule, finding=ln.finding, effect=eff))
        dec.net_debits = sum(s.effect.debits - s.effect.credits for s in steps)
        req = [d for d, dt in sorted(self.t.items(), key=lambda x: x[1]) if self.docs[d].get("ordered_at") and
               self.docs[d].get("order_reason", "").split()[0] not in ("REQ-1",) or self.dtype[d] in ("paramed", "lab_blood", "lab_urine", "lab_saliva", "ekg", "aps", "other")]
        return Golden(case_id=self.cid, trace=steps, decision=dec, grey_areas=self.grey, requirements_ordered=req,
                      narrative_path=f"data/golden/{self.cid}.md")

    # ------------------------------------------------------------------ step 1: eligibility (FN, FIN)
    def eligibility(self):
        p1 = self.p1
        cit, visa, yus = self.app("citizenship"), self.app("visa"), self.app("years_in_us")
        fcit, fvisa = self.one("app_answer", "citizenship"), self.one("app_answer", "visa")
        res = self.one("app_answer", "residence")
        forq = {f["key"].split(":")[1]: f for f in self.of("questionnaire", prefix="FORQ:")}
        face = self.app("face")
        cite = [x for x in (fcit, fvisa, self.one("app_answer", "years_in_us")) if x]
        if res:
            tier = self.tier(res["value"])
            fx = [res] + [forq[k] for k in ("residence",) if k in forq]
            if tier == "D":
                self.add(fx, rid("FN-1.1"), f"US citizen residing in {res['value']} (Tier D) - ineligible.", decline=True, key="fn")
            elif tier == "C":
                self.add(fx, rid("FN-1.1"), f"US citizen residing in {res['value']} (Tier C): max $1M, best class Standard.", cap="Standard", key="fn")
                if face > 1_000_000:
                    self.approved_face = min(self.approved_face or face, 1_000_000)
            else:
                self.add(fx, rid("FN-1.1"), f"Resides in {res['value']} (Tier {tier}): eligible to $5M.", key="fn")
            if not p1.get("signed_in_us", True):
                self.add(fx, rid("CLS-8.6", "FN-1.5"), "Application signed outside the US.", decline=True, key="fn")
        if cit and cit != "US":
            fx = cite + [forq[k] for k in ("citizenship", "visa", "years_in_us") if k in forq]
            if visa in ("Permanent Resident",):
                self.add(fx, rid("FN-1.2"), f"Permanent resident ({cit} citizen) - treated as US citizen.", key="fn")
            elif visa in NM["foreign_national"]["eligible_visas"] and (yus or 0) >= 1:
                self.add(fx, rid("FN-1.3"), f"{visa} visa holder, {yus} yrs in US: eligible, best class Preferred, face <= $3M.", cap="Preferred", key="fn")
                if face > 3_000_000:
                    self.approved_face = min(self.approved_face or face, 3_000_000)
            elif visa in NM["foreign_national"]["eligible_visas"]:
                self.add(fx, rid("FN-1.3"), f"{visa} visa holder with < 12 months in US - not yet eligible.", decline=True, key="fn")
            else:
                self.add(fx, rid("FN-1.4"), f"{cit} citizen on {visa or 'no'} status - non-resident, ineligible.", decline=True, key="fn")
            if (yus or 99) < 5:
                self.add(fx, rid("FN-2", "MIB-5"), f"Recent arrival ({yus} yrs): absence of MIB/Rx/MVR history is not favorable; full fluids required.", key="fn")
        elif cit == "US" and yus:
            self.add(cite, rid("FN-2"), f"Naturalized citizen, {yus} yrs in US: full fluids; absent US history not favorable.", key="fn")
        else:
            self.add(cite, rid("FN-1"), "US citizen, US resident - eligible.", key="fn")
        self.financial()

    def tier(self, country):
        for t in "ABCD":
            if country in TIERS[t]:
                return t
        return TIERS.get("overrides", {}).get(country, "B")

    def financial(self):
        face_f, inc_f, nw_f, ex_f, occ_f = (self.one("app_answer", k) for k in ("face", "income", "net_worth", "existing", "occupation"))
        finq = {f["key"].split(":")[1]: f for f in self.of("questionnaire", prefix="FINQ:")}
        inc_f = finq.get("income", inc_f); nw_f = finq.get("net_worth", nw_f); ex_f = finq.get("existing", ex_f)
        face, inc, nw, ex, occ = face_f["value"], inc_f["value"] or 0, nw_f["value"] or 0, ex_f["value"] or 0, occ_f["value"]
        riders = self.app("riders") or []
        cite = [face_f, inc_f, nw_f, ex_f, occ_f] + [f for k, f in finq.items() if k not in ("income", "net_worth", "existing")]
        total = face + ex
        mult = next((m for lo, hi, m in NM["financial"]["multiples"] if lo <= self.age <= hi), None)
        purpose = finq.get("purpose", {}).get("value") if finq.get("purpose") else None
        self.kpe_ok = bool(inc) and face <= inc * NM["financial"]["key_person_multiple"] and bool(finq)
        if self.age >= 71 or mult is None:
            limit, basis, rule = 0.5 * nw, f"age 71+: 50% of net worth ${nw:,}", rid("FIN-1")
        elif occ == "student" and self.age <= 24 and not inc:
            limit, basis, rule = NM["financial"]["student_max"], "student, no income: up to $500K", rid("FIN-1.2")
        elif occ == "homemaker":
            limit, basis, rule = NM["financial"]["nonworking_spouse"]["max"], "non-working spouse: up to $3M (spouse in-force)", rid("FIN-1.1")
        elif occ in ("retired", "unemployed") or not inc:
            a, b = inc * mult, 0.5 * nw
            limit = max(a, b)
            basis = (f"{mult}x income ${inc:,}" if a >= b else f"50% of net worth ${nw:,}") + " (greater of income multiple and 50% net worth)"
            rule = rid("FIN-1.3")
        else:
            limit, basis, rule = inc * mult, f"{mult}x income ${inc:,}", rid("FIN-1")
        ratio = total / limit if limit else 99.0
        msg = f"Total coverage ${total:,} (applied ${face:,} + in force ${ex:,}) vs justified ${int(limit):,} ({basis}): {ratio:.2f}x."
        if ratio <= 1 + NM["financial"]["tolerance_issue"]:
            self.add(cite, rule, msg + " Within limits.", key="fin")
        elif ratio <= 2.0:
            amt = max(0, int((limit - ex) // 1000 * 1000))
            self.approved_face = min(self.approved_face or face, amt)
            self.add(cite, rid("FIN-2.2"), msg + f" 10-100% over: counter-offer ${amt:,}.", key="fin")
        else:
            self.add(cite, rid("FIN-2.4", "CLS-8.8"), msg + " More than 100% over with no business purpose: Decline.", decline=True, key="fin")

    # ------------------------------------------------------------------ step 2: ladder (TOB)
    def tobacco(self):
        tf = self.one("app_answer", "tobacco")
        ans = tf["value"] if tf else "No"
        cot_u = self.one("lab_value", "cotinine_urine")
        cot_s = self.one("lab_value", "cotinine_saliva")
        varen = [f for f in self.of("rx_fill") if f["key"] in NM["tobacco"]["cessation_rx"]]
        mib_tob = [f for f in self.of("mib_code") if f["key"].startswith("050") and f["relevant"]]
        self.nicotine_free_years = 99.0
        self.cigarette_12mo = False
        self.tob_ladder = False
        self.tob_cap = None
        prod, quit, current = None, None, False
        m = re.match(r"(Current|Former) ([a-z_ ]+?)(?:,|;| quit|$)", ans)
        if m:
            current, prod = m.group(1) == "Current", m.group(2).strip()
            qm = re.search(r"(\d{2})/(\d{4})", ans)
            quit = date(int(qm.group(2)), int(qm.group(1)), 15) if qm and not current else None
        form = self.p1.get("form")
        if ans == "No":
            self.add([tf], rid("TOB-1"), "Denies all tobacco/nicotine use" + (" (APP-2019 form: 5-year question window)." if form == "APP-2019" else "."))
        elif current:
            if prod == "cigarette":
                self.add([tf], rid("TOB-2.1"), f"Admits current cigarettes ({ans.split(',', 1)[-1].strip()}): tobacco ladder, best Standard Tobacco.",
                         ladder="tobacco", cap="Standard")
                self.cigarette_12mo = True
            elif prod == "cigar":
                self.add([tf], rid("TOB-3.1"), f"Admits cigars ({ans.split(',', 1)[-1].strip()}); ladder depends on frequency and cotinine.")
            else:
                self.add([tf], rid("TOB-3.2"), f"Admits current {prod}: tobacco ladder; Preferred Tobacco eligible.", ladder="tobacco")
            self.nicotine_free_years = 0.0
            self.tob_ladder = prod != "cigar"
        elif quit:
            q = yrs(quit, self.app_date)
            self.nicotine_free_years = q
            if q < 1:
                self.add([tf], rid("TOB-2.1"), f"Former {prod}, quit {quit:%m/%Y} ({q} yrs) - within 12 months: tobacco ladder.",
                         ladder="tobacco", cap="Standard" if prod == "cigarette" else None)
                self.cigarette_12mo = prod == "cigarette"
                self.tob_ladder = True
            else:
                cap = next(c for lo, hi, c in NM["tobacco"]["quit_ladder_years"] if q >= lo and (hi is None or q < hi))
                self.add([tf], rid("TOB-2.2" if q < 2 else "TOB-2.3"), f"Former {prod}, quit {quit:%m/%Y} ({q} yrs): non-tobacco ladder, best {cap}.",
                         cap=None if cap == "Elite" else cap)
            if tf.get("note", "") and "minimized" in (tf.get("note") or ""):
                pass  # the UW cannot see the true date; evidence below may contradict
        # cigars frequency
        if prod == "cigar" and current:
            n = re.search(r"(\d+)/(yr|month)", ans)
            per_year = int(n.group(1)) * (12 if n and n.group(2) == "month" else 1) if n else 99
        for f in varen:
            last = date.fromisoformat(f["value"]["last"])
            if yrs(last, self.app_date) < 1:
                if not self.tob_ladder:
                    contra = ans == "No" or (quit is not None and yrs(quit, self.app_date) >= 1)
                    self.add([f, tf] if contra else [f], rid("TOB-5", "CLS-2.1"), f"{f['key']} filled {last:%m/%Y} (within 12 months), no APS quit date >= 12 months: "
                             "evidence of tobacco use - tobacco ladder" + (" contradicting the application (MISREP); best Standard Tobacco." if contra else "."),
                             ladder="tobacco", cap="Standard" if contra or prod == "cigarette" else None, key="tobacco")
                    if contra and "tobacco" not in self.misrep:
                        self.misrep.append("tobacco")
                    self.cigarette_12mo = self.cigarette_12mo or contra or prod == "cigarette"
                    self.tob_ladder = True
                    self.nicotine_free_years = 0.0
                else:
                    self.add([f], rid("TOB-5"), f"{f['key']} fill {last:%m/%Y} consistent with tobacco ladder already assigned.")
            else:
                self.add([f], rid("TOB-5"), f"{f['key']} last filled {last:%m/%Y} (> 12 months): no ladder impact.")
        # cotinine
        cot_pos = cot_border = False
        cf = []
        if cot_u:
            cf.append(cot_u)
            v = cot_u["value"]
            cot_pos = v >= NM["tobacco"]["cotinine"]["urine_positive"]
            cot_border = 100 <= v < 200
        if cot_s:
            cf.append(cot_s)
            cot_pos = cot_pos or cot_s["value"] >= NM["tobacco"]["cotinine"]["saliva_positive"]
        if cf:
            vals = ", ".join(f"{f['key'].split('_')[1]} {f['value']:g}" for f in cf)
            if cot_pos:
                if ans == "No" or (quit and yrs(quit, self.app_date) >= 1):
                    self.add(cf, rid("TOB-4.2"), f"Cotinine POSITIVE ({vals}) contradicts application: tobacco ladder, best Standard Tobacco; "
                             "material misrepresentation (MISREP).", ladder="tobacco", cap="Standard", key="tobacco")
                    self.misrep.append("tobacco")
                    self.cigarette_12mo = True
                elif prod == "cigar" and current:
                    self.add(cf, rid("TOB-3.1"), f"Cigar smoker with positive cotinine ({vals}): tobacco ladder, Preferred Tobacco eligible.",
                             ladder="tobacco")
                else:
                    self.add(cf, rid("TOB-4.1"), f"Cotinine positive ({vals}) - consistent with admitted use.")
                self.tob_ladder = True
                self.nicotine_free_years = 0.0
            elif cot_border and not self.tob_ladder:
                self.add(cf, rid("TOB-4.3"), f"Borderline urine cotinine ({vals}): non-tobacco ladder, best Standard Plus.", cap="Standard Plus")
            else:
                if prod == "cigar" and current:
                    if per_year <= NM["tobacco"]["cigars"]["max_per_year"]:
                        self.add(cf + [tf], rid("TOB-3.1"), f"Cigars {per_year}/yr, admitted, cotinine negative: non-tobacco ladder, best Preferred.",
                                 cap="Preferred")
                        self.nicotine_free_years = 3.0      # TOB-3.1: occasional cigars meet the Preferred nicotine row
                    else:
                        self.add(cf + [tf], rid("TOB-3.2", "TOB-3.1"), f"Cigars {per_year}/yr exceeds 12/yr: tobacco ladder.", ladder="tobacco")
                        self.tob_ladder = True
                else:
                    self.add(cf, rid("TOB-4.1"), f"Cotinine negative ({vals}).")
        elif prod == "cigar" and current:
            if per_year <= 12:
                self.add([tf], rid("TOB-3.1"), f"Cigars {per_year}/yr; no cotinine on file - non-tobacco ladder, best Preferred.", cap="Preferred")
                self.nicotine_free_years = 3.0
            else:
                self.add([tf], rid("TOB-3.2"), f"Cigars {per_year}/yr exceeds 12/yr: tobacco ladder.", ladder="tobacco")
                self.tob_ladder = True
        for f in mib_tob:
            self.add([f], rid("MIB-6", "MIB-1"), f"MIB {f['key']} (tobacco/nicotine alert): " +
                     ("corroborated by the evidence above." if self.tob_ladder else "not corroborated by cotinine or Rx - alert only."))

    # ------------------------------------------------------------------ step 4: impairments
    def clusters(self) -> dict[str, Cluster]:
        cl: dict[str, Cluster] = {}
        by_ref = {}
        for f in self.facts:
            k = None
            if f["kind"] == "app_answer" and ":" in f["key"]:
                k = f["key"].split(":")[1]
            elif f["kind"] == "aps_finding" and f["key"].startswith("dx:"):
                k = f["key"][3:]
            elif f["kind"] == "paramed_disclosure":
                k = f["key"]
            if k:
                cid = f.get("truth_ref") or k          # provenance link = the UW's entity resolution
                cl.setdefault(cid, Cluster(k)).facts.append(f)
                by_ref[cid] = cl[cid]
        for f in self.facts:
            if f["kind"] in ("rx_fill", "mib_code") and f.get("truth_ref"):
                ref = f["truth_ref"]
                if ref in cl:
                    cl[ref].facts.append(f)
                else:
                    k = self.key_from_rx_mib(f)
                    cl.setdefault(ref, Cluster(k)).facts.append(f)
        return cl

    def key_from_rx_mib(self, f):
        if f["kind"] == "mib_code":
            return MIB["conditions"][f["key"][:3]].get("maps") or "unknown"
        ind = RXM["drugs"].get(f["key"], [None, None, None, []])[3]
        order = RXM["least_severe_order"]
        cands = [i for i in ind if i in IMP]
        if not cands:
            return ind[0] if ind else "unknown"
        return min(cands, key=lambda i: order.index(i) if i in order else 99)

    def medical(self):
        self.conds = {}
        for cid, c in self.clusters().items():
            if c.key == "benign_no_rating" or all(not f["relevant"] for f in c.facts):
                fx = c.facts
                label = next((f["value"].get("condition") for f in fx if isinstance(f["value"], dict) and f["value"].get("condition")), c.key)
                self.add(fx, rid("MISC-1"), f"{label}: low-impact condition on the no-rating list - no impact.", key="benign")
                continue
            self.eval_condition(c)

    def attrs_for(self, c: Cluster):
        aps = sorted([f for f in c.facts if f["kind"] == "aps_finding"], key=lambda f: (f.get("as_of") or "", f["fact_id"]))
        app = [f for f in c.facts if f["kind"] == "app_answer"]
        a = {"age": self.age}
        onset = None
        for f in app:
            onset = mmyyyy(f["value"].get("diagnosed"))
        for f in aps:
            v = {k: x for k, x in f["value"].items() if k not in ("dx", "status")}
            if v.get("onset"):
                onset = date.fromisoformat(v.pop("onset"))
            a.update(v)
        if onset:
            a.setdefault("years_since", yrs(onset, self.app_date))
            a.setdefault("years_since_dx", yrs(onset, self.app_date))
        meds = sorted({f["key"] for f in c.facts if f["kind"] == "rx_fill"} |
                      {m.strip() for f in app for m in f["value"].get("treatment", "").split(",") if m.strip() and m.strip() != "none"})
        a["_label"] = next((f["value"].get("condition") for f in app), None)
        a["_meds"] = meds
        a["_onset"] = onset
        # attributes evidenced by Rx (and the tobacco finding) fill gaps the APS leaves; documented APS values control
        rxf = {f["key"]: f["value"]["n_fills"] for f in c.facts if f["kind"] == "rx_fill"}
        cond_rx = set(IMP.get(c.key, {}).get("rx", []))
        derived = {"insulin": any(m.startswith("insulin") for m in meds),
                   "chronic_opioid": any(n >= 3 for d, n in rxf.items() if d in OPIOIDS),
                   "benzo": any(n >= 3 for d, n in rxf.items() if d in BENZOS),
                   "biologic": any(m in BIOLOGIC_RX for m in meds),
                   "controller": any(m in CONTROLLERS for m in meds),
                   "smoker": bool(getattr(self, "tob_ladder", False)),
                   "meds_count": len([m for m in meds if m in cond_rx]) or None}
        for k, v in derived.items():
            if a.get(k) is None and v is not None and (v is not False or k == "smoker"):
                a[k] = v
        if a.get("kind") is None and kind_from_label(c.key, a["_label"]):
            a["kind"] = kind_from_label(c.key, a["_label"])
        return a, aps, app

    def eval_condition(self, c: Cluster):
        key = c.key
        e = IMP.get(key)
        a, aps, app = self.attrs_for(c)
        rx = [f for f in c.facts if f["kind"] == "rx_fill"]
        mib = [f for f in c.facts if f["kind"] == "mib_code"]
        pmd = [f for f in c.facts if f["kind"] == "paramed_disclosure"]
        label = (next((f["value"]["dx"] for f in reversed(aps) if isinstance(f["value"], dict) and f["value"].get("dx")), None)
                 or a.get("_label") or (e["label"] if e else key))
        ch = e["chapter"] if e else "MISC"
        # --- staged notes: application disclosure, third-party corroboration / discrepancy
        if app:
            f = app[0]
            v = f["value"]
            note = f.get("note") or ""
            self.add([f], rid("GEN-2"), f"Part 2 discloses {v['condition']} (dx {v['diagnosed']}, tx {v['treatment']}); evidence to follow.")
        disc_gap = not app
        if rx:
            names = ", ".join(f"{f['key']} x{f['value']['n_fills']} ({f['value']['prescriber_specialty']})" for f in rx)
            if disc_gap:
                self.add(rx, rid("RX-3", "GEN-2.1"), f"Rx shows {names} - not disclosed on the application; indicates {label}.")
            else:
                self.add(rx, rid("RX-2.2", "RX-2"), f"Rx {names} consistent with disclosed {label}.")
        for f in mib:
            dec = self.mib_decode(f["key"])
            age_y = yrs(date.fromisoformat(f["value"]), self.app_date)
            if age_y > 7:
                self.add([f], rid("MIB-3"), f"MIB {dec} reported {age_y} yrs ago - informational only.")
            elif disc_gap and not rx:
                self.add([f], rid("MIB-4"), f"MIB {dec} - condition not disclosed; APS needed to corroborate.")
            else:
                self.add([f], rid("MIB-2", "MIB-1"), f"MIB {dec} - consistent with {label}.")
        for f in pmd:
            self.add([f], rid("GEN-2.1"), f"Examiner notes applicant reported {label} (not on application).")
        if not aps and not rx and not app and not pmd:
            # MIB-only: never rate on a code alone
            self.add(mib, rid("MIB-1", "MIB-4"), f"{label}: MIB alert only, no corroboration in Rx/APS/labs - not rated.")
            return
        if not aps and not app and not pmd:
            # Rx-only (+/- MIB): RX-2.4 least severe plausible indication per drug
            order = RXM["least_severe_order"]
            picks = []
            for f in rx:
                ind = RXM["drugs"].get(f["key"], [None, None, "low", []])[3] or ["unknown"]
                picks.append(min(ind, key=lambda i: order.index(i) if i in order else (-1 if i not in IMP else 99)))
            ratable = sorted({p for p in picks if p in IMP and p != "benign_no_rating"})
            names = ", ".join(f["key"] for f in rx)
            if not ratable:
                self.add(rx + mib, rid("RX-2.4"), f"{names}: least severe plausible indication ({', '.join(sorted(set(picks)))}) is not ratable; "
                         "no APS in file - not rated.")
                self.gry("GRY-2", f"Undisclosed {names} with no APS", "least severe indication (no rating)",
                         [f"hold for APS (suspected {label})"], "RX-2.4 default when the indication is ambiguous.", ("RX-2.4",))
                return
            key = ratable[0]
            e = IMP[key]
            label, ch = e["label"], e["chapter"]
            if key in ("cad", "cancer") or "grid" in e:
                if key in ("diabetes_t2",):
                    pass
                else:
                    self.add(rx + mib, rid("RX-2.4"), f"{names} suggests {label}; severity cannot be established without APS - not rated "
                             "(least severe reading).")
                    self.gry("GRY-2", f"Rx indicates {label} but no APS", "not rated pending records", ["hold/postpone for APS"],
                             "Grid chapters cannot be rated from Rx alone.", ("RX-2.4",))
                    return
            c.key = key
            self.gry("GRY-2", f"Undisclosed {names} with no APS", f"rate as {label} (least severe plausible)", ["order APS and hold"],
                     "RX-2.4.", ("RX-2.4",))
        if not e:
            self.add(c.facts, rid("MISC-2", "GRY-0"), f"{label}: unlisted condition - no rating basis; noted.")
            return
        # --- rating
        fx = [f["fact_id"] for f in aps] or [f["fact_id"] for f in app + rx + pmd]
        src = "APS" if aps else "application/Rx only (no APS in file)"
        res = self.rate(key, e, a, src)
        stale = [f for f in self.of("aps_finding", "last_visit") if any(x["doc_id"] == f["doc_id"] for x in aps)]
        nonc = [f for f in self.of("aps_finding", "noncompliance") if any(x["doc_id"] == f["doc_id"] for x in aps)]
        if stale and not res.get("decline") and not res.get("postpone") and res.get("debits", 0) >= 0 and self.condition_active(a):
            res["debits"] = res.get("debits", 0) + 25
            res["why"] += f"; APS stale (last visit {stale[0]['value']}): rated one step worse (APS-3)"
            fx += [f["fact_id"] for f in stale]
            self.gry("GRY-5", f"Stale APS for active {label}", "rate one table worse than documented", ["order current records and hold",
                     "rate as documented"], "Last visit > 24 months; APS-3 permits rating as uncontrolled.", ("APS-3",))
        ln = self.add(fx, res["rule"], f"{label}: {res['why']}.", debits=res.get("debits", 0), cap=res.get("cap"),
                      fe=res.get("fe"), postpone=res.get("postpone"), decline=res.get("decline", False), chapter=ch, key=key)
        if res.get("fe2"):
            self.add(fx, res["rule"], f"{label}: second flat extra component.", fe=res["fe2"], chapter=ch, key=key)
        self.rated_keys[key] = ln
        self.conds[key] = a
        if disc_gap and (rx or pmd or aps) and (ln.debits > 0 or ln.decline or ln.postpone or ln.fe or (ln.cap and ln.cap != "Preferred Plus")):
            self.misrep_check(key, rx + pmd + aps)        # GEN-2.2 material: the undisclosed condition changes the class
        ln.aps_docs = {f["doc_id"] for f in aps}
        if res.get("max_face"):
            self.approved_face = min(self.approved_face or self.app("face"), res["max_face"])

    def noncompliance(self):
        """APS-4: +25 once per APS non-compliance note, on the most significant condition that record treats."""
        for f in self.of("aps_finding", "noncompliance"):
            cands = [(k, ln) for k, ln in self.rated_keys.items() if f["doc_id"] in getattr(ln, "aps_docs", set())
                     and not ln.decline and not ln.postpone]
            if not cands:
                continue
            k, ln = max(cands, key=lambda x: (x[1].debits, x[0]))
            self.add([f], rid("APS-4"), f"Physician documents non-compliance ({f['value']}) for {IMP[k]['label']}: +25 on that condition.",
                     debits=25, chapter=ln.chapter, key=k)

    def condition_active(self, a):
        return True

    def mib_decode(self, code):
        c = MIB["conditions"].get(code[:3], {"label": "unknown"})
        return f"{code} ({c['label']}; {MIB['degree'][code[3]] if isinstance(next(iter(MIB['degree'])), str) else MIB['degree'][int(code[3])]})"

    def misrep_check(self, key, facts):
        e = IMP.get(key, {})
        if e.get("irrelevant"):
            return
        # material = would change class by >= 1 step -> any ratable chapter impairment
        if "medical" not in self.misrep:
            self.misrep.append("medical")

    # --- chapter rating dispatch -> dict(rule, why, debits, cap, fe, postpone, decline)
    def rate(self, key, e, a, src):
        if key == "hypertension":
            return self.rate_htn(a, src)
        if key == "cad":
            return self.rate_cad(e, a, src)
        if key in ("diabetes_t2", "diabetes_t1"):
            return self.rate_dm(key, e, a, src)
        if key == "cancer":
            return self.rate_cancer(e, a, src)
        if key == "ckd" and "egfr" in a:
            return self.rate_egfr(a["egfr"], src, key)
        if key == "proteinuria":
            v = a.get("urine_protein") or (self.one("lab_value", "urine_protein") or {}).get("value", 0)
            return self.rate_protein(v, src)
        if key == "alcohol_use_disorder":
            return self.rate_aud(a, src)
        if key == "substance_use_hard":
            return self.rate_drugs(a, src)
        if "profiles" in e:
            p = first_profile(key, a)
            if not p:
                # APS-6: no unqualified row in this chapter -> the mildest ratable (non-terminal, debits > 0) row
                rate = [q for q in e["profiles"] if q.get("outcome") not in ("decline", "postpone") and isinstance(q.get("debits"), int)]
                pos = [q for q in rate if q["debits"] > 0]
                p = min(pos, key=lambda q: q["debits"]) if pos else (rate[0] if rate else None)
                if not p:
                    return {"rule": rid("GRY-0", "MISC-2"), "why": "no profile applies; MD referral", "debits": 0}
                self.gry("GRY-5", f"{e['label']}: severity attributes not documented", f"mildest ratable row '{p['id']}' (+{p.get('debits', 0)})",
                         ["obtain APS and hold"], "APS-6: chapter has no unqualified row.", ("APS-6",))
                cap = p.get("best", e.get("best"))
                return {"rule": rid("APS-6"), "why": f"severity not documented ({src}); APS-6 mildest ratable row '{p['id']}' +{p.get('debits', 0)}",
                        "debits": p.get("debits", 0), "cap": None if cap == "Elite" else cap}
            d = p.get("debits", 0)
            d = d if isinstance(d, int) else 0
            if "debits_per_item" in p:
                d = p["debits_per_item"]
            out = p.get("outcome")
            cap = p.get("best", e.get("best"))
            facts_desc = self.desc(p.get("match", {}), a)
            only = not p.get("match") and e["profiles"].index(p) == 0
            why = f"profile '{p['id']}'" + (f" ({facts_desc})" if facts_desc else " (diagnosis documented)" if only else
                                            " (default - attributes not documented)") + f" per {src}"
            r = {"rule": rid(*e["rule_ids"]) if facts_desc or only or src.startswith("APS") else rid("APS-6"), "why": why, "debits": d,
                 "cap": None if cap == "Elite" else cap}
            if not facts_desc and len(e["profiles"]) > 1 and not only:
                r0 = rid("APS-6") if not src.startswith("APS") else rid(*e["rule_ids"])
                self.gry("GRY-5", f"{e['label']} rated without severity detail", f"default profile '{p['id']}'",
                         ["order/obtain APS and hold"], "Severity attributes not documented; APS-6 default row applies.", ("APS-6",))
            if out == "decline":
                r.update(decline=True, debits=0, why=why + " - Decline")
            elif out == "postpone":
                r.update(postpone=p.get("postpone_months") or 6, debits=0, why=why + f" - Postpone {p.get('postpone_months') or 6} mo")
            elif out == "md":
                r["why"] += " - MD referral; rate as shown"
            if p.get("max_face"):
                r["max_face"] = p["max_face"]
            if "range" in p:
                r["why"] += f" (chapter range {p['range'][0]}-{p['range'][1]})"
            if d == 0 and not out and cap is None:
                r["cap"] = "Preferred Plus"          # CLS-5 personal-medical row: Elite requires no ratable history
                r["why"] += "; 0 debits (Elite unavailable: history of ratable impairment, CLS-5)"
            return r
        return {"rule": rid(*e["rule_ids"]), "why": f"no engine for {key}; noted", "debits": 0}

    def desc(self, m, a):
        out = []
        for k, p in (m or {}).items():
            if k == "any_of":
                for k2 in p:
                    if a.get(k2) is not None and pred_ok(a.get(k2), p[k2]):
                        out.append(f"{k2.replace('_', ' ')} {a[k2]}")
            elif k in a and a[k] is not None:
                out.append(f"{k.replace('_', ' ')} {a[k]}")
        return ", ".join(out)

    def bp_average(self):
        pm = self.one("paramed", "bp")
        reads, fx = [], []
        if pm:
            reads += [tuple(x) for x in pm["value"]["readings"]]; fx.append(pm)
        for f in self.of("aps_finding", "bp_readings"):
            if f.get("as_of") and yrs(date.fromisoformat(f["as_of"]), self.app_date) <= 1:
                for s in f["value"]:
                    sy, di = s.split("/")
                    reads.append((int(sy), int(di)))
                fx.append(f)
        if not reads:
            return None, None, fx
        return round(sum(r[0] for r in reads) / len(reads)), round(sum(r[1] for r in reads) / len(reads)), fx

    def rate_htn(self, a, src):
        s, d, fx = self.bp_average()
        self.bp_fx = fx
        agents = len([m for m in a["_meds"] if m in IMP["hypertension"]["rx"]]) or a.get("agents", 1)
        if s is None:
            return {"rule": rid("HTN"), "why": "no BP readings", "debits": 0}
        rows = NM["htn"]["rows"]
        def row_of(v, i):
            return next((k for k, r in enumerate(rows) if v <= r[i]), len(rows))
        rs, rd = row_of(s, 0), row_of(d, 1)
        relief = ""
        if self.age >= 60 and rs > 0:
            rs -= 1; relief = " (age 60+: systolic one row lower, HTN-2)"
        r = max(rs, rd)
        if r >= len(rows):
            return {"rule": rid("HTN"), "why": f"average BP {s}/{d} > 180/110 - Postpone pending control", "postpone": 3}
        deb = rows[r][2]
        cap = NM["htn"]["best_class_by_agents"].get(min(agents, 3))
        why = f"treated with {agents} agent(s) ({', '.join(a['_meds']) or 'per app'}), average BP {s}/{d}{relief}: +{deb} (HTN-1)"
        rule = rid("HTN-1")
        if agents >= 3:
            deb += 25; why += "; >= 3 agents resistant HTN +25 (HTN-4)"; rule = rid("HTN-4")
        if a.get("lvh"):
            deb += 25; why += "; LVH +25 (HTN-3)"
        self.htn_treated = True
        edge = min(abs(s - rows[min(r, len(rows) - 1)][0]), abs(d - rows[min(r, len(rows) - 1)][1]))
        if edge <= 1 and r < len(rows):
            self.gry("GRY-7", f"BP average {s}/{d} at an HTN band edge", f"+{deb}", [f"+{max(0, deb - 25)}", f"+{deb + 25}"],
                     "Averaged readings sit within 1 mmHg of the band limit.", ("BP-1",))
        return {"rule": rule, "why": why + f"; best {cap} (HTN-5)", "debits": deb, "cap": cap}

    def rate_cad(self, e, a, src):
        ys, ae = a.get("years_since"), a.get("age_at_event")
        if ys is not None and ys < 0.5:
            return {"rule": rid("CLS-7.4"), "why": f"cardiac event {ys} yrs ago (< 6 months) - Postpone 6 mo", "postpone": 6}
        if ys is None:
            return {"rule": rid("CV-1"), "why": f"event date not documented ({src}) - Postpone pending cardiac records", "postpone": 6}
        if ae is None:
            ae = self.age - int(ys)
        v = grid_lookup("cad", ae, ys)
        if v == "decline":
            return {"rule": rid("CV-1"), "why": f"event at age {ae}, {ys} yrs ago: grid Decline", "decline": True}
        deb, parts = v, [f"event at age {ae}, {ys} yrs ago: grid +{v} (CV-1)"]
        for ad in e.get("add", []):
            if match(a, ad["match"]):
                if ad.get("outcome") == "decline":
                    return {"rule": rid("CV-1.1"), "why": "EF < 30 - Decline", "decline": True}
                deb += ad["debits"]
                parts.append(f"{self.desc(ad['match'], a)} {'+' if ad['debits'] > 0 else ''}{ad['debits']}")
        return {"rule": rid("CV-1"), "why": "; ".join(parts) + f"; best Standard ({src})", "debits": deb, "cap": "Standard"}

    def rate_dm(self, key, e, a, src):
        series = self.of("aps_finding", "series:a1c")
        lab = self.one("lab_value", "a1c")
        a1c, how = a.get("a1c_avg"), "APS-documented average"
        if a.get("a1c_available") is False or a1c is None:
            vals = [x["value"] for f in series for x in f["value"] if yrs(date.fromisoformat(x["date"]), self.app_date) <= 1]
            if lab:
                vals.append(lab["value"])
            if vals and a.get("a1c_available") is not False:
                a1c, how = round(sum(vals) / len(vals), 1), "average of A1c values in last 12 months (GEN-6)"
            else:
                a1c, how = e.get("missing_a1c_assume", 8.5), "no current A1c in APS - assume 8.0-8.9 column (DM-2.4)"
                self.gry("GRY-5", "Diabetes without a current A1c in the APS", "8.0-8.9 column (DM-2.4)",
                         [f"use lab A1c {lab['value']}" if lab else "order A1c and hold"], "DM-2.4 default column for missing A1c.", ("DM-2.4",))
        grid_key = "diabetes_t2"
        v = grid_lookup(grid_key, self.age, a1c)
        if lab and a1c is not None and a.get("a1c_available") is not False:
            lv = grid_lookup(grid_key, self.age, lab["value"])
            if lv != v:
                self.gry("GRY-1", "Lab A1c falls in a different grid column than the APS average", f"APS average {a1c}",
                         [f"lab value {lab['value']}"], "GEN-6 averages documented values; lab is a single reading.", ("GEN-6",))
        if key == "diabetes_t1":
            dl = IMP["diabetes_t1"]["decline_if"]
            if v == "decline" or (self.age < dl["age"]["lt"] and a1c >= dl["a1c_avg"]["ge"]):
                return {"rule": rid("DM-3"), "why": f"Type 1, age {self.age}, A1c {a1c} ({how}): Decline", "decline": True}
            deb = v + IMP["diabetes_t1"]["add_flat"]
            why = f"Type 1, age {self.age}, A1c {a1c} ({how}): T2 grid +{v} plus +50 (DM-3)"
            if match(a, IMP["diabetes_t1"]["pump_credit"]["match"]):
                deb -= 25; why += "; pump/CGM with A1c < 7 at 40+ -25"
            return {"rule": rid("DM-3"), "why": why + "; best Standard", "debits": deb, "cap": "Standard"}
        if v == "decline":
            return {"rule": rid("DM-2"), "why": f"age {self.age}, A1c {a1c} ({how}): grid Decline", "decline": True}
        deb, parts = v, [f"age {self.age}, A1c {a1c} ({how}): grid +{v} (DM-2)"]
        for ad in e.get("add", []):
            if ad["match"] == {"cad": True}:
                continue   # CMB-2 handled at combination step
            if match(a, ad["match"]):
                deb += ad["debits"]; parts.append(f"{self.desc(ad['match'], a)} +{ad['debits']}")
        cap = "Standard"
        bo = e.get("best_override")
        if bo and not a.get("insulin") and a1c < 7.0 and self.age >= 60 and deb == 0:
            cap = bo["best"]; parts.append("non-insulin, A1c < 7, age 60+: best Standard Plus (DM-2.5)")
        return {"rule": rid("DM-2"), "why": "; ".join(parts) + f"; best {cap}", "debits": deb, "cap": cap}

    def rate_cancer(self, e, a, src):
        t = a.get("type")
        ys = a.get("years_since_tx")
        if t is None and a.get("_label"):
            t = cancer_type_from_label(a["_label"])
            if t and ys is None and a.get("years_since_dx") is not None:
                ys = max(0.0, round(a["years_since_dx"] - 0.5, 1))
                self.gry("GRY-5", f"Cancer rated from the application only ({a['_label']})", f"{t.replace('_', ' ')}, ~{ys} yrs since treatment",
                         ["Postpone pending pathology/oncology APS"], "APS-6: type from the stated diagnosis; treatment date estimated from diagnosis date.",
                         ("APS-6", "CA-1"))
            if t and "stage" not in a and re.search(r"stage (I+V?)", a["_label"]):
                a["stage"] = re.search(r"stage (I+V?)", a["_label"]).group(1)
            if t and t in STAGE_ORDER and "stage" not in a and not t.startswith(("thyroid", "hodgkin")):
                a["stage"] = None
        if t is None or ys is None:
            return {"rule": rid("CA"), "why": f"cancer type/treatment date not documented ({src}) - Postpone pending pathology/APS",
                    "postpone": 6}
        if a.get("recurrence"):
            return {"rule": rid("CA-2", "CA"), "why": "recurrence - Decline", "decline": True}
        note = ""
        if "stage" in IMP["cancer"]["attributes"] and a.get("stage") is None and t in STAGE_ORDER and STAGE_ORDER[t] != t:
            worse = STAGE_ORDER[t]
            self.gry("GRY-6", f"Cancer stage not documented ({t.replace('_', ' ')})", f"rate as next worse stage ({worse.replace('_', ' ')})",
                     ["Postpone pending pathology", f"rate as {t.replace('_', ' ')}"], "CA-1: unknown stage -> next worse stage.", ("CA-1",))
            note = f"; stage not documented - rated as {worse.replace('_', ' ')} (CA-1)"
            t = worse
        rows = e["types"].get(t)
        if not rows:
            return {"rule": rid("MISC-3"), "why": f"{t} not in CA table - MD", "debits": 0}
        row = next((r for r in rows if r["years"][0] <= ys < r["years"][1]), rows[-1])
        out = row.get("outcome")
        base = f"{t.replace('_', ' ')}, {ys} yrs since treatment{note}"
        cap = row.get("best", "Standard") if t != "bcc_scc" else None
        if out == "decline":
            return {"rule": rid("CA-1", "CA"), "why": base + " - Decline", "decline": True}
        if out == "postpone":
            return {"rule": rid("CLS-7.3", "CA"), "why": base + " - within postpone window", "postpone": 12}
        r = {"rule": rid("CA-1", "CA"), "why": base, "debits": row.get("debits", 0) if isinstance(row.get("debits", 0), int) else 0,
             "cap": cap}
        if out == "md":
            r["why"] += " - MD referral"
        if row.get("fe"):
            fe = row["fe"]
            r["fe"] = FlatExtra(per_thousand=fe["per_k"], years=fe.get("years"), reason=f"cancer ({t.replace('_', ' ')})")
            r["why"] += f": FE ${fe['per_k']:g}/1000 x {fe.get('years')} yrs"
        if cap:
            r["why"] += f"; best {cap}"
        return r

    def rate_egfr(self, egfr, src, key="ckd"):
        rows = LABS["renal"]["egfr_rows"]
        if egfr < 15:
            return {"rule": rid("REN-1"), "why": f"eGFR {egfr} < 15 - Decline", "decline": True}
        for lo, d in rows:
            if egfr >= lo:
                if isinstance(d, dict):
                    d = d["under60"] if self.age < 60 else d["60plus"]
                return {"rule": rid("REN-1"), "why": f"eGFR {egfr} ({src}): +{d}", "debits": d}
        return {"rule": rid("REN-1"), "why": f"eGFR {egfr}", "debits": 0}

    def rate_protein(self, v, src):
        for hi, d in LABS["renal"]["proteinuria"]:
            if hi is None or v <= hi:
                return {"rule": rid("REN-2"), "why": f"urine protein {v} mg/dL ({src}): +{d}", "debits": d}

    def rate_aud(self, a, src):
        ab = a.get("abstinent_years")
        rel = a.get("relapses", 0)
        if ab is None:
            return {"rule": rid("ALC"), "why": "alcohol use disorder, abstinence not documented - Postpone pending APS", "postpone": 6}
        if rel >= NM["alcohol"]["relapse_decline_count"]:
            return {"rule": rid("ALC"), "why": f"{rel} relapses - Decline", "decline": True}
        row = next(r for r in NM["alcohol"]["aud_abstinence"] if r["max"] is None or ab < r["max"])
        if row.get("outcome") == "postpone":
            return {"rule": rid("CLS-7.7"), "why": f"treated alcohol use disorder, abstinent {ab} yrs (< 1) - Postpone 12 mo", "postpone": 12}
        d = row.get("debits", 0) + (NM["alcohol"]["relapse_add"] if rel else 0)
        cap = row.get("best_class")
        why = f"treated alcohol use disorder, abstinent {ab} yrs: +{row.get('debits', 0)}" + (f"; relapse +{NM['alcohol']['relapse_add']}" if rel else "")
        return {"rule": rid("ALC"), "why": why + (f"; best {cap}" if cap else ""), "debits": d, "cap": cap}

    def rate_drugs(self, a, src):
        if a.get("maintenance"):
            m = a.get("maintenance_years", 0)
            if m < 2:
                return {"rule": rid("DRG-4"), "why": f"opioid use disorder on maintenance {m} yrs (< 2) - Decline", "decline": True}
            return {"rule": rid("DRG-4"), "why": f"opioid use disorder, stable maintenance {m} yrs: +100 (MD)", "debits": 100}
        y = a.get("years_since_last_use")
        sub = a.get("substance", "illicit drug")
        if y is None:
            return {"rule": rid("DRG-2"), "why": f"{sub} misuse, last use not documented - Decline pending records", "decline": True}
        if y < 5:
            return {"rule": rid("DRG-2", "CLS-8.4"), "why": f"{sub} misuse, last use {y} yrs ago (< 5) - Decline", "decline": True}
        if y < 10:
            return {"rule": rid("DRG-2"), "why": f"{sub}, abstinent {y} yrs: +50", "debits": 50}
        return {"rule": rid("DRG-2"), "why": f"{sub}, abstinent {y} yrs (> 10): 0, best Standard Plus", "debits": 0, "cap": "Standard Plus"}

    # ------------------------------------------------------------------ build / BP / lipids
    def build(self):
        f = self.one("paramed", "build")
        if not f:
            sb = self.one("app_answer", "stated_build")
            m = re.match(r"(\d+)'(\d+)\" ([\d.]+) lbs", sb["value"]) if sb else None
            if not m:
                return
            h, w = int(m.group(1)) * 12 + int(m.group(2)), float(m.group(3))
            fx, src = [sb], "stated (no paramed)"
        else:
            h, w = f["value"]["height_in"], f["value"]["weight_lb"]
            fx, src = [f], "measured"
        bmi = w * 703 / (h * h)
        self.bmi = bmi
        bands = BUILD["upper_bands"]
        i = next((i for i, b in enumerate(bands) if bmi <= b["max_bmi"] + 1e-9), None)
        hstr = f"{int(h // 12)}'{h % 12:g}\" {w:g} lb ({src}), BMI {bmi:.1f}"
        wl = self.one("app_answer", "weight_change")
        if i is None:
            self.add(fx, rid("BLD-1.4"), f"Build {hstr}: over the +250 column - Decline.", decline=True, key="build")
            self.build_col = None
            return
        if bmi < BUILD["lower_bands"][0]["min_bmi"]:
            lows = BUILD["lower_bands"]
            lb = next((b for b in lows if bmi >= b["min_bmi"]), None)
            if lb is None:
                self.add(fx, rid("BLD-1.5", "CLS-7.11"), f"Build {hstr}: below the lowest band, no explanation in file - Postpone.",
                         postpone=6, key="build")
            else:
                d = lb.get("debits", 0)
                self.add(fx, rid("BLD-1"), f"Build {hstr}: underweight band '{lb.get('label')}' +{d}.", debits=d, key="build",
                         cap=lb.get("best_class"))
            self.build_col = "Standard"
            return
        b = bands[i]
        col = b["label"]
        j = i
        if self.age >= 70 and 1 <= i <= 4:
            j = i - 1; col = bands[j]["label"]
        self.build_col = bands[j]["best_class"] or "Standard"
        self.build_debits = b["debits"]
        msg = f"Build {hstr}: {b['label']} column" + (f"; age 70+ one column more lenient -> {col} (BLD-1.8)" if j != i else "")
        if b["debits"]:
            self.add(fx, rid("BLD-1.2", "BLD-1"), msg + f": +{b['debits']}.", debits=b["debits"], key="build", chapter="BLD")
        else:
            self.add(fx, rid("BLD-1.1", "BLD-1"), msg + f" (preferred matrix build row: {self.build_col}).", key="build")
        lo = bands[i - 1]["max_bmi"] if i else 0
        if b["max_bmi"] - bmi < 0.15 * 1 or (i and bmi - lo < 0.15):
            pass
        bar = [x for x in self.of("aps_finding") if "bariatric" in json.dumps(x["value"]).lower()]
        if wl:
            pass

    def bp_lipids(self):
        s, d, fx = self.bp_average()
        self.bp = (s, d)
        self.bp_fx = fx
        if s is not None and "hypertension" not in self.rated_keys:
            n = len(fx)
            self.add(fx, rid("BP-1"), f"Blood pressure average {s}/{d} ({'paramed' if n == 1 else 'paramed + APS readings in last 12 months'}); "
                     f"untreated - used for preferred matrix (CLS-5).", key="bp")
            if s > 150 or d > 95:
                rows = NM["htn"]["rows"]
                rs = next((k for k, r in enumerate(rows) if s <= r[0]), len(rows))
                rd = next((k for k, r in enumerate(rows) if d <= r[1]), len(rows))
                if self.age >= 60 and rs > 0:
                    rs -= 1
                r = max(rs, rd)
                if r >= len(rows):
                    self.add(fx, rid("BP-3", "BP-4"), f"Untreated average {s}/{d} > 180/110 - Postpone pending evaluation.", postpone=3, key="bp")
                elif rows[r][2]:
                    self.add(fx, rid("BP-4"), f"Untreated average {s}/{d} > 150/95: rated on the HTN table as untreated hypertension "
                             f"+{rows[r][2]}; APS advised.", debits=rows[r][2], key="bp", chapter="HTN")
        tc, hdl, ratio = (self.one("lab_value", k) for k in ("tc", "hdl", "tc_hdl_ratio"))
        self.lip = None
        if tc and (hdl or ratio):
            r = ratio["value"] if ratio else round(tc["value"] / hdl["value"], 1)
            self.lip = (tc["value"], r, hdl["value"] if hdl else None)
            fx = [x for x in (tc, hdl, ratio) if x]
            statin = [f for f in self.of("rx_fill") if f["key"].endswith("statin") or f["key"] == "ezetimibe"]
            self.statin = bool(statin)
            rows = NM["lipids"]["rows"]
            k1 = next((k for k, rr in enumerate(rows) if tc["value"] <= rr[0]), len(rows))
            k2 = next((k for k, rr in enumerate(rows) if r <= rr[1]), len(rows))
            k = max(k1, k2)
            deb = rows[k][2] if k < len(rows) else NM["lipids"]["over_last"]["debits"]
            txt = f"TC {tc['value']:g}, HDL {hdl['value']:g}, ratio {r}" if hdl else f"TC {tc['value']:g}, ratio {r} (ratio-only report)"
            if deb:
                self.add(fx, rid("LIP-3", "LIP-3.1"), f"Lipids {txt}: +{deb} (worse of TC and ratio rows).", debits=deb, key="lipids", chapter="LIP")
            elif hdl and hdl["value"] < 30:
                self.add(fx, rid("LIP-4"), f"Lipids {txt}: HDL < 30 alone +15.", debits=15, key="lipids", chapter="LIP")
            else:
                self.add(fx, rid("LIP-1", "LIP-2"), f"Lipids {txt}" + (" on statin (treated values, LIP-7)" if statin else "") + " - preferred matrix row.",
                         key="lipids")
            tg = self.one("lab_value", "triglycerides")
            fast = next((c.get("fasting") for did, c in self.content["docs"].items() if self.dtype.get(did) == "lab_blood"), True)
            if tg and tg["value"] > 500:
                if fast is False:
                    self.add([tg], rid("LIP-6"), f"Triglycerides {tg['value']:g} on a non-fasting specimen - ignored.", key="lipids")
                else:
                    d2 = 25 if tg["value"] <= 1000 else 50
                    self.add([tg], rid("LIP-5"), f"Triglycerides {tg['value']:g}: +{d2}.", debits=d2, key="lipids", chapter="LIP")

    # ------------------------------------------------------------------ other labs
    def labs(self):
        L = {f["key"]: f for f in self.of("lab_value")}
        has = set(self.rated_keys) | set(self.conds)
        alc_rated = False
        def uln(k):
            return LABS["analytes"][k]["uln"]
        # liver panel
        liv = [L[k] for k in ("ast", "alt") if k in L and L[k]["value"] > 1.5 * uln(k)]
        if liv:
            mx = max(f["value"] / uln(f["key"]) for f in liv)
            vals = ", ".join(f"{f['key'].upper()} {f['value']:g} ({f['value'] / uln(f['key']):.1f}x ULN)" for f in liv)
            explained = has & LIVER_KEYS or self.alcohol_signal()
            if explained:
                self.add(liv, rid("CMB-3"), f"{vals}: attributed to {', '.join(sorted(explained)) if isinstance(explained, set) and explained else 'alcohol use'} "
                         "- rated there, not added (same finding).", key="lab")
            elif mx > 5:
                self.add(liv, rid("LAB-2"), f"{vals}: > 5x ULN unexplained - Postpone pending workup.", postpone=6, key="lab")
            elif mx > 3:
                self.add(liv, rid("LAB-2"), f"{vals}: > 3x ULN - APS required; rated +50 pending explanation.", debits=50, key="lab")
            else:
                self.add(liv, rid("LAB-2"), f"{vals}: 1.5-3x ULN unexplained: +25.", debits=25, key="lab")
        g, cdt = L.get("ggt"), L.get("cdt")
        gx = [x for x in (g,) if x and x["value"] > 2 * uln("ggt")]
        cx = [x for x in (cdt,) if x and x["value"] > LABS["analytes"]["cdt"]["normal_max"]]
        if gx or cx:
            vals = ", ".join(f"{f['key'].upper()} {f['value']:g}" for f in gx + cx)
            if has & LIVER_KEYS or self.alcohol_signal():
                self.add(gx + cx, rid("CMB-3"), f"{vals}: alcohol/liver marker - folded into the alcohol/liver rating (no double count).", key="lab")
            else:
                d = 0
                if gx:
                    r = g["value"] / uln("ggt")
                    d = 25 if r <= 3 else 50
                    if cx and r <= 3:
                        d = 50
                elif cx:
                    d = 25 if cdt["value"] < 2.5 else 50
                self.add(gx + cx, rid("LAB-2"), f"{vals}: unexplained alcohol marker(s): +{d}.", debits=d, key="lab")
        ap = L.get("alk_phos")
        if ap and ap["value"] > 1.5 * uln("alk_phos"):
            self.add([ap], rid("LAB-2"), f"Alkaline phosphatase {ap['value']:g} > 1.5x ULN: +25.", debits=25, key="lab")
        bili = L.get("bilirubin")
        if bili and bili["value"] > 1.5:
            self.add([bili], rid("LAB-2"), f"Bilirubin {bili['value']:g}: " + ("isolated <= 3.0 with normal LFTs - Gilbert's, 0." if bili["value"] <= 3 and not liv else "APS."), key="lab")
        alb = L.get("albumin")
        if alb and alb["value"] < 3.5:
            self.add([alb], rid("LAB-2"), f"Albumin {alb['value']:g} < 3.5: +25.", debits=25, key="lab")
        hb = L.get("hemoglobin")
        if hb:
            lo = LABS["analytes"]["hemoglobin"]["normal"][self.sex][0]
            if hb["value"] < 10:
                self.add([hb], rid("LAB-2"), f"Hemoglobin {hb['value']:g} < 10 - Postpone pending workup.", postpone=6, key="lab")
            elif hb["value"] < lo:
                if "anemia" in has:
                    self.add([hb], rid("CMB-3"), f"Hemoglobin {hb['value']:g}: explained by documented anemia - rated there.", key="lab")
                else:
                    self.add([hb], rid("LAB-2"), f"Hemoglobin {hb['value']:g} below normal, unexplained: +25.", debits=25, key="lab")
        eg = L.get("egfr")
        if eg and eg["value"] < 60:
            if has & RENAL_KEYS & {"ckd", "polycystic_kidney"}:
                self.add([eg], rid("CMB-3"), f"eGFR {eg['value']:g}: consistent with documented kidney disease - rated there.", key="lab")
            else:
                r = self.rate_egfr(eg["value"], "lab")
                self.add([eg], r["rule"], f"Undisclosed reduced kidney function: {r['why']}.", debits=r.get("debits", 0),
                         decline=r.get("decline", False), key="lab", chapter="REN")
        up = L.get("urine_protein")
        if up and up["value"] > 30:
            if has & {"proteinuria", "ckd", "polycystic_kidney"} or ("diabetes_t2" in has and self.conds.get("diabetes_t2", {}).get("microalbuminuria")):
                self.add([up], rid("CMB-3"), f"Urine protein {up['value']:g}: rated under the renal/diabetes chapter (use the higher, not the sum).", key="lab")
            else:
                r = self.rate_protein(up["value"], "lab")
                self.add([up], r["rule"], f"Proteinuria on urinalysis: {r['why']}.", debits=r["debits"], key="lab", chapter="REN")
        a1c = L.get("a1c")
        if a1c and a1c["value"] >= 5.7 and not has & {"diabetes_t2", "diabetes_t1", "prediabetes"}:
            if a1c["value"] >= 6.5:
                v = grid_lookup("diabetes_t2", self.age, a1c["value"])
                if v == "decline":
                    self.add([a1c], rid("DM-2"), f"A1c {a1c['value']:g} - undisclosed diabetes: grid Decline.", decline=True, key="lab")
                else:
                    self.add([a1c], rid("DM-2"), f"A1c {a1c['value']:g} - undisclosed/undiagnosed diabetes: grid +{v}, best Standard.",
                             debits=v, cap="Standard", key="lab", chapter="DM")
            else:
                p = first_profile("prediabetes", {"a1c_avg": a1c["value"], "age": self.age})
                self.add([a1c], rid("DM-1"), f"A1c {a1c['value']:g} - prediabetic range: profile '{p['id']}' +{p.get('debits', 0)}" +
                         (f", best {p['best']}" if p.get("best") else "") + ".", debits=p.get("debits", 0), cap=p.get("best"), key="lab")
        elif a1c and a1c["value"] >= 5.7:
            self.add([a1c], rid("CMB-3"), f"A1c {a1c['value']:g}: part of the diabetes rating above.", key="lab")
        for gk in ("glucose_fasting", "glucose_random"):
            gl = L.get(gk)
            if gl and gl["relevant"]:
                self.add([gl], rid("LAB-2"), f"{gk.replace('_', ' ')} {gl['value']:g}: evaluated with A1c (" +
                         (f"A1c {a1c['value']:g}" if a1c else "no A1c") + ") - no separate rating.", key="lab")
        ug = L.get("urine_glucose")
        if ug and ug["value"]:
            self.add([ug], rid("LAB-2"), "Urine glucose positive: " + ("explained by diabetes." if has & {"diabetes_t2", "diabetes_t1"} else
                     "with A1c in range - renal glycosuria, 0."), key="lab")
        ur = L.get("urine_rbc")
        if ur and ur["value"] > 5:
            self.add([ur], rid("LAB-2"), f"Urine RBC {ur['value']}/hpf: repeat urinalysis advised; not ratable alone.", key="lab")
        psa = L.get("psa")
        if psa and psa["relevant"]:
            lim = next(m for a, m in LABS["analytes"]["psa"]["age_max"] if a is None or self.age <= a)
            if "cancer" in has and str(self.conds.get("cancer", {}).get("type", "")).startswith("prostate"):
                self.add([psa], rid("CMB-3"), f"PSA {psa['value']:g}: known prostate cancer - rated there.", key="lab")
            elif psa["value"] > 10:
                self.add([psa], rid("LAB-2"), f"PSA {psa['value']:g} > 10 untreated - Postpone.", postpone=6, key="lab")
            elif psa["value"] > lim:
                self.add([psa], rid("LAB-2"), f"PSA {psa['value']:g} above age limit {lim}: urology APS; not rated pending.", key="lab")
        bnp = L.get("nt_probnp")
        if bnp and bnp["relevant"]:
            if has & CARDIAC_KEYS:
                self.add([bnp], rid("CMB-3"), f"NT-proBNP {bnp['value']:g}: cardiac chapter already rated.", key="lab")
            else:
                v = bnp["value"]
                nmax = 449 if self.age >= 75 else 124
                d = 0 if v <= nmax else 25 if v <= 299 else 75 if v <= 899 else None
                if d is None:
                    self.add([bnp], rid("LAB-2"), f"NT-proBNP {v:g} >= 900 unexplained - Decline.", decline=True, key="lab")
                elif d == 0:
                    self.add([bnp], rid("LAB-2"), f"NT-proBNP {v:g}: within the age-adjusted normal (< {nmax + 1} at age {self.age}).", key="lab")
                else:
                    self.add([bnp], rid("LAB-2"), f"NT-proBNP {v:g} unexplained: +{d}.", debits=d, key="lab")
        hiv = [f for f in self.of("lab_value", "hiv") if f["value"]]
        if hiv:
            if "hiv" in has:
                self.add(hiv, rid("IMM-1"), "HIV positive - known, rated under IMM above.", key="lab")
            else:
                self.add(hiv, rid("IMM-1"), "HIV positive, not disclosed - Decline pending records.", decline=True, key="lab")
                self.misrep.append("medical")
        coc = [f for f in self.of("lab_value", "cocaine") if f["value"]]
        if coc:
            self.add(coc, rid("DRG-2", "CLS-8.4"), "Cocaine metabolite positive - Decline.", decline=True, key="lab")

    def alcohol_signal(self):
        dpw = [f["value"] for f in self.of("app_answer", "alcohol_dpw")] + [f["value"] for f in self.of("questionnaire", "ALCQ:drinks_per_week")]
        cdt = self.one("lab_value", "cdt")
        return bool((dpw and max(dpw) > 14) or (cdt and cdt["value"] >= 1.7))

    # ------------------------------------------------------------------ FH, MVR, ALC/DRG, OCC/AVO/AVI/TRV
    def family(self):
        fh = self.of("app_answer", "family_history")
        counted = {"MI", "CAD", "stroke", "sudden cardiac death", "cardiomyopathy", "breast cancer", "colon cancer", "ovarian cancer",
                   "prostate cancer", "pancreatic cancer", "melanoma"}
        cvd = {"MI", "CAD", "stroke", "sudden cardiac death", "cardiomyopathy"}
        rel = [f for f in fh if f["value"]["condition"] in counted and f["value"]["relation"] in NM["family_history"]["relatives"]]
        dx65 = [f for f in rel if (f["value"].get("age_at_onset") or f["value"].get("age_at_death") or 99) < 65]
        d60 = [f for f in rel if f["value"].get("age_at_death") and f["value"]["age_at_death"] < 60]
        cvd60 = [f for f in d60 if f["value"]["condition"] in cvd]
        if self.age >= 70:
            self.fh_level = "Elite"
            if fh:
                self.add(fh, rid("FH-4", "CLS-5.4"), "Family history waived at age 70+.", key="fh")
            return
        lvl = "Elite" if not dx65 else "Preferred Plus" if not d60 else "Preferred" if len(d60) <= 1 else "Standard Plus"
        self.fh_level = lvl
        if not fh:
            return
        desc = "; ".join(f"{f['value']['relation']} {f['value']['condition']}" + (f" d.{f['value']['age_at_death']}" if f['value'].get('age_at_death') else
                         f" dx {f['value'].get('age_at_onset')}") for f in rel) or "no parent/sibling CVD or cancer before 65"
        if len(cvd60) >= 2:
            self.add(rel, rid("FH-2"), f"Family history: {desc} - two parent/sibling CVD deaths < 60: +25.", debits=25, key="fh", chapter="FH")
        else:
            self.add(rel or fh, rid("FH-1", "FH-1.1"), f"Family history: {desc} - preferred matrix FH row meets {lvl}.", key="fh")

    def mvr(self):
        ev = self.of("mvr_violation")
        self.mvr_level = "Elite"
        doc = next((d for d in self.docs if self.dtype[d] == "mvr"), None)
        if not ev:
            if doc:
                fx = self.one("app_answer", "dui_10y")
                if fx:
                    self.add([fx], rid("MVR-1"), f"Application DUI question: {fx['value']}; MVR clear.", key="mvr")
            return
        minors, majors, duis, other, susp = [], [], [], [], []
        for f in ev:
            c = MVRC[f["key"]]
            y = yrs(date.fromisoformat(f["as_of"]), self.app_date)
            cls = c["class"]
            if f["key"] == "L02":
                susp.append(f)
            elif cls == "dui":
                duis.append((y, f))
            elif cls == "major" or c.get("counts_as") == "major":
                (majors if y <= 5 else other).append(f if y <= 5 else f)
            elif cls == "minor" or c.get("counts_as") == "minor":
                (minors if y <= 3 else other).append(f)
            else:
                other.append(f)
        if other:
            self.add(other, rid("MVR-1"), f"{len(other)} MVR item(s) non-moving, not-at-fault, or outside lookback - ignored.", key="mvr")
        nmin, nmaj = len(minors), len(majors)
        if minors:
            row = next((d for mx, d in NM["mvr"]["minor_3yr"] if nmin <= mx), None)
            if nmin >= NM["mvr"]["minor_decline_at"]:
                self.add(minors, rid("MVR-3"), f"{nmin} minor violations in 3 yrs - Decline.", decline=True, key="mvr")
            else:
                self.add(minors, rid("MVR-3"), f"{nmin} minor moving violation(s) in 3 yrs: +{row}.", debits=row, key="mvr", chapter="MVR")
        if majors:
            if nmaj >= NM["mvr"]["major_decline_at"]:
                self.add(majors, rid("MVR-3"), f"{nmaj} major violations in 5 yrs - Decline.", decline=True, key="mvr")
            else:
                d = NM["mvr"]["major_5yr"][nmaj]
                self.add(majors, rid("MVR-3", "MVR-3.1"), f"{nmaj} major violation(s) in 5 yrs: +{d}.", debits=d, key="mvr", chapter="MVR")
        app_dui = self.one("app_answer", "dui_10y")
        if duis:
            duis.sort(key=lambda x: x[0])
            y, f = duis[0]
            in5 = [x for x in duis if x[0] <= 5]
            fx = [x[1] for x in duis] + susp
            if app_dui and app_dui["value"] == "No" and any(x[0] <= 10 for x in duis):
                self.add([app_dui], rid("GEN-2.1", "GEN-2.2"), "Application denies DUI in 10 yrs; MVR shows DUI - misrepresentation (MISREP).", key="mvr")
                self.misrep.append("mvr")
            elif app_dui:
                self.add([app_dui], rid("MVR-1"), f"Application DUI answer: {app_dui['value']}.", key="mvr")
            if len(in5) >= 2:
                self.add(fx, rid("CLS-8.3"), f"{len(in5)} DUIs within 5 yrs - Decline.", decline=True, key="mvr")
            elif y < 1 or susp:
                self.add(fx, rid("CLS-7.6"), f"DUI {y} yrs ago" + (" with license suspended" if susp else "") + " - Postpone 12 months from DUI.",
                         postpone=12, key="mvr")
            else:
                row = next(r for r in NM["mvr"]["dui"] if r["min"] <= y < r["max"]) if y < 10 else None
                if row:
                    self.add(fx, rid("MVR-3", "MVR-3.3"), f"DUI {y} yrs ago: +{row.get('debits', 0)}, best {row.get('best_class')}.",
                             debits=row.get("debits", 0), cap=row.get("best_class"), key="mvr", chapter="MVR")
                else:
                    self.add(fx, rid("MVR-3"), f"DUI {y} yrs ago (> 10): not rated.", key="mvr")
            self.mvr_dui_years = y
        elif susp:
            self.add(susp, rid("CLS-7.6"), "License currently suspended (DUI) - Postpone.", postpone=12, key="mvr")
        # preferred matrix MVR row
        min5 = len([f for f in ev if MVRC[f["key"]]["class"] in ("minor",) and yrs(date.fromisoformat(f["as_of"]), self.app_date) <= 5])
        dy = min((x[0] for x in duis), default=99)
        lv = "Standard"
        for c in PREF[:4]:
            m = CLS["preferred_matrix"]["classes"][c]["mvr"]
            n = min5 if c == "Elite" else nmin
            if n <= m["max_minor"] and (m.get("dui_free_years") is None and dy == 99 and not majors if c == "Elite" else dy >= (m.get("dui_free_years") or 0)):
                lv = c
                break
        self.mvr_level = lv

    def alcohol_drugs(self):
        app = self.one("app_answer", "alcohol_dpw")
        q = self.one("questionnaire", "ALCQ:drinks_per_week")
        cdt = self.one("lab_value", "cdt")
        ggt = self.one("lab_value", "ggt")
        srcs = [f for f in (app, q) if f]
        dpw = max([f["value"] for f in srcs], default=0)
        self.alc_level = None
        abnormal = (cdt and cdt["value"] >= 1.7) or (ggt and ggt["value"] > 2 * LABS["analytes"]["ggt"]["uln"])
        if "alcohol_use_disorder" in self.rated_keys:
            if srcs:
                self.add(srcs, rid("ALC"), f"Current alcohol {dpw:g} drinks/wk reported; history rated under alcohol use disorder.", key="alc")
            return
        fx = srcs + [x for x in (cdt, ggt) if x and abnormal]
        if dpw > 35:
            self.add(fx, rid("ALC"), f"Alcohol {dpw:g} drinks/wk (> 35): +100 (MD).", debits=100, key="alc", chapter="ALC")
        elif dpw > 21 or (abnormal and dpw > 14):
            self.add(fx, rid("ALC", "ALC-1"), f"Alcohol {dpw:g} drinks/wk" + (" with abnormal CDT/GGT" if abnormal else "") + ": +50, best Standard.",
                     debits=50, cap="Standard", key="alc", chapter="ALC")
        elif abnormal and cdt and cdt["value"] >= 2.5:
            self.add(fx, rid("ALC-2"), f"CDT {cdt['value']:g} >= 2.5 with stated {dpw:g} drinks/wk: treat as 22-35 row, +50, best Standard "
                     "(objective evidence controls, GEN-2.1).", debits=50, cap="Standard", key="alc", chapter="ALC")
            self.gry("GRY-11", "Stated alcohol intake conflicts with lab markers", "22-35 drinks/wk row (+50)",
                     ["rate on stated intake with lab-only debits"], "ALC-2: CDT >= 2.5 overrides stated intake.", ("ALC-2",))
        elif abnormal:
            self.add(fx, rid("ALC", "LAB-2"), f"Alcohol {dpw:g} drinks/wk with abnormal CDT/GGT: 22-35 row, +50, best Standard.",
                     debits=50, cap="Standard", key="alc", chapter="ALC")
            self.gry("GRY-11", "Stated alcohol intake conflicts with lab markers", "22-35 drinks/wk row (+50)",
                     ["15-21 row (+25)", "lab debits only"], "Abnormal CDT/GGT puts the case in the 22-35 row (ALC table).", ("ALC-1",))
        elif dpw > 14:
            self.add(fx, rid("ALC"), f"Alcohol {dpw:g} drinks/wk, normal LFT/CDT: +25, best Standard Plus.", debits=25, cap="Standard Plus",
                     key="alc", chapter="ALC")
        elif srcs and any(f["relevant"] for f in srcs):
            self.add(srcs, rid("ALC"), f"Alcohol {dpw:g} drinks/wk - within limits.", key="alc")
        if app and q and app["value"] != q["value"]:
            self.gry("GRY-11", "Alcohol quantity differs between application and questionnaire", f"higher value {dpw:g}/wk (ALC-1)",
                     ["lab-consistent estimate"], "ALC-1 uses the higher stated amount.", ("ALC-1",))
        mj = self.one("app_answer", "marijuana")
        if mj:
            n = mj["value"]
            row = next(r for r in NM["drugs"]["marijuana"] if r["max"] is None or n <= r["max"])
            self.add([mj], rid("DRG-3", "TOB-7"), f"Marijuana {n}x/week: +{row['debits']}, best {row['best_class']}.", debits=row["debits"],
                     cap=row["best_class"], key="drg", chapter="DRG")
        for f in self.of("questionnaire", prefix="ALCQ:"):
            if f["fact_id"] not in self.cited:
                self.add([f], rid("REQ-2.4", "ALC"), f"Alcohol questionnaire {f['key'].split(':')[1].replace('_', ' ')}: {f['value']}.", key="alc")

    def occupation_avocation(self):
        occ_f = self.one("app_answer", "occupation")
        occ = occ_f["value"]
        oc = OCC.get(occ, {"class": "1A"})
        cl = oc["class"]
        self.occ_class = cl
        if "deploying" in occ:
            self.add([occ_f], rid("OCC-1", "CLS-7"), f"Occupation {occ}: deployment to combat zone within 12 months - Postpone.", postpone=12, key="occ")
        elif cl == "4A":
            hi = occ in ("commercial fisherman", "logger", "crop duster pilot")
            fe = 5.0 if hi else 2.5
            self.add([occ_f], rid("OCC"), f"Occupation {occ} (class 4A): FE ${fe:g}/1000 permanent.",
                     fe=FlatExtra(per_thousand=fe, years=None, reason=f"occupation ({occ})"), key="occ", chapter="OCC")
        elif cl == "5A":
            self.add([occ_f], rid("OCC"), f"Occupation {occ} (class 5A): FE $7.50/1000 (Senior UW).",
                     fe=FlatExtra(per_thousand=7.5, years=None, reason=f"occupation ({occ})"), key="occ", chapter="OCC")
        else:
            self.add([occ_f], rid("OCC"), f"Occupation {occ} (class {cl}): no rating" + ("; Elite not available (police/fire)." if occ in
                     ("police officer", "firefighter") else "."), cap="Preferred Plus" if any(w in occ for w in ("police", "firefighter")) else None, key="occ")
        self.avo_fe = 0.0
        self.avo_any = False
        acts = []
        q = self.one("questionnaire", "AVOQ:activities")
        app_av = self.of("app_answer", "avocation")
        if q:
            acts = [(a, q) for a in q["value"]]
        else:
            acts = [(f["value"], f) for f in app_av]
        for f in app_av:
            if f["fact_id"] not in self.cited and not f["relevant"]:
                self.add([f], rid("AVO-1.1"), f"Avocation {f['value']['activity']}: not a listed hazardous activity - no rating.", key="avo")
        for a, f in acts:
            res = self.rate_avocation(a)
            if res is None:
                continue
            fx = [f] + [x for x in app_av if x["value"].get("activity") == a["activity"] and x is not f]
            self.avo_any = True
            self.add(fx, res["rule"], res["why"], fe=res.get("fe"), decline=res.get("decline", False), cap=res.get("cap"), key="avo", chapter="AVO")
        haz = self.one("app_answer", "hazardous_avocation")
        if haz:
            mibs = [x for x in self.of("mib_code") if x["key"][:3] in ("021", "022", "023", "024", "025")]
            self.add([haz] + mibs, rid("GEN-2.1", "MIB-6"), "Application denies hazardous activities; " +
                     ("MIB/questionnaire shows otherwise - misrepresentation noted (MISREP)." if (mibs or q) else "no contrary evidence."), key="avo")
            if mibs or q:
                self.misrep.append("avocation")
        for f in self.of("mib_code"):
            if f["key"][:3] in ("021", "022", "023", "024", "025", "020") and f["fact_id"] not in self.cited:
                self.add([f], rid("MIB-6"), f"MIB {self.mib_decode(f['key'])}: avocation alert - see AVO review.", key="avo")
        # travel
        tr = [f for f in self.of("app_answer", "foreign_travel")]
        forq_t = self.one("questionnaire", "FORQ:travel")
        for f in tr:
            v = f["value"]
            t = self.tier(v["country"])
            wk = v["weeks_per_year"]
            col = 0 if wk <= 4 else 1 if wk <= 13 else 2
            cell = NM["travel"][t][col]
            fx = [f] + ([forq_t] if forq_t else [])
            base = f"Travel to {v['country']} (Tier {t}) {wk:g} wks/yr ({v['purpose']})"
            if cell == "none" or v["purpose"] == "vacation" and t in "AB":
                self.add(fx, rid("TRV"), base + ": no rating.", key="trv")
            elif cell == "decline":
                self.add(fx, rid("TRV"), base + ": Decline.", decline=True, key="trv")
            elif "fe" in cell:
                fe = cell["fe"]
                self.add(fx, rid("TRV"), base + f": FE ${fe:g}/1000" + (f", max face ${cell['max_face']:,}" if cell.get("max_face") else "") + ".",
                         fe=FlatExtra(per_thousand=fe, years=None, reason=f"foreign travel ({v['country']})"), key="trv", chapter="TRV")
                if cell.get("max_face") and self.app("face") > cell["max_face"]:
                    self.approved_face = min(self.approved_face or self.app("face"), cell["max_face"])
                if cell.get("or_best_class"):
                    self.gry("GRY-0", f"Tier C travel {wk:g} wks/yr", f"FE ${fe:g}/1000", [f"best {cell['or_best_class']} instead of FE"],
                             "TRV table permits FE or class limit.", ("TRV",))
            else:
                self.add(fx, rid("TRV"), base + f": best {cell['best_class']}.", cap=cell["best_class"], key="trv")
        if forq_t and forq_t["fact_id"] not in self.cited:
            self.add([forq_t], rid("TRV-2"), "Foreign questionnaire travel section reviewed.", key="trv")
        for f in self.of("questionnaire", prefix="FORQ:"):
            if f["fact_id"] not in self.cited:
                self.add([f], rid("FN-1"), f"Foreign questionnaire {f['key'].split(':')[1].replace('_', ' ')}: {f['value'] or 'n/a'}.", key="fn")

    def rate_avocation(self, a):
        act = a.get("activity")
        stop = a.get("intends_to_stop")
        yrs_fe = NM["avocations"]["intent_to_stop_temporary_years"] if stop else None
        def fe(x, why, rule="AVO"):
            if stop:
                self.gry("GRY-9", f"Applicant states intent to stop {act.replace('_', ' ')}", f"temporary FE ${x:g} x 2 yrs",
                         [f"permanent FE ${x:g}"], "AVO-1.2 makes the FE temporary when intent to stop is stated.", ("AVO-1.2",))
            cap = "Standard Plus" if x > NM["avocations"]["preferred_max_fe"] else None
            self.avo_fe += x
            return {"rule": rid(rule), "why": why + f": FE ${x:g}/1000 " + (f"x {yrs_fe} yrs (intent to stop, AVO-1.2)" if yrs_fe else "permanent") +
                    (f"; FE > $2.50 -> best Standard Plus (AVO-1.4)" if cap else ""),
                    "fe": FlatExtra(per_thousand=x, years=yrs_fe, reason=f"avocation ({act.replace('_', ' ')})"), "cap": cap}
        if act == "scuba":
            d = a.get("max_depth_ft", 0)
            if d > 200:
                return {"rule": rid("AVO"), "why": f"Scuba to {d} ft (> 200 ft) - Decline", "decline": True}
            if d > 130 or a.get("cave"):
                return fe(5.0, f"Scuba {d} ft{' cave' if a.get('cave') else ''}")
            if d > 100 or a.get("dives_per_year", 0) > 50:
                return fe(2.5, f"Scuba {d} ft, {a.get('dives_per_year', '?')} dives/yr")
            self.avo_any = True
            return {"rule": rid("AVO"), "why": f"Scuba {d} ft, certified, {a.get('dives_per_year')} dives/yr: no rating"}
        if act == "skydiving":
            n = a.get("jumps_per_year", 0)
            return fe(5.0 if n > 50 else 2.5, f"Skydiving {n} jumps/yr")
        if act == "base_jumping":
            return {"rule": rid("AVO"), "why": "BASE jumping - Decline", "decline": True}
        if act == "mountain_climbing":
            alt = a.get("max_altitude_ft", 0)
            if alt > 26000:
                return {"rule": rid("AVO"), "why": f"Climbing to {alt:,} ft (> 26,000) - Decline", "decline": True}
            if alt > 20000 or a.get("technical"):
                return fe(7.5, f"Climbing to {alt:,} ft")
            if alt > 14000:
                return fe(3.0, f"Climbing to {alt:,} ft")
            return {"rule": rid("AVO"), "why": f"Climbing to {alt:,} ft: no rating"}
        if act == "motor_racing":
            if a.get("professional") or a.get("max_mph", 0) > 150:
                return fe(5.0, f"Motor racing (professional / {a.get('max_mph', '?')} mph)")
            return fe(2.5, f"Motor racing, amateur {a.get('events_per_year')} events/yr")
        if act == "hang_gliding":
            n = a.get("flights_per_year", 0)
            return fe(5.0 if n > 25 else 2.5, f"Hang gliding {n} flights/yr")
        if act == "heli_skiing":
            return fe(2.5, "Heli-skiing")
        if act == "rodeo":
            return fe(5.0, "Competitive rodeo")
        if act == "private_aviation":
            return self.rate_aviation(a)
        return None

    def rate_aviation(self, a):
        h, hy = a.get("total_hours", 0), a.get("hours_per_year", 0)
        def fe(x, why, years=None):
            self.avo_fe += x
            cap = "Standard Plus" if x > 2.5 else None
            return {"rule": rid("AVI-1"), "why": why + f": FE ${x:g}/1000" + (f" x {years} yrs" if years else " permanent") +
                    ("; best Standard Plus (AVI-1.2/AVO-1.4)" if cap else ""), "fe": FlatExtra(per_thousand=x, years=years, reason="private aviation"),
                    "cap": cap}
        if a.get("aerobatic"):
            self.gry("GRY-0", "Aerobatic pilot", "FE $7.50/1000", ["FE $5/1000", "FE $10/1000", "aviation exclusion"],
                     "AVI-1 permits $5-$10 or exclusion for aerobatics.", ("AVI-1",))
            return fe(7.5, f"Private pilot, aerobatics, {h} hrs")
        if a.get("aircraft") in ("homebuilt", "experimental", "ultralight"):
            self.gry("GRY-0", "Homebuilt/experimental aircraft", "FE $5/1000", ["FE $2.50/1000"], "AVI-1 range $2.50-$5.", ("AVI-1",))
            return fe(5.0, f"Private pilot, {a['aircraft']} aircraft, {h} hrs")
        if h < 100:
            return fe(2.5, f"Student/new pilot, {h} total hrs", years=2)
        if a.get("ifr") and hy <= 200 and self.age <= 70:
            return {"rule": rid("AVI-1"), "why": f"Private pilot, {h} hrs, {hy} hrs/yr, IFR rated: no aviation rating"}
        if not a.get("ifr") and hy > 100:
            return fe(2.5, f"Private pilot, not IFR, {hy} hrs/yr (> 100)")
        if self.age >= 71:
            return fe(2.5, "Pilot age 71+")
        return {"rule": rid("AVI-1"), "why": f"Private pilot, {h} hrs, {hy} hrs/yr: no aviation rating"}

    def misc_nonmedical(self):
        pt = self.one("app_answer", "pending_tests")
        if pt:
            v = pt["value"]
            if "scheduled" in v and "biopsy" not in v:
                self.add([pt], rid("CLS-7.2"), f"Pending: {v} - Postpone to 3 months post-op.", postpone=3, key="misc")
            else:
                self.add([pt], rid("CLS-7.1"), f"Pending workup: {v} - Postpone until results + 3 months.", postpone=3, key="misc")
        wc = self.one("app_answer", "weight_change")
        if wc:
            self.add([wc], rid("CLS-7.9"), f"Unexplained weight loss ({wc['value']}) - Postpone pending workup.", postpone=6, key="misc")
        cr = self.one("app_answer", "criminal")
        if cr:
            if "pending" in cr["value"]:
                self.add([cr], rid("CLS-7.10"), "Pending felony charge - Postpone until disposition.", postpone=12, key="misc")
            else:
                self.add([cr], rid("CLS-8.5"), f"{cr['value']} (< 2 yrs) - Decline.", decline=True, key="misc")
        for f in self.of("app_answer", "prior_application"):
            self.add([f], rid("GEN-1", "MIB-6"), f"Prior application: {f['value']} - informational; current evidence governs.", key="misc")
        for f in self.of("mib_code"):
            if f["fact_id"] in self.cited:
                continue
            code = f["key"]
            c = MIB["conditions"].get(code[:3], {})
            age_y = yrs(date.fromisoformat(f["value"]), self.app_date)
            if code[:3] == "031":
                self.add([f], rid("MIB-6"), f"MIB {self.mib_decode(code)}: driving alert - checked against MVR.", key="mvr")
            elif c.get("retired") or age_y > 7:
                self.add([f], rid("MIB-3"), f"MIB {self.mib_decode(code)} reported {age_y} yrs ago / retired code - informational only.", key="mib")
            elif code[:3].startswith("01"):
                self.add([f], rid("MIB-6"), f"MIB {self.mib_decode(code)}: insurance-activity code - informational.", key="mib")
            else:
                ro = [x for x in self.of("aps_finding", "rule_out")]
                if ro:
                    self.add([f] + ro, rid("GRY-8", "APS-2"), f"MIB {self.mib_decode(code)} corroborated only by an 'r/o' note in APS - not rated (default).",
                             key="mib")
                    self.gry("GRY-8", "MIB code supported only by an r/o note", "ignore (not rated)", ["rate as mild form (+25)"],
                             "APS-2: rule-outs are suspicions, not diagnoses.", ("APS-2", "MIB-1"))
                else:
                    self.add([f], rid("MIB-4", "MIB-1"), f"MIB {self.mib_decode(code)}: not disclosed, no corroboration in Rx/APS/labs - not rated.",
                             key="mib")
        for f in self.of("aps_finding", "rule_out"):
            if f["fact_id"] not in self.cited:
                self.add([f], rid("APS-2"), f"APS '{f['value']}' - suspicion only, not rated.", key="aps")
        for f in self.of("aps_finding", "noncompliance") + self.of("aps_finding", "last_visit"):
            if f["fact_id"] not in self.cited:
                self.add([f], rid("APS-4" if f["key"] == "noncompliance" else "APS-3"), f"APS note: {f['value']} - no ratable condition attached.", key="aps")
        for f in self.of("aps_finding", prefix="series:"):
            if f["fact_id"] not in self.cited:
                vals = ", ".join(str(x["value"]) for x in f["value"])
                self.add([f], rid("GEN-6"), f"APS serial {f['key'][7:]} values: {vals}.", key="aps")
        for f in self.of("ekg"):
            if f["relevant"]:
                self.add([f], rid("CV", "CMB-3"), f"EKG: {f['value']} - consistent with the cardiac history reviewed." if self.rated_keys.keys() & (CARDIAC_KEYS | {"arrhythmia_other", "hypertension"})
                         else f"EKG: {f['value']} - cardiology review advised; not rated alone.", key="ekg")
        for f in self.facts:
            if f["relevant"] and f["fact_id"] not in self.cited and f["kind"] == "rx_fill":
                self.add([f], rid("RX-2.3", "RX-2"), f"Rx {f['key']} x{f['value']['n_fills']} ({f['value']['prescriber_specialty']}): short/acute course - no impact.",
                         key="rx")
        # misrepresentation pattern (GEN-2.3)
        cats = sorted(set(self.misrep))
        if len(cats) >= 2:
            self.add([], rid("GEN-2.3", "CLS-8.7"), f"Material misrepresentation in {len(cats)} categories ({', '.join(cats)}) - Decline, CUO notification.",
                     decline=True, at=max(self.t.values()) + timedelta(minutes=1), stage="final", key="misrep")
        elif cats:
            self.add([], rid("GEN-2.2"), f"Material misrepresentation ({cats[0]}): rated on the true facts; MISREP note for compliance.",
                     at=max(self.t.values()) + timedelta(minutes=1), stage="final", key="misrep")

    # ------------------------------------------------------------------ requirements
    def requirements(self):
        meta = self.content["meta"]
        third = [t for d, t in self.t.items() if STAGE[self.dtype[d]] in ("application", "third_party")]
        at = max(third) + timedelta(minutes=2)
        codes = {"PM": "paramed", "B": "lab_blood", "U": "lab_urine", "S": "lab_saliva", "EKG": "ekg", "NTPROBNP": "lab_blood",
                 "ALCQ": "other", "AVOQ": "other", "FORQ": "other", "FINQ": "other"}
        grp = defaultdict(list)
        for c, why in meta["requirements"].items():
            grp[why].append(c)
        for why, cs in grp.items():
            r = why.split()[0]
            r = r if r in RULE_IDS else rid(r.split("-")[0] + "-1" if "-" in r else "REQ")
            ln = Line(stage="requirements", at=at, facts=[], rule=r, finding=f"Order {', '.join(cs)}: {why}.", order=codes.get(cs[0], "other"))
            self.lines.append(ln)
        provs = {c["provider"]["provider_id"]: c["provider"] for did, c in self.content["docs"].items() if self.dtype.get(did) == "aps"}
        for pid, why in meta["aps"]:
            p = provs.get(pid, {"name": pid, "specialty": "?"})
            r = why.split()[0]
            self.lines.append(Line(stage="requirements", at=at, facts=[], rule=r if r in RULE_IDS else rid("REQ-2.1"),
                                   finding=f"Order APS from {p['name']} ({p['specialty']}): {why}.", order="aps"))

    def irrelevant(self):
        by_doc = defaultdict(list)
        for f in self.facts:
            if f["fact_id"] not in self.cited:
                by_doc[f["doc_id"]].append(f)
        for did, fs in by_doc.items():
            dt = self.dtype[did]
            rel = [f for f in fs if f["relevant"]]
            kinds = {f["kind"] for f in fs}
            what = {"lab_blood": "remaining blood values within UW normal limits", "lab_urine": "remaining urine values within limits",
                    "lab_saliva": "saliva panel otherwise negative", "paramed": "pulse/other exam items unremarkable",
                    "rx": "acute/low-impact fills", "mib": "remaining codes informational",
                    "app_part1": "remaining Part 1 answers reviewed", "app_part2": "remaining Part 2 answers reviewed",
                    "aps": "routine visit content (normal BP readings, exercise notes, legacy labs) reviewed",
                    "ekg": "EKG normal", "mvr": "MVR clear", "other": "questionnaire items reviewed"}.get(dt, "reviewed")
            r = {"lab_blood": "LAB-2", "lab_urine": "LAB-2", "lab_saliva": "LAB-2", "paramed": "GEN-5", "rx": "RX-2.1", "mib": "MIB-3",
                 "app_part1": "GEN-2", "app_part2": "GEN-2", "aps": "APS-1", "ekg": "CV", "mvr": "MVR-1", "other": "GEN-1"}.get(dt, "GEN-1")
            self.add(fs, rid(r), f"{what[0].upper() + what[1:]}: no impact" + (f" ({len(rel)} item(s) flagged relevant reviewed in context)" if rel else "") + ".")

    # ------------------------------------------------------------------ decision (CLS-4 steps 3-10)
    def decide(self) -> Decision:
        L = self.lines
        end = max(self.t.values()) + timedelta(minutes=5)
        ladder = "tobacco" if any(ln.ladder == "tobacco" for ln in L) else "non_tobacco"
        prelim = self.preliminary()
        dec_lines = [ln for ln in L if ln.decline]
        pp_lines = [ln for ln in L if ln.postpone]
        face = self.app("face")
        if dec_lines:
            reason = dec_lines[0].finding
            self.add([], rid("CLS-8.2" if dec_lines[0].key not in ("misrep", "fin", "fn") else dec_lines[0].rule), f"Knockout: {reason}",
                     at=end, stage="final")
            return Decision(ladder=ladder, risk_class="Decline", decline_reason=reason, preliminary_class=prelim)
        if pp_lines:
            m = max(ln.postpone for ln in pp_lines)
            reason = "; ".join(ln.finding for ln in pp_lines)
            self.add([], rid("CLS-7"), f"Postpone trigger(s) present - reconsider in {m} months: {reason}", at=end, stage="final")
            return Decision(ladder=ladder, risk_class="Postpone", postpone_months=m, decline_reason=None, preliminary_class=prelim)
        # CMB-2 interaction surcharges
        keys = set(self.rated_keys)
        bd = getattr(self, "build_debits", 0)
        if bd >= 50 and keys & {"diabetes_t2", "diabetes_t1", "hypertension", "sleep_apnea", "cad"}:
            self.add([], rid("BLD-1.6", "CMB-2"), f"Build +{bd} with {', '.join(sorted(keys & {'diabetes_t2', 'diabetes_t1', 'hypertension', 'sleep_apnea', 'cad'}))}: +25 interaction.",
                     debits=25, at=end, stage="final", key="cmb")
        if keys & {"diabetes_t2", "diabetes_t1"} and "cad" in keys:
            self.add([], rid("CMB-2"), "Diabetes with CAD: +50 interaction.", debits=50, at=end, stage="final", key="cmb")
        if "depression_anxiety" in keys and any(ln.key == "alc" and ln.debits > 0 for ln in L):
            self.add([], rid("CMB-2"), "Depression with alcohol rating: +25 interaction.", debits=25, at=end, stage="final", key="cmb")
        if "sleep_apnea" in keys and getattr(self, "bmi", 0) > 40:
            self.add([], rid("CMB-2"), "Sleep apnea with BMI > 40: +25 interaction.", debits=25, at=end, stage="final", key="cmb")
        gross = sum(ln.debits for ln in self.lines)
        # credits (CLS-6)
        net = gross
        if net > 0:
            net -= self.credits(gross, end)
        net = sum(ln.debits - ln.credits for ln in self.lines)
        fes = [ln.fe for ln in self.lines if ln.fe]
        fe_eq = sum(int(f.per_thousand / 2.5 * 25) for f in fes)
        if gross + fe_eq > 500:
            self.add([], rid("CMB-6"), f"Debits {gross} plus FE equivalents {fe_eq} > +500 - Decline (MD).", decline=True, at=end, stage="final")
            return Decision(ladder=ladder, risk_class="Decline", decline_reason="CMB-6 total > +500", preliminary_class=prelim, net_debits=net)
        # AVI-1.1
        if any(ln.key == "avo" and "pilot" in ln.finding.lower() for ln in self.lines) and max([ln.debits for ln in self.lines if ln.key in IMP] + [0]) >= 75:
            self.exclusions.append("aviation exclusion (AVI-1.1)")
            self.add([], rid("AVI-1.1"), "Pilot with a medical rating >= +75: aviation exclusion endorsement required.", at=end, stage="final")
        caps = [ln.cap for ln in self.lines if ln.cap]
        cls_, table = None, 0
        if net > 25:
            kind, table = table_from_net(net, self.age)
            if kind == "Decline":
                why = f"Net debits +{net}" + (" exceed Table 8 at age 71+ (CLS-3.4)" if net <= 425 else " > +425")
                self.add([], rid("CLS-8.1", "CLS-3.4"), why + " - Decline.", decline=True, at=end, stage="final")
                return Decision(ladder=ladder, risk_class="Decline", decline_reason=why, net_debits=net, preliminary_class=prelim)
            cls_ = "Table Tobacco" if ladder == "tobacco" else "Table"
            self.add([], rid("CLS-3.3"), f"Net debits +{net} -> {cls_} {table} (+{25 * table}%).", at=end, stage="final")
        elif net > 0 or gross > 0:
            cls_ = "Standard Tobacco" if ladder == "tobacco" else "Standard"
            self.add([], rid("CLS-3.3", "CLS-3.2"), f"Net debits +{net}" + (f" (gross +{gross}, credits applied)" if gross != net else "") +
                     f" -> {cls_} (credits cannot improve beyond Standard).", at=end, stage="final")
        else:
            cls_ = self.matrix(ladder, caps, end)
        dec = Decision(ladder=ladder, risk_class=cls_, table=table, flat_extras=fes, preliminary_class=prelim, net_debits=net,
                       exclusions=self.exclusions)
        if fes:
            self.add([], rid("CMB-5", "CLS-4"), "Flat extras: " + "; ".join(f"FE ${f.per_thousand:g}/1000 " + (f"x {f.years} yrs" if f.years else "perm") +
                     f" ({f.reason})" for f in fes) + ".", at=end + timedelta(minutes=1), stage="final")
        dec.riders = self.riders(dec, end + timedelta(minutes=2))
        if self.approved_face and self.approved_face < face:
            dec.approved_face_amount = self.approved_face
            self.add([], rid("FIN-2.2", "CLS-4"), f"Amount: approve ${self.approved_face:,} (applied ${face:,}).", at=end + timedelta(minutes=3), stage="final")
        return dec

    def credits(self, gross, at):
        if gross >= CLS["credits"]["excluded_if_gross_debits_ge"]:
            self.add([], rid("CLS-6"), f"Gross debits +{gross} >= +150: credits not available.", at=at, stage="final")
            return 0
        ex = [ln for ln in self.lines if (ln.debits > 0 or ln.key in self.rated_keys) and
              (ln.chapter in NO_CREDIT_CHAPTERS or IMP.get(ln.key or "", {}).get("chapter") in NO_CREDIT_CHAPTERS)]
        if ex:
            self.add([], rid("CLS-6"), f"Credits not available ({', '.join(sorted({ln.chapter or ln.key for ln in ex}))} rating).", at=at, stage="final")
            return 0
        cr = []
        if self.lip and not getattr(self, "statin", False) and self.lip[1] <= 3.5:
            cr.append(("CLS-6.1", 15, f"TC/HDL {self.lip[1]} <= 3.5 untreated", [self.one("lab_value", "tc_hdl_ratio") or self.one("lab_value", "tc")]))
        s, d = getattr(self, "bp", (None, None))
        if s is not None and "hypertension" not in self.rated_keys and s <= 125 and d <= 80:
            cr.append(("CLS-6.2", 10, f"BP {s}/{d} <= 125/80 untreated", self.bp_fx))
        ex_f = self.of("aps_finding", "exercise")
        pulse = self.one("paramed", "pulse")
        if ex_f and pulse:
            if pulse["value"] <= 65:
                cr.append(("CLS-6.4", 10, f"documented exercise ({ex_f[0]['value']}) and pulse {pulse['value']}", [ex_f[0], pulse]))
            elif pulse["value"] <= 70:
                self.gry("GRY-12", "Exercise documented but resting pulse 66-70", "withhold CLS-6.4 credit", ["apply -10 credit"],
                         "CLS-6.4 requires pulse <= 65.", ("CLS-6.4",))
        bnp = self.one("lab_value", "nt_probnp")
        if bnp and self.age >= 50 and bnp["value"] < 50:
            cr.append(("CLS-6.5", 10, f"NT-proBNP {bnp['value']:g} < 50 at age {self.age}", [bnp]))
        tot = 0
        for r, amt, why, fx in cr:
            amt = min(amt, CLS["credits"]["max_total"] * -1 - tot)
            if amt <= 0:
                break
            tot += amt
            self.add([x for x in fx if x], rid(r), f"Credit -{amt}: {why}.", credits=amt, at=at, stage="final")
        return tot

    def matrix(self, ladder, caps, at):
        """CLS-5 preferred matrix (net <= 0) -> class, honoring caps (CMB-4)."""
        rows = {}
        rows["build"] = getattr(self, "build_col", "Standard") or "Standard"
        s, d = self.bp
        if s is None:
            rows["bp"] = "Elite"                                    # not measured (accelerated path, REQ-3)
        else:
            treated = "hypertension" in self.rated_keys
            k = "bp_under60" if self.age < 60 else "bp_60plus"
            rows["bp"] = next((c for c in PREF[:4] if s <= CLS["preferred_matrix"]["classes"][c][k]["sys"] and d <= CLS["preferred_matrix"]["classes"][c][k]["dia"]
                               and (CLS["preferred_matrix"]["classes"][c][k]["treated_ok"] or not treated)), "Standard")
        if self.lip:
            tc, r, _ = self.lip
            st = getattr(self, "statin", False)
            rows["lipids"] = next((c for c in PREF[:4] if tc <= CLS["preferred_matrix"]["classes"][c]["tc_max"] and r <= CLS["preferred_matrix"]["classes"][c]["ratio_max"]
                                   and (CLS["preferred_matrix"]["classes"][c]["lipids_treated_ok"] or not st)), "Standard")
        else:
            rows["lipids"] = "Elite"                                # no blood drawn (accelerated path, REQ-3)
        nfy = self.nicotine_free_years
        rows["nicotine"] = next((c for c in PREF[:4] if nfy >= CLS["preferred_matrix"]["classes"][c]["nicotine_free_years"]), "Standard")
        rows["family_history"] = getattr(self, "fh_level", "Elite")
        rows["mvr"] = self.mvr_level
        if getattr(self, "occ_class", "1A") and any(w in self.app("occupation") for w in ("police", "firefighter")):
            rows["occupation"] = "Preferred Plus"
        rows["age"] = next(c for c in PREF[:4] if CLS["preferred_matrix"]["classes"][c]["ages"][0] <= self.age <= CLS["preferred_matrix"]["classes"][c]["ages"][1])
        face = self.approved_face or self.app("face")
        rows["face"] = next(c for c in PREF[:4] if face >= CLS["preferred_matrix"]["classes"][c]["min_face"])
        if not any(self.dtype[x] in ("lab_blood", "lab_urine") for x in self.docs):
            rows["fluids"] = "Preferred Plus"                       # Elite requires fluids (REQ-3)
        if self.avo_fe:
            rows["avocation"] = "Preferred" if self.avo_fe <= 2.5 else "Standard Plus"
        mh = [k for k in self.rated_keys if k in MAJOR_HISTORY or (k == "cancer" and self.conds.get("cancer", {}).get("type") != "bcc_scc")]
        if mh:
            rows["personal_medical"] = "Preferred"
        zero = [k for k, ln in self.rated_keys.items() if ln.debits == 0 and not ln.decline and not ln.postpone and k != "hypertension"]
        chs = {IMP[k]["chapter"] for k in zero if k in IMP}
        if len(zero) >= 2 and len(chs) >= 2:
            caps = caps + ["Standard Plus"]
            self.gry("GRY-10", f"Two or more 0-debit impairments in unrelated systems ({', '.join(IMP[k]['label'] for k in zero)})", "Standard Plus (default)",
                     ["Preferred if both minor-impact"], "GRY-10 default.", ("CLS-5",))
        fails_pref = [k for k, v in rows.items() if PREF.index(v) > 2]
        level = max(rows.values(), key=PREF.index)
        note = ""
        if 1 <= len(fails_pref) <= 2 and all(PREF.index(rows[k]) <= 3 for k in fails_pref):
            level = max(level, "Standard Plus", key=PREF.index) if PREF.index(level) <= 3 else level
            note = f" (fails Preferred on {', '.join(fails_pref)}: Standard Plus rule CLS-5.2)"
        elif len(fails_pref) >= 3:
            level = "Standard"
            note = f" (fails Preferred on {len(fails_pref)} rows: Standard, CLS-5.2)"
        cap = worst(*caps)
        best = worst(level, cap)
        rtxt = ", ".join(f"{k} {v}" for k, v in rows.items())
        if ladder == "tobacco":
            pref_ok = all(PREF.index(v) <= 2 for k, v in rows.items() if k != "nicotine") and not self.cigarette_12mo and \
                (cap is None or PREF.index(cap) <= 2)
            cls_ = "Preferred Tobacco" if pref_ok else "Standard Tobacco"
            self.add([], rid("CLS-5.6"), f"Net 0 on tobacco ladder; rows: {rtxt}" + ("" if pref_ok else "; Preferred Tobacco not met") + f" -> {cls_}.",
                     at=at, stage="final")
            return cls_
        self.add([], rid("CLS-5", "CLS-5.2"), f"Net 0: preferred matrix rows {rtxt}{note} -> {level}" +
                 (f"; chapter cap {cap} (CMB-4)" if cap and PREF.index(cap) > PREF.index(level) else "") + f" => {best}.", at=at, stage="final")
        self.edge_grey(rows)
        return best

    def edge_grey(self, rows):
        bmi = getattr(self, "bmi", None)
        if bmi:
            for b in BUILD["upper_bands"][:5]:
                if 0 < bmi - b["max_bmi"] <= 0.02 * b["max_bmi"] * 0.25:
                    self.gry("GRY-1", f"BMI {bmi:.1f} just over the {b['label']} column", f"{rows['build']}", [b["best_class"]],
                             "Within 2% of the threshold; better class only with improving APS trend.", ("BLD-1",))
                    break

    def preliminary(self):
        """Class indicated from the application alone (Part 1/2 answers), before third-party evidence."""
        app_lines = [ln for ln in self.lines if ln.stage == "application"]
        if any(ln.decline for ln in app_lines):
            return "Decline"
        if any(ln.postpone for ln in app_lines):
            return "Postpone"
        disc = [f for f in self.of("app_answer") if ":" in f["key"] and f["relevant"]]
        tob = any(ln.ladder for ln in app_lines)
        if disc:
            return "Standard Tobacco" if tob else "Standard"
        caps = [ln.cap for ln in app_lines if ln.cap]
        c = worst("Preferred Plus", *caps) if caps else "Preferred Plus"
        return ("Preferred Tobacco" if tob else c)

    def riders(self, dec, at):
        req = self.app("riders") or []
        rf = self.one("app_answer", "riders")
        out = []
        prod = self.app("product")
        tbl = dec.table
        std_or_better = dec.risk_class in PREF + ["Preferred Tobacco", "Standard Tobacco"]
        for code in req:
            r = RID.get(code, {})
            lo, hi = r.get("ages", [18, 99])
            reason, ok = None, True
            if self.age < lo or self.age > hi:
                ok, reason = False, f"issue age {self.age} outside {lo}-{hi}"
            elif r.get("products") and prod not in r["products"]:
                ok, reason = False, f"not available on {prod}"
            elif "max_table" in r and tbl > r["max_table"]:
                ok, reason = False, f"Table {tbl} exceeds rider max Table {r['max_table']}"
            elif r.get("min_class") and not (std_or_better and (r["min_class"] != "Standard Plus" or dec.risk_class in PREF[:4])):
                ok, reason = False, f"base class {dec.label()} below rider minimum {r['min_class']}"
            elif code == "GIO" and dec.flat_extras:
                ok, reason = False, "flat extra on the base policy"
            elif code in ("WP", "WMD"):
                if any(f.reason.startswith("occupation") for f in dec.flat_extras):
                    ok, reason = False, "occupation flat extra"
                elif getattr(self, "bmi", 0) > 40:
                    ok, reason = False, "BMI > 40"
                elif any(k in self.rated_keys and self.rated_keys[k].debits > 0 for k in ("back_pain", "depression_anxiety", "bipolar", "schizophrenia", "ptsd")):
                    ok, reason = False, "back/spine or psychiatric rating"
                elif self.app("occupation") in ("retired", "homemaker", "unemployed", "student"):
                    ok, reason = False, "non-earning applicant"
            elif code == "ADB":
                if any(ln.key in ("mvr",) and (ln.debits or ln.cap) for ln in self.lines):
                    ok, reason = False, "MVR major/DUI rating"
                elif any(f.reason.startswith(("avocation", "private aviation")) for f in dec.flat_extras):
                    ok, reason = False, "avocation/aviation flat extra"
                elif any(ln.key in ("alc", "drg") and ln.debits for ln in self.lines) or "alcohol_use_disorder" in self.rated_keys:
                    ok, reason = False, "alcohol/drug rating"
                elif getattr(self, "occ_class", "1A") in ("4A", "5A"):
                    ok, reason = False, "occupation class 4A/5A"
            elif code == "CIA" and any(k in self.rated_keys for k in ("parkinsons", "multiple_sclerosis", "stroke", "tia", "cognitive_impairment", "epilepsy", "tbi")):
                ok, reason = False, "neurological rating"
            elif code == "KPE" and not getattr(self, "kpe_ok", False):
                ok, reason = False, "face exceeds 10x key-person compensation or FIN-Q missing (FIN-2.3)"
            st = "approved" if ok else "declined"
            ra = RiderAction(code=code, status=st, reason=reason or "eligible")
            out.append(ra)
            self.add([rf] if rf else [], rid("RID-2" if not ok else "RID-1", "RID"), f"Rider {code}: {st}" + (f" - {reason}." if reason else "."),
                     rider=ra, at=at, stage="final")
        return out


def run_case(cid: str) -> Golden:
    return Engine(cid).run()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    ids = a.ids.split(",") if a.ids else sorted(p.name for p in (ROOT / "data/source").glob("C*"))
    out = ROOT / "data/golden"
    out.mkdir(parents=True, exist_ok=True)
    for cid in ids:
        g = run_case(cid)
        (out / f"{cid}.json").write_text(g.model_dump_json(indent=1))
        if not a.quiet:
            print(cid, g.decision.label(), f"net {g.decision.net_debits}", f"steps {len(g.trace)}", f"grey {len(g.grey_areas)}")


if __name__ == "__main__":
    main()
