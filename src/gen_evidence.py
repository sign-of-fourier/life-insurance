"""Phase 4b: Truth -> evidence facts + structured document content (what the UW will see).

Outputs per case (data/source/<case>/):
  evidence.json  schemas.EvidenceBundle (facts + SourceDoc metadata: type, vendor, ordered/received, order reason)
  content.json   {doc_id: structured content} consumed by renderers (Phase 4c)
Ordering follows guidelines REQ-1 grid -> REQ-3 accel eligibility -> REQ-2 UW triggers (doc.order_reason cites rule).
Disclosure: honest | minimized | misremembered | omitted drive app answers; traces (Rx/MIB/APS/labs) for omitted
conditions are guaranteed unless details.untraceable.

Run: python src/gen_evidence.py [--ids ...] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rules import load  # noqa: E402
from schemas import EvidenceBundle, EvidenceFact, SourceDoc, Truth  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
IMP = load("impairments")
REQ = load("requirements")
RX = load("rx_map")["drugs"]
MIB = load("mib_codebook")
MVRC = load("mvr_codes")["codes"]
VEND = load("vendors")
LABS = load("labs")["analytes"]

# app Part 2 question categories (generic ids; app forms renumber them)
Q_BY_CHAPTER = {"CV": "heart", "HTN": "bp", "DM": "diabetes", "CA": "cancer", "MH": "mental", "RSP": "respiratory",
                "GI": "digestive", "REN": "kidney", "NEU": "neuro", "END": "endocrine", "MSK": "musculoskeletal",
                "HEM": "blood_immune", "IMM": "blood_immune", "GER": "neuro", "OBS": "other", "MISC": "other",
                "ALC": "alcohol_treatment", "DRG": "drugs"}
PART2_QS = ["tobacco", "alcohol", "alcohol_treatment", "drugs", "heart", "bp", "diabetes", "cancer", "mental", "respiratory",
            "digestive", "kidney", "neuro", "endocrine", "musculoskeletal", "blood_immune", "hiv", "other", "pending_tests",
            "hospitalized_5y", "current_meds", "physician", "family_history", "weight_change", "height_weight"]
FORM_NUM = {
    "APP-2019": {q: f"Q{i + 1}" for i, q in enumerate(PART2_QS)},
    "APP-2024": {q: (f"7{chr(97 + i)}" if i < 26 else f"8{chr(97 + i - 26)}") for i, q in enumerate(PART2_QS)},
}
ACCEL_OK_BENIGN = {"seasonal_allergy", "acne", "gerd", "contraception", "acute_injury", "dental"}


def dt(d: date, hh=9, mm=0) -> datetime:
    return datetime(d.year, d.month, d.day, hh, mm)


class EvidenceGen:
    def __init__(self, t: Truth):
        self.t = t
        self.row = t.design
        self.x = t.design.get("_extra", {})
        self.r = random.Random(t.seed ^ 0x5EED)
        self.facts: list[EvidenceFact] = []
        self.docs: list[SourceDoc] = []
        self.content: dict[str, dict] = {}
        self.t0 = dt(t.app_date, 9, self.r.randint(0, 50))
        self.trace: Counter = Counter()   # condition index -> # traces in evidence

    # ------------------------------------------------------------------ plumbing
    def doc(self, doc_type, vendor, received, ordered=None, reason=None, pages=1, content=None) -> str:
        did = f"{self.t.case_id}-D{len(self.docs) + 1:02d}"
        self.docs.append(SourceDoc(doc_id=did, case_id=self.t.case_id, doc_type=doc_type, vendor_id=vendor,
                                   ordered_at=ordered, received_at=received, order_reason=reason, pages=pages,
                                   text_path=f"data/source/{self.t.case_id}/{did}.txt"))
        self.content[did] = content or {}
        return did

    def fact(self, did, kind, key, value, unit=None, as_of=None, relevant=True, truth_ref=None, note=None) -> str:
        fid = f"{self.t.case_id}-F{len(self.facts) + 1:03d}"
        self.facts.append(EvidenceFact(fact_id=fid, doc_id=did, kind=kind, key=key, value=value, unit=unit, as_of=as_of,
                                       relevant=relevant, truth_ref=truth_ref, note=note))
        next(d for d in self.docs if d.doc_id == did).fact_ids.append(fid)
        return fid

    def cond_refs(self):
        return [(i, c) for i, c in enumerate(self.t.conditions)]

    # ------------------------------------------------------------------ application
    def app(self):
        t, r = self.t, self.r
        form = self.row["vendors"]["app"]
        p = t.person
        p1 = {"form": form, "name": f"{p.first_name} {p.last_name}", "sex": p.sex, "dob": p.dob.isoformat(), "state": p.address_state,
              "country": p.country_of_residence, "citizenship": p.citizenship, "years_in_us": p.years_in_us, "visa": p.visa_type,
              "occupation": p.occupation, "income": p.annual_income, "net_worth": p.net_worth, "marital": p.marital_status,
              "dependents": p.dependents, "face": t.coverage.face_amount, "product": t.coverage.product,
              "riders": t.coverage.riders_requested, "existing": t.coverage.existing_coverage, "replacement": t.coverage.replacement,
              "beneficiary": t.coverage.beneficiary_relation, "signed": t.app_date.isoformat(),
              "signed_in_us": not (self.row["items"] and any(i["variant"] == "citizen_abroad_C" for i in self.row["items"])) or r.random() < 0.8}
        d1 = self.doc("app_part1", form, self.t0, content=p1)
        for k in ("occupation", "income", "net_worth", "face", "existing", "citizenship", "visa", "years_in_us", "riders", "product"):
            self.fact(d1, "app_answer", k, p1[k] if k != "years_in_us" or p1[k] else None)
        if p.country_of_residence != "US":
            self.fact(d1, "app_answer", "residence", p.country_of_residence)
        # avocation / aviation / travel / MVR / criminal / prior apps (Part 1 non-medical questions)
        for i, a in enumerate(t.avocations):
            hazardous = a.activity not in ("hiking", "recreational boating", "hunting", "marathon running", "martial arts", "skiing")
            if a.disclosure == "omitted":
                self.fact(d1, "app_answer", "hazardous_avocation", "No", truth_ref=f"avocations[{i}]", note="omitted")
            else:
                self.fact(d1, "app_answer", "avocation", {"activity": a.activity, **a.details}, truth_ref=f"avocations[{i}]",
                          relevant=hazardous)
        for i, tr in enumerate(t.travel):
            self.fact(d1, "app_answer", "foreign_travel", {"country": tr.country, "weeks_per_year": tr.weeks_per_year, "purpose": tr.purpose},
                      truth_ref=f"travel[{i}]", relevant=tr.purpose != "vacation")
        dui10 = [e for e in t.mvr if MVRC[e.code]["class"] == "dui" and (t.app_date - e.date).days < 3653]
        if dui10:
            if any(e.disclosure == "omitted" for e in dui10):
                self.fact(d1, "app_answer", "dui_10y", "No", note="omitted")
            else:
                self.fact(d1, "app_answer", "dui_10y", f"Yes - {len(dui10)}; last {max(e.date for e in dui10).strftime('%m/%Y')}")
        for k in ("nm_criminal",):
            if k in self.x:
                self.fact(d1, "app_answer", "criminal", {"pending_felony": "pending felony charge", "released_lt2": "released from incarceration "
                          f"{r.randint(3, 20)} months ago"}[self.x[k]])
        for pa in t.prior_apps:
            self.fact(d1, "app_answer", "prior_application", f"{pa.year} {pa.company}: {pa.outcome}",
                      relevant=pa.outcome in ("declined", "postponed", "issued Table 2"))
        if "nm_misrep" in self.x:
            self.misrep = True
        # ---- Part 2
        nums = FORM_NUM[form]
        answers = {q: {"answer": "No"} for q in PART2_QS}
        d2 = self.doc("app_part2", form, self.t0 + timedelta(minutes=2), content={"form": form, "numbering": nums, "answers": answers})
        # tobacco
        tob_ans, tob_note = "No", None
        if t.tobacco:
            u = t.tobacco[0]
            last = u.quit or t.app_date
            if u.disclosure == "omitted":
                tob_ans, tob_note = "No", "omitted"
            elif u.disclosure == "minimized":
                fake_quit = t.app_date - timedelta(days=r.randint(400, 1500))
                tob_ans, tob_note = f"Former {u.product}; quit {fake_quit.strftime('%m/%Y')}", "minimized: quit date understated"
            else:
                tob_ans = (f"Current {u.product}, {u.frequency}" if u.status == "current" else
                           f"Former {u.product}, quit {last.strftime('%m/%Y')}")
            if form == "APP-2019" and u.status == "former" and (t.app_date - last).days > 5 * 365 and u.disclosure != "omitted":
                tob_ans = "No"   # 5-yr question window: older quits not asked
        answers["tobacco"] = {"answer": tob_ans}
        self.fact(d2, "app_answer", "tobacco", tob_ans, truth_ref="tobacco[0]" if t.tobacco else None, note=tob_note)
        # alcohol
        dpw = t.alcohol_drinks_per_week
        alc_disc = next((i["disclosure"] for i in self.row["items"] if i["key"] == "nm_alcohol"), "honest")
        stated = dpw if alc_disc == "honest" else max(0, int(dpw * r.uniform(0.3, 0.6)))
        answers["alcohol"] = {"answer": f"{stated} drinks/week"}
        self.fact(d2, "app_answer", "alcohol_dpw", stated, unit="drinks/wk", relevant=dpw > 14 or stated != dpw,
                  note=None if stated == dpw else "understated")
        for du in t.drug_use:
            if du.get("disclosure", "honest") != "omitted":
                answers["drugs"] = {"answer": "Yes", "details": f"marijuana {du['per_week']}x/week ({du['form']})"}
                self.fact(d2, "app_answer", "marijuana", du["per_week"], unit="uses/wk")
        # conditions
        for i, c in self.cond_refs():
            q = "hiv" if c.condition_key == "hiv" else Q_BY_CHAPTER.get(IMP[c.condition_key]["chapter"], "other")
            if c.irrelevant:
                q = {"gerd": "digestive", "seasonal_allergy": "respiratory", "acne": "other"}.get(c.details.get("member"), "other")
            label = c.label
            if c.disclosure == "omitted":
                continue
            detail = {"condition": label, "diagnosed": c.onset.strftime("%m/%Y"), "treatment": ", ".join(m.drug for m in c.meds) or "none",
                      "physician": next((pr.name for pr in self.t.providers if pr.provider_id in c.treating_provider_ids), None)}
            note = None
            if c.disclosure == "minimized":
                detail["condition"] = self.minimize_label(c)
                detail["treatment"] = (c.meds[0].drug if c.meds else "none")
                note = "minimized"
            elif c.disclosure == "misremembered":
                off = r.choice([-1, 1]) * r.randint(2, 4)
                detail["diagnosed"] = (c.onset + timedelta(days=365 * off)).strftime("%m/%Y")
                note = "misremembered date"
            prev = answers[q]
            pd = prev.get("details") or []
            answers[q] = {"answer": "Yes", "details": (pd if isinstance(pd, list) else [pd]) + [detail]}
            self.fact(d2, "app_answer", f"{q}:{c.condition_key}", detail, truth_ref=f"conditions[{i}]", note=note, relevant=not c.irrelevant)
            self.trace[i] += 1
        # pending tests / surgery / weight loss
        if "nm_workup" in self.x or "nm_surgery" in self.x:
            what = "biopsy scheduled - breast" if "nm_workup" in self.x and t.person.sex == "F" else \
                   "referred for CT of lung nodule" if "nm_workup" in self.x else f"{r.choice(['knee replacement', 'hernia repair (open)', 'spinal fusion', 'hysterectomy' if t.person.sex == 'F' else 'shoulder repair'])} scheduled"
            answers["pending_tests"] = {"answer": "Yes", "details": what}
            self.fact(d2, "app_answer", "pending_tests", what)
        if "nm_weightloss" in self.x:
            answers["weight_change"] = {"answer": "Yes", "details": f"lost {r.randint(22, 40)} lbs, not trying"}
            self.fact(d2, "app_answer", "weight_change", answers["weight_change"]["details"])
        # stated build (people shave pounds)
        sw = t.weight_lb - (r.randint(3, 15) if r.random() < 0.5 else 0)
        sh = t.height_in + (1 if r.random() < 0.15 else 0)
        answers["height_weight"] = {"answer": f"{int(sh // 12)}'{int(sh % 12)}\" {sw} lbs"}
        self.fact(d2, "app_answer", "stated_build", answers["height_weight"]["answer"], relevant=False)
        # family history
        fh = [f"{f.relation}: {f.condition}" + (f", died {f.age_at_death}" if f.age_at_death else f", dx {f.age_at_onset}" if f.age_at_onset else "")
              for f in t.family_history]
        answers["family_history"] = {"answer": "; ".join(fh) or "none known"}
        for f in t.family_history:
            counted = f.condition in ("MI", "CAD", "stroke", "sudden cardiac death", "breast cancer", "colon cancer")
            self.fact(d2, "app_answer", "family_history", {"relation": f.relation, "condition": f.condition, "age_at_onset": f.age_at_onset,
                      "age_at_death": f.age_at_death}, relevant=counted)
        pcp = t.providers[0]
        answers["physician"] = {"answer": f"{pcp.name}, {pcp.practice}; last visit {(t.app_date - timedelta(days=r.randint(20, 400))).strftime('%m/%Y')}"}
        answers["current_meds"] = {"answer": ", ".join(sorted({m.drug for c in t.conditions if c.disclosure != "omitted" for m in c.meds if not m.stop})) or "none"}
        return d1, d2

    def minimize_label(self, c):
        k = c.condition_key
        return {"cad": "chest pain, tests ok", "diabetes_t2": "borderline sugar", "diabetes_t1": "diabetes", "depression_anxiety": "stress",
                "bipolar": "depression", "copd": "bronchitis", "afib": "palpitations", "hypertension": "slightly high BP",
                "cancer": "skin spot removed" if c.details.get("type", "").startswith("melanoma") else "lump removed, benign?",
                "alcohol_use_disorder": "drank too much, stopped", "sleep_apnea": "snoring", "stroke": "dizzy spell",
                "epilepsy": "fainting episode", "hepatitis_c": "liver test abnormal once", "multiple_sclerosis": "numbness, resolved"}.get(k, c.label.split("/")[0].lower() + " (mild)")

    # ------------------------------------------------------------------ third party (intake)
    def rx(self):
        t, r = self.t, self.r
        v = self.row["vendors"]["rx"]
        lookback = VEND["rx_vendors"][v]["lookback_years"]
        start = t.app_date - timedelta(days=365 * lookback)
        fills = []
        prov = {p.provider_id: p for p in t.providers}
        for i, c in self.cond_refs():
            if c.details.get("untraceable"):
                continue
            for m in c.meds:
                s, e = max(m.start, start), min(m.stop or t.app_date, t.app_date - timedelta(days=3))
                if e < start or s > e:
                    continue
                days = r.choice([30, 30, 90]) if not c.irrelevant else r.choice([10, 30])
                n = max(1, min(40, (e - s).days // days + 1))
                if c.irrelevant and m.stop:
                    n = min(n, r.randint(1, 2))
                pid = c.treating_provider_ids[0] if c.treating_provider_ids else t.providers[0].provider_id
                pr = prov.get(pid, t.providers[0])
                dates = sorted({s + timedelta(days=int(k * (e - s).days / max(1, n - 1))) if n > 1 else s for k in range(n)})
                fills.append({"drug": m.drug, "brand": RX[m.drug][0], "strength": m.dose, "fills": [d.isoformat() for d in dates], "days_supply": days,
                              "prescriber": pr.name, "specialty": pr.specialty, "cond_index": i})
        # cessation Rx evidence (TOB-5)
        q = self.x.get("cessation_rx_quit")
        if q:
            qd = date.fromisoformat(q)
            fills.append({"drug": "varenicline", "brand": "Chantix", "strength": "1 mg", "fills": [(qd - timedelta(days=30 * k)).isoformat() for k in range(3)],
                          "days_supply": 30, "prescriber": t.providers[0].name, "specialty": t.providers[0].specialty, "cond_index": None})
        # acute noise
        for _ in range(r.choice([0, 1, 2, 3])):
            d = r.choice(["amoxicillin", "azithromycin", "ibuprofen", "prednisone", "ondansetron", "cyclobenzaprine", "hydrocodone-acetaminophen"])
            fd = t.app_date - timedelta(days=r.randint(30, 365 * lookback - 10))
            fills.append({"drug": d, "brand": RX[d][0], "strength": r.choice(RX[d][1]), "fills": [fd.isoformat()], "days_supply": r.choice([5, 7, 10]),
                          "prescriber": f"Dr. {r.choice(['Patel', 'Nguyen', 'Garcia', 'Kim', 'Smith'])} (Urgent Care)", "specialty": "urgent care", "cond_index": None})
        did = self.doc("rx", v, self.t0 + timedelta(minutes=r.randint(5, 40)), ordered=self.t0 + timedelta(minutes=1), reason="REQ-1 always",
                       content={"vendor": v, "fills": fills, "no_history": not fills})
        for f in fills:
            ci = f["cond_index"]
            c = self.t.conditions[ci] if ci is not None else None
            rel = (c is not None and not c.irrelevant) or f["drug"] == "varenicline" or (f["drug"] == "prednisone" and len(f["fills"]) > 2)
            note = None
            if c is not None and not c.irrelevant and c.disclosure == "omitted":
                note = "not disclosed on app"
            self.fact(did, "rx_fill", f["drug"], {"strength": f["strength"], "n_fills": len(f["fills"]), "first": f["fills"][0], "last": f["fills"][-1],
                      "prescriber_specialty": f["specialty"]}, as_of=date.fromisoformat(f["fills"][-1]), relevant=rel,
                      truth_ref=f"conditions[{ci}]" if ci is not None else None, note=note)
            if ci is not None:
                self.trace[ci] += 1
        return did

    def mib_code_for(self, c):
        k = c.condition_key
        opts = [scc for scc, v in MIB["conditions"].items() if v.get("maps") == k and not v.get("retired")]
        if k == "cancer":
            t = c.details.get("type", "")
            pref = {"bcc": "801", "melanoma": "802", "breast_dcis": "804", "breast": "803", "prostate": "805", "colon": "806", "thyroid": "807",
                    "hodgkin": "808", "nhl": "808", "cll": "809", "acute": "809", "lung": "810", "testicular": "811"}
            opts = [next((v for p, v in pref.items() if t.startswith(p)), "812")]
        if k == "benign_no_rating":
            opts = [scc for scc, v in MIB["conditions"].items() if v.get("maps") == "benign_no_rating"]
        if not opts:
            return None
        scc = self.r.choice(opts)
        deg = {"mild": "2", "moderate": "3", "severe": "4"}[c.severity]
        if self.r.random() < 0.15:
            deg = self.r.choice(["7", "9", "8"])
        src = self.r.choice("1111235677")
        yrs = (self.t.app_date - c.onset).days / 365.25
        qual = "5" if yrs < 1 else "6" if yrs < 5 else "7"
        if c.meds and self.r.random() < 0.3:
            qual = "2"
        return scc + deg + src + qual

    def mib(self):
        t, r = self.t, self.r
        v = self.row["vendors"]["mib"]
        recent_imm = (t.person.years_in_us or 99) < 5 and t.person.citizenship != "US"
        codes = []
        for i, c in self.cond_refs():
            if c.details.get("untraceable"):
                continue
            need_trace = c.disclosure == "omitted" and not c.irrelevant and self.trace[i] == 0 and not c.meds
            if need_trace or (c.in_mib and not (recent_imm and r.random() < 0.8)):
                code = self.mib_code_for(c)
                if code:
                    rep = c.onset + timedelta(days=r.randint(30, max(31, (t.app_date - c.onset).days - 30)))
                    codes.append({"code": code, "reported": min(rep, t.app_date - timedelta(days=40)).isoformat(), "cond_index": i})
        for pa in t.prior_apps:
            codes.append({"code": f"010{r.choice('09')}{r.choice('07')}{r.choice('09' if pa.outcome in ('declined', 'postponed') else '00')}",
                          "reported": date(pa.year, r.randint(1, 12), 15).isoformat(), "cond_index": None, "admin": True})
        for j, a in enumerate(t.avocations):
            scc = {"scuba": "021", "skydiving": "022", "motor_racing": "023", "mountain_climbing": "024", "private_aviation": "025"}.get(a.activity)
            if scc and (a.disclosure == "omitted" or r.random() < 0.3):
                codes.append({"code": f"{scc}0{r.choice('0478')}0", "reported": (t.app_date - timedelta(days=r.randint(200, 1500))).isoformat(),
                              "cond_index": None, "avocation": j})
        if any(e.disclosure == "omitted" and MVRC[e.code]["class"] == "dui" for e in t.mvr):
            codes.append({"code": "031040", "reported": (t.app_date - timedelta(days=r.randint(100, 900))).isoformat(), "cond_index": None})
        if t.tobacco and t.tobacco[0].disclosure == "omitted" and r.random() < 0.5:
            codes.append({"code": "0500" + r.choice("07") + "6", "reported": (t.app_date - timedelta(days=r.randint(300, 1400))).isoformat(), "cond_index": None})
        # noise: stale (>7y) and retired codes
        if r.random() < 0.25:
            scc = r.choice(["090", "190", "390", "490", "690", "890", "990", "180"])
            codes.append({"code": f"{scc}{r.randint(0, 9)}{r.randint(0, 9)}{r.randint(0, 9)}", "reported": date(t.app_date.year - r.randint(8, 16), r.randint(1, 12), 1).isoformat(), "cond_index": None})
        if r.random() < 0.15:
            scc = r.choice(["114", "225", "316", "525", "816", "170"])   # ambiguous / uncorroborated (GRY-8 bait)
            codes.append({"code": f"{scc}7{r.choice('17')}{r.choice('56')}", "reported": (t.app_date - timedelta(days=r.randint(200, 2000))).isoformat(),
                          "cond_index": None, "uncorroborated": True})
        did = self.doc("mib", v, self.t0 + timedelta(minutes=r.randint(3, 30)), ordered=self.t0 + timedelta(minutes=1), reason="REQ-1 always",
                       content={"vendor": v, "codes": codes, "no_hit": not codes})
        for cd in codes:
            ci = cd.get("cond_index")
            c = t.conditions[ci] if ci is not None else None
            age_y = (t.app_date - date.fromisoformat(cd["reported"])).days / 365.25
            rel = (c is not None and not c.irrelevant and age_y <= 7) or cd.get("uncorroborated") or ("avocation" in cd) or cd["code"].startswith(("031", "050"))
            if cd["code"][:3] in ("090", "190", "390", "490", "690", "890", "990", "180") or age_y > 7:
                rel = False
            self.fact(did, "mib_code", cd["code"], cd["reported"], as_of=date.fromisoformat(cd["reported"]), relevant=bool(rel),
                      truth_ref=f"conditions[{ci}]" if ci is not None else None,
                      note="uncorroborated" if cd.get("uncorroborated") else None)
            if ci is not None:
                self.trace[ci] += 1
        return did

    def mvr(self):
        t, r = self.t, self.r
        if t.person.age > 75 and r.random() < 0.6:
            return None
        v = self.row["vendors"]["mvr"]
        evs = [e for e in t.mvr if (t.app_date - e.date).days < 7 * 365]
        did = self.doc("mvr", v, self.t0 + timedelta(minutes=r.randint(10, 90)), ordered=self.t0 + timedelta(minutes=1), reason="REQ-1 always",
                       content={"vendor": v, "license_state": t.person.address_state, "status": "SUSPENDED" if any(e.code == "L02" for e in evs) else "VALID",
                                "events": [{"date": e.date.isoformat(), "code": e.code, "desc": MVRC[e.code]["desc"]} for e in evs],
                                "no_record": not evs, "foreign_license": t.person.country_of_residence != "US"})
        for e in evs:
            cls = MVRC[e.code]["class"]
            yrs = (t.app_date - e.date).days / 365.25
            rel = cls in ("dui", "major") or (cls == "minor" and yrs <= 3) or (cls == "accident" and MVRC[e.code].get("counts_as") not in (None, "none") and yrs <= 3)
            self.fact(did, "mvr_violation", e.code, MVRC[e.code]["desc"], as_of=e.date, relevant=rel,
                      note="not disclosed" if e.disclosure == "omitted" and cls == "dui" else None)
        return did

    # ------------------------------------------------------------------ requirements
    def requirements(self):
        """REQ-1 grid + REQ-3 accel check + REQ-2 triggers -> list of (code, reason, provider_id?)."""
        t = self.t
        age, face = t.person.age, t.coverage.face_amount
        ai = next(i for i, (lo, hi) in enumerate(REQ["age_bands"]) if lo <= age <= hi)
        fi = next(i for i, (lo, hi) in enumerate(REQ["amount_bands"]) if face >= lo and (hi is None or face <= hi))
        grid = list(REQ["grid"][ai][fi])
        reasons = {g: "REQ-1 grid" for g in grid}
        ratable = [(i, c) for i, c in self.cond_refs() if not c.irrelevant]
        if grid == ["ACCEL"]:
            breaks = []
            part2_yes = [f for f in self.facts if f.kind == "app_answer" and ":" in f.key and f.relevant]
            if part2_yes: breaks.append("Part 2 yes")
            rx_hi = [f for f in self.facts if f.kind == "rx_fill" and RX.get(f.key, [0, 0, "low"])[2] == "high"]
            if rx_hi: breaks.append("high-impact Rx")
            mib_med = [f for f in self.facts if f.kind == "mib_code" and f.key[0] in "123456" and f.relevant]
            if mib_med: breaks.append("MIB code")
            if any(f.kind == "mvr_violation" and MVRC[f.key]["class"] in ("major", "dui") for f in self.facts): breaks.append("MVR major")
            if self.x.get("bmi", 25) > 33: breaks.append("build")
            if (t.person.years_in_us or 99) < 5 or t.person.citizenship != "US": breaks.append("foreign")
            tob = next((f for f in self.facts if f.key == "tobacco"), None)
            if tob and tob.value == "No" and any(f.key == "varenicline" for f in self.facts): breaks.append("tobacco ambiguity")
            if breaks:
                grid = list(REQ["grid"][ai][min(fi + 1, 4)])
                grid = [g for g in grid if g != "ACCEL"] or ["PM", "B", "U"]
                reasons = {g: f"REQ-3 accel fails ({', '.join(breaks)}) -> next column" for g in grid}
        if (t.person.years_in_us or 99) < 5 and t.person.citizenship != "US":
            for g in ("PM", "B", "U"):
                reasons.setdefault(g, "FN-2 recent immigrant: full fluids")
        # REQ-2 triggers
        aps = []
        for i, c in ratable:
            if c.details.get("untraceable") or self.trace[i] == 0:
                continue
            item = next((it for it in self.row["items"] if it["key"] == c.condition_key), {})
            big = item.get("debits", 0) >= 50 or item.get("outcome") in ("postpone", "decline")
            discrep = c.disclosure in ("omitted", "minimized")
            if big or discrep or item.get("best"):
                for pid in c.treating_provider_ids:
                    aps.append((pid, "REQ-2.2 app vs 3rd-party discrepancy" if discrep else "REQ-2.1 impairment may rate >= +50" if big else
                                "chapter order: confirm control/class cap"))
        if "APS" in reasons:
            aps.append((t.providers[0].provider_id, reasons.pop("APS")))
        if "APS" in grid:
            grid.remove("APS")
        seen, aps_final = set(), []
        for pid, why in aps:
            if pid not in seen:
                seen.add(pid); aps_final.append((pid, why))
        n_target = max(self.row.get("n_aps", 0), 1 if aps_final else 0)
        aps_final = aps_final[: max(n_target, min(len(aps_final), 2))]
        if self.row.get("n_aps", 0) > len(aps_final):    # design wants more records: add PCP / other treating providers
            for p in t.providers:
                if p.provider_id not in seen and len(aps_final) < self.row["n_aps"]:
                    seen.add(p.provider_id); aps_final.append((p.provider_id, "REQ-4 additional treating provider"))
        if any(f.kind == "mvr_violation" and MVRC[f.key]["class"] == "dui" and (t.app_date - f.as_of).days < 5 * 365 for f in self.facts):
            reasons.setdefault("B", "REQ-2.4 DUI within 5 yrs"); reasons["ALCQ"] = "REQ-2.4 DUI within 5 yrs"
        if any(a.activity not in ("hiking", "recreational boating", "hunting", "marathon running", "martial arts", "skiing") for a in t.avocations):
            reasons["AVOQ"] = "REQ-2.5 avocation/aviation disclosed or indicated"
        if t.travel and any(tr.purpose != "vacation" for tr in t.travel) or t.person.country_of_residence != "US" or t.person.citizenship != "US":
            reasons["FORQ"] = "REQ-2.6 foreign national / travel"
        if self.x.get("fin_ratio", 0) > 1.0 or "KPE" in t.coverage.riders_requested:
            reasons.setdefault("FINQ", "FIN-2 over limit / KPE")
        grid_set = set(reasons)
        if self.row["tobacco_disclosure"] in ("omitted", "minimized") and not ({"B", "U", "S"} & grid_set):
            reasons["S"] = "REQ-2.3 tobacco evidence ambiguous"
        return reasons, aps_final

    # ------------------------------------------------------------------ ordered evidence
    def paramed(self, reason, ordered):
        t, r = self.t, self.r
        v = self.row["vendors"]["paramed"]
        when = ordered + timedelta(days=r.randint(3, 14), hours=r.randint(0, 8))
        h = t.height_in + r.choice([0, 0, 0, -0.5, 0.5])
        w = t.weight_lb + r.randint(-3, 3)
        bps = [(t.bp_systolic + r.randint(-6, 6), t.bp_diastolic + r.randint(-4, 4)) for _ in range(VEND["paramed_vendors"][v]["readings"])]
        avg = (round(sum(b[0] for b in bps) / len(bps)), round(sum(b[1] for b in bps) / len(bps)))
        qa = {}
        if VEND["paramed_vendors"][v]["includes_questions"]:
            for i, c in self.cond_refs():   # examiner re-asks: some omissions get disclosed here
                if c.disclosure == "omitted" and not c.irrelevant and r.random() < 0.25:
                    qa[c.label] = "applicant mentioned to examiner"
        did = self.doc("paramed", v, when + timedelta(hours=6), ordered=ordered, reason=reason,
                       content={"vendor": v, "exam_date": when.date().isoformat(), "height_in": h, "weight_lb": w, "bp": bps, "pulse": t.pulse + r.randint(-4, 4),
                                "examiner_notes": qa})
        self.fact(did, "paramed", "build", {"height_in": h, "weight_lb": w}, as_of=when.date())
        self.fact(did, "paramed", "bp", {"readings": bps, "avg": avg}, as_of=when.date())
        self.fact(did, "paramed", "pulse", t.pulse, unit="bpm", as_of=when.date(), relevant=False)
        for i, c in self.cond_refs():
            if c.label in qa:
                self.fact(did, "paramed_disclosure", c.condition_key, qa[c.label], truth_ref=f"conditions[{i}]", note="disclosed to examiner, not on app")
                self.trace[i] += 1
        return did, when

    def labs(self, reasons, exam_at):
        t, r = self.t, self.r
        out = []
        lv = self.row["vendors"]["lab"]
        L = t.true_labs
        collected = exam_at.date()
        if "B" in reasons or "U" in reasons:
            res_at = exam_at + timedelta(days=r.randint(2, 5))
            blood = {k: L[k] for k in ("tc", "hdl", "ldl", "triglycerides", "tc_hdl_ratio", "glucose_fasting", "a1c", "ast", "alt", "ggt",
                                       "alk_phos", "bilirubin", "albumin", "creatinine", "egfr", "hemoglobin", "hiv", "cdt") if k in L}
            if "psa" in L:
                blood["psa"] = L["psa"]
            if "NTPROBNP" in reasons or t.person.age >= 50:
                blood["nt_probnp"] = L["nt_probnp"]
            fasting = r.random() < 0.7
            if not fasting:
                blood["glucose_random"] = blood.pop("glucose_fasting") + r.randint(10, 45)
            dB = self.doc("lab_blood", lv, res_at, ordered=exam_at - timedelta(days=1), reason=reasons.get("B", "REQ-1 grid"),
                          content={"vendor": lv, "collected": collected.isoformat(), "fasting": fasting, "results": blood})
            urine = {"cotinine_urine": L["cotinine_urine"], "urine_protein": L["urine_protein"], "cocaine": L["cocaine"],
                     "urine_glucose": 1 if L["a1c"] >= 7.5 else 0, "urine_rbc": r.choice([0, 0, 1, 2, 8])}
            dU = self.doc("lab_urine", lv, res_at + timedelta(minutes=5), ordered=exam_at - timedelta(days=1), reason=reasons.get("U", "REQ-1 grid"),
                          content={"vendor": lv, "collected": collected.isoformat(), "results": urine})
            for k, v in blood.items():
                self.fact(dB, "lab_value", k, v, unit=LABS.get(k, {}).get("unit"), as_of=collected, relevant=self.lab_relevant(k, v))
            for k, v in urine.items():
                self.fact(dU, "lab_value", k, v, unit=LABS.get(k, {}).get("unit"), as_of=collected, relevant=self.lab_relevant(k, v))
            out += [dB, dU]
        if "S" in reasons:
            res_at = exam_at + timedelta(days=r.randint(2, 4))
            sal = {"cotinine_saliva": max(0, round(L["cotinine_urine"] / r.uniform(6, 9))), "hiv": L["hiv"], "cocaine": L["cocaine"]}
            dS = self.doc("lab_saliva", lv if lv != "NGL" else "MIL", res_at, ordered=exam_at - timedelta(days=1), reason=reasons["S"],
                          content={"vendor": lv, "collected": collected.isoformat(), "results": sal})
            for k, v in sal.items():
                self.fact(dS, "lab_value", k, v, unit="ng/mL" if k.startswith("cot") else "qual", as_of=collected, relevant=self.lab_relevant(k, v))
            out.append(dS)
        return out

    def lab_relevant(self, k, v):
        if k in ("tc", "hdl", "tc_hdl_ratio", "cotinine_urine", "cotinine_saliva"):
            return True
        th = {"a1c": 5.6, "glucose_fasting": 109, "glucose_random": 139, "ast": 60, "alt": 67, "ggt": 120, "alk_phos": 195, "bilirubin": 1.5,
              "cdt": 1.6, "egfr": None, "urine_protein": 30, "hemoglobin": None, "psa": 2.5, "nt_probnp": 124, "triglycerides": 500}
        if k == "egfr":
            return v < 60
        if k == "hemoglobin":
            return v < (13 if self.t.person.sex == "M" else 12)
        if k == "albumin":
            return v < 3.5
        if k in ("hiv", "cocaine", "urine_glucose"):
            return bool(v)
        if k == "urine_rbc":
            return v > 5
        return k in th and th[k] is not None and v > th[k]

    def ekg(self, reason, at):
        t = self.t
        f = "normal sinus rhythm"
        for c in t.conditions:
            if c.condition_key == "afib" and c.details.get("type") in ("persistent", "permanent"):
                f = "atrial fibrillation, controlled ventricular rate"
            if c.condition_key == "arrhythmia_other" and c.details.get("kind") in ("lbbb", "rbbb"):
                f = {"lbbb": "left bundle branch block", "rbbb": "right bundle branch block"}[c.details["kind"]]
            if c.condition_key == "hypertension" and c.details.get("lvh"):
                f = "sinus rhythm, LVH by voltage criteria"
            if c.condition_key == "cad" and c.details.get("event") == "MI":
                f = "sinus rhythm, Q waves inferior leads (old infarct)"
        did = self.doc("ekg", "PMX", at + timedelta(hours=8), ordered=at - timedelta(days=1), reason=reason, content={"interpretation": f, "rate": t.pulse})
        self.fact(did, "ekg", "interpretation", f, as_of=at.date(), relevant=f != "normal sinus rhythm")
        return did

    def questionnaires(self, reasons):
        t, r = self.t, self.r
        for code in ("ALCQ", "AVOQ", "FORQ", "FINQ"):
            if code not in reasons:
                continue
            at = self.t0 + timedelta(days=r.randint(3, 15))
            content = {"type": code}
            if code == "AVOQ":
                content["activities"] = [{"activity": a.activity, **a.details} for a in t.avocations]
            if code == "FORQ":
                content["travel"] = [tr.model_dump() for tr in t.travel]
                content["citizenship"] = t.person.citizenship; content["visa"] = t.person.visa_type; content["years_in_us"] = t.person.years_in_us
                content["residence"] = t.person.country_of_residence
            if code == "FINQ":
                content.update({"income": t.person.annual_income, "net_worth": t.person.net_worth, "existing": t.coverage.existing_coverage,
                                "purpose": "business" if "KPE" in t.coverage.riders_requested else r.choice(["income replacement", "estate", "mortgage"])})
            if code == "ALCQ":
                content.update({"drinks_per_week": t.alcohol_drinks_per_week, "treatment": t.alcohol_treatment})
            did = self.doc("other", code, at, ordered=self.t0 + timedelta(hours=2), reason=reasons[code], content=content)
            for k, v in content.items():
                if k != "type":
                    self.fact(did, "questionnaire", f"{code}:{k}", v)

    def aps(self, pid, why, idx):
        """Structured APS spec; prose rendering happens in Phase 4c."""
        t, r = self.t, self.r
        p = next(p for p in t.providers if p.provider_id == pid)
        ordered = self.t0 + timedelta(days=r.randint(0, 2), hours=r.randint(1, 6))
        received = ordered + timedelta(days=r.randint(7, 40))
        stale = self.row.get("grey") == "GRY-5" and idx == 0
        last_visit = t.app_date - timedelta(days=r.randint(760, 1200) if stale else r.randint(10, 300))
        span_years = r.uniform(2, 5)
        is_pcp = p.specialty in ("family medicine", "internal medicine")
        conds = [(i, c) for i, c in self.cond_refs() if not c.details.get("untraceable") and (pid in c.treating_provider_ids or is_pcp)]
        problems, findings = [], []
        for i, c in conds:
            entry = {"cond_index": i, "dx": c.label, "key": c.condition_key, "onset": c.onset.isoformat(), "status": c.status,
                     "details": {k: v for k, v in c.details.items() if k != "untraceable"}, "meds": [m.drug + " " + m.dose for m in c.meds]}
            if c.condition_key == "cancer" and c.details.get("stage_documented") is False:
                entry["details"].pop("stage", None)
            problems.append(entry)
            self.trace[i] += 1
        # visits
        nv = r.randint(3, 9) if p.aps_style != "specialist_letter" else 1
        visits = []
        for k in range(nv):
            vd = last_visit - timedelta(days=int(k * span_years * 365 / max(1, nv)))
            focus = r.choice(conds)[1].label if conds and r.random() < 0.7 else r.choice(
                ["URI", "annual physical", "ankle sprain", "medication refill", "rash", "back strain", "flu shot", "lab review"])
            visits.append({"date": vd.isoformat(), "reason": focus, "bp": f"{t.bp_systolic + r.randint(-8, 8)}/{t.bp_diastolic + r.randint(-6, 6)}",
                           "weight_lb": t.weight_lb + r.randint(-8, 8)})
        # serial values for key conditions (A1c history etc.)
        series = {}
        for i, c in conds:
            if c.condition_key in ("diabetes_t2", "diabetes_t1", "prediabetes") and c.details.get("a1c_available", True):
                base = c.details.get("a1c_avg") or 6.0
                trend = r.choice([-0.4, 0, 0.3]) if self.row.get("grey") != "GRY-1" else -0.6
                series["a1c"] = [{"date": v["date"], "value": round(base + trend * (j / max(1, nv - 1)) + r.uniform(-0.2, 0.2), 1)} for j, v in enumerate(visits[:4])]
            if c.condition_key == "ckd" and "egfr" in c.details:
                series["egfr"] = [{"date": v["date"], "value": c.details["egfr"] + r.randint(-4, 4)} for v in visits[:3]]
        noncompliant = r.random() < 0.08
        rule_outs = []
        mib_unc = [f for f in self.facts if f.kind == "mib_code" and f.note == "uncorroborated"]
        if mib_unc and (self.row.get("grey") == "GRY-8" or r.random() < 0.3):
            rule_outs.append(MIB["conditions"][mib_unc[0].key[:3]]["label"])
        old_lab = None
        if self.row.get("legacy_lab") and idx == 0:
            yr = r.randint(2009, 2014)
            old_lab = {"vendor": "HRT", "date": date(yr, r.randint(1, 12), r.randint(1, 28)).isoformat(),
                       "results": {"tc": t.true_labs["tc"] + r.randint(-30, 30), "hdl": t.true_labs["hdl"] + r.randint(-6, 6),
                                   "fructosamine": r.randint(220, 300), "cotinine_qual": "NEG" if t.true_labs["cotinine_urine"] < 200 else "POS",
                                   "ggt": r.randint(15, 60)}}
        pages = r.randint(*VEND["aps_styles"][p.aps_style]["pages"])
        spec = {"provider": p.model_dump(), "style": p.aps_style, "ordered_reason": why, "last_visit": last_visit.isoformat(), "stale": stale,
                "problems": problems, "visits": visits, "series": series, "noncompliant": noncompliant, "rule_outs": rule_outs,
                "legacy_lab": old_lab, "exercise_documented": r.random() < 0.2, "pages": pages,
                "copy_forward": VEND["aps_styles"][p.aps_style].get("copy_forward", False),
                "patient": {"name": f"{t.person.first_name} {t.person.last_name}", "dob": t.person.dob.isoformat(), "sex": t.person.sex},
                "tobacco_documented": [u.model_dump(mode="json") for u in t.tobacco], "alcohol_dpw": t.alcohol_drinks_per_week,
                "family_history": [f.model_dump() for f in t.family_history][:3]}
        did = self.doc("aps", p.aps_style, received, ordered=ordered, reason=why, pages=pages, content=spec)
        for pr in problems:
            c = t.conditions[pr["cond_index"]]
            self.fact(did, "aps_finding", f"dx:{pr['key']}", {"dx": pr["dx"], "onset": pr["onset"], "status": pr["status"], **pr["details"]},
                      as_of=last_visit, relevant=not c.irrelevant, truth_ref=f"conditions[{pr['cond_index']}]",
                      note="not disclosed on app" if c.disclosure == "omitted" and not c.irrelevant else None)
        for k, s in series.items():
            self.fact(did, "aps_finding", f"series:{k}", s, as_of=date.fromisoformat(s[0]["date"]))
        if visits:
            self.fact(did, "aps_finding", "bp_readings", [v["bp"] for v in visits[:3]], as_of=date.fromisoformat(visits[0]["date"]), relevant=False)
        if noncompliant:
            self.fact(did, "aps_finding", "noncompliance", "patient non-compliant with medications / missed follow-ups", as_of=last_visit)
        for ro in rule_outs:
            self.fact(did, "aps_finding", "rule_out", f"r/o {ro}", as_of=last_visit, note="uncorroborated suspicion")
        if stale:
            self.fact(did, "aps_finding", "last_visit", last_visit.isoformat(), note="stale > 24 months")
        if old_lab:
            self.fact(did, "aps_finding", "legacy_lab", old_lab, as_of=date.fromisoformat(old_lab["date"]), relevant=False, note="legacy method")
        if spec["exercise_documented"]:
            self.fact(did, "aps_finding", "exercise", "runs 3-4x/week", as_of=last_visit, relevant=False)
        return did

    # ------------------------------------------------------------------ build all
    def make(self):
        self.misrep = False
        self.app()
        self.rx()
        self.mib()
        self.mvr()
        # omitted, traceable conditions with no trace yet -> force an MIB-style trace via APS later; record
        reasons, aps = self.requirements()
        exam_at = None
        if "PM" in reasons or "B" in reasons or "S" in reasons:
            _, exam_at = self.paramed(reasons.get("PM", "REQ-1 grid"), self.t0 + timedelta(hours=3))
            self.labs(reasons, exam_at)
            if "EKG" in reasons:
                self.ekg(reasons["EKG"], exam_at)
        self.questionnaires(reasons)
        for k, (pid, why) in enumerate(aps):
            self.aps(pid, why, k)
        # traceability audit
        untraced = [i for i, c in self.cond_refs() if not c.irrelevant and not c.details.get("untraceable") and self.trace[i] == 0]
        self.docs.sort(key=lambda d: d.received_at)
        # renumber docs chronologically? keep ids stable (ids reflect generation order); facts reference ids.
        return EvidenceBundle(case_id=self.t.case_id, facts=self.facts, docs=self.docs), {"requirements": reasons, "aps": aps, "untraced": untraced}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    files = sorted((ROOT / "data/truth").glob("C*.json"))
    if a.ids:
        files = [f for f in files if f.stem in set(a.ids.split(","))]
    if a.limit:
        files = files[: a.limit]
    stats, errs = Counter(), []
    for f in files:
        t = Truth.model_validate_json(f.read_text())
        try:
            g = EvidenceGen(t)
            ev, meta = g.make()
            EvidenceBundle.model_validate_json(ev.model_dump_json())
            out = ROOT / "data/source" / t.case_id
            out.mkdir(parents=True, exist_ok=True)
            (out / "evidence.json").write_text(ev.model_dump_json(indent=1))
            (out / "content.json").write_text(json.dumps({"meta": meta, "docs": g.content}, indent=1, default=str))
            stats["cases"] += 1
            stats["facts"] += len(ev.facts)
            stats["relevant"] += sum(f.relevant for f in ev.facts)
            stats["docs"] += len(ev.docs)
            stats["aps"] += sum(d.doc_type == "aps" for d in ev.docs)
            stats["untraced_conditions"] += len(meta["untraced"])
            for d in ev.docs:
                stats[f"doc:{d.doc_type}"] += 1
        except Exception as ex:  # noqa: BLE001
            import traceback
            errs.append(f"{t.case_id}: {type(ex).__name__}: {ex} @ {traceback.extract_tb(ex.__traceback__)[-1].lineno}")
    print({k: v for k, v in stats.items() if not k.startswith("doc:")})
    print({k[4:]: v for k, v in sorted(stats.items()) if k.startswith("doc:")})
    for e in errs[:15]:
        print("ERR", e)
    print(f"errors: {len(errs)}")


if __name__ == "__main__":
    main()
