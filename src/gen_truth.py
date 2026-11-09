"""Phase 4a: design row -> Truth (latent ground truth), validated against schemas.Truth.

Run: python src/gen_truth.py [--ids C0001,C0002] [--limit N]    writes data/truth/<case>.json + qa/phase4a_truth.md
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from faker import Faker  # noqa: E402

from rules import first_profile, load, match, pred_ok  # noqa: E402
from schemas import (Avocation, Condition, Coverage, FamilyHistoryItem, MedUse, MvrEvent, Person,  # noqa: E402
                     PriorApplication, Provider, TobaccoUse, Travel, Truth)

ROOT = Path(__file__).resolve().parents[1]
IMP = load("impairments")
CLS = load("classes")
BUILD = load("build")
RX = load("rx_map")["drugs"]
OCC = load("occupations")["occupations"]
TIERS = load("country_tiers")
STATES = ["CA", "TX", "FL", "NY", "PA", "IL", "OH", "GA", "NC", "MI", "NJ", "VA", "WA", "AZ", "MA", "TN", "IN", "MO", "MD",
          "WI", "CO", "MN", "SC", "AL", "LA", "KY", "OR", "OK", "CT", "UT", "IA", "NV", "AR", "KS", "NM", "NE", "ID", "ME"]

# global attribute domains: (lo, hi, kind, p_none)  kind: i=int f=float h=half-steps
NUM = {
    "years_since": (0.2, 30, "f", 0), "ef": (20, 70, "i", 0), "vessels": (1, 4, "i", 0), "ldl": (40, 190, "i", 0),
    "chads_vasc": (0, 5, "i", 0), "ablation_years": (0, 12, "f", 0.7), "a1c_avg": (5.0, 12.0, "f", 0),
    "duration_years": (0, 30, "i", 0), "age_at_dx": (15, 75, "i", 0), "meds_count": (1, 4, "i", 0),
    "work_loss_months": (0, 6, "i", 0.6), "hospitalization_years_ago": (0, 20, "f", 0.7), "years_since_dx": (0.3, 30, "f", 0),
    "stable_years": (0, 20, "f", 0), "steroid_bursts_per_year": (0, 4, "i", 0.6), "er_years_ago": (0, 10, "f", 0.6),
    "fev1_pct": (25, 95, "i", 0), "ahi": (5, 80, "i", 0), "surgery_years_ago": (0, 15, "f", 0.6),
    "colonoscopy_years_ago": (0, 10, "f", 0), "seizures_per_year": (0, 8, "i", 0.4), "seizure_free_years": (0, 20, "f", 0),
    "edss": (0, 8, "h", 0), "age_at_onset": (30, 80, "i", 0), "cd4": (200, 1200, "i", 0), "art_years": (0, 20, "f", 0),
    "undetectable_months": (0, 120, "i", 0), "transplant_years": (0, 15, "f", 0.7), "size_cm": (3.0, 6.0, "f", 0),
    "repaired_months": (0, 60, "i", 0.7), "repaired_years": (0, 15, "f", 0.7), "stenosis_pct": (0, 99, "i", 0),
    "cac_score": (0, 1000, "i", 0.5), "recovered_years": (0, 10, "f", 0), "egfr": (15, 110, "i", 0),
    "years_since_tx": (0.2, 25, "f", 0), "recovered_years_": (0, 10, "f", 0),
}
P_TRUE = 0.3


def r1(x):
    return round(x, 1)


class TruthGen:
    def __init__(self, row: dict):
        self.row = row
        self.r = random.Random(row["seed"])
        self.fk = Faker("en_US")
        self.fk.seed_instance(row["seed"])
        self.log: list[str] = []
        d0, d1 = date(2025, 1, 6), date(2026, 10, 30)
        self.app_date = d0 + timedelta(days=self.r.randint(0, (d1 - d0).days))
        self.age = row["age"]
        self.providers: list[Provider] = []

    # ------------------------------------------------------------------ helpers
    def ago(self, years: float) -> date:
        return self.app_date - timedelta(days=int(years * 365.25))

    def sample_num(self, name, pred=None):
        lo, hi, kind, p_none = NUM.get(name, (0, 10, "f", 0))
        if name in ("years_since", "years_since_dx", "years_since_tx", "duration_years", "stable_years", "art_years"):
            hi = min(hi, max(0.5, self.age - 16))
        for _ in range(200):
            if pred is None and p_none and self.r.random() < p_none:
                return None
            v = self.r.uniform(lo, hi)
            v = int(round(v)) if kind == "i" else round(v * 2) / 2 if kind == "h" else r1(v)
            if pred is None or pred_ok(v, pred):
                return v
        # predicate outside global domain: construct directly
        if isinstance(pred, list):
            return pred[0]
        for op in ("ge", "gt", "le", "lt"):
            if op in pred:
                x = pred[op]
                return x + (1 if op == "gt" else 0) if op in ("ge", "gt") else x - (1 if op == "lt" else 0)
        return lo

    def satisfy(self, name, pred, cat_domain):
        if isinstance(pred, bool):
            return pred
        if isinstance(pred, (str,)):
            return pred
        if isinstance(pred, dict) and "in" in pred:
            return self.r.choice(pred["in"])
        if isinstance(pred, (int, float)) and not isinstance(pred, bool):
            return pred
        return self.sample_num(name, pred)

    def domains(self, key):
        """attribute -> ('bool'|'num'|list of categoricals), derived from the catalog."""
        e = IMP[key]
        dom = {a: None for a in e.get("attributes", [])}
        cats: dict[str, set] = {}
        for p in e.get("profiles", []):
            for k, v in (p.get("match") or {}).items():
                items = v.items() if k == "any_of" else [(k, v)]
                for k2, v2 in items:
                    if isinstance(v2, bool):
                        dom[k2] = "bool"
                    elif isinstance(v2, str):
                        cats.setdefault(k2, set()).add(v2)
                    elif isinstance(v2, dict) and "in" in v2:
                        cats.setdefault(k2, set()).update(v2["in"])
                    else:
                        dom.setdefault(k2, "num")
                        if dom[k2] is None:
                            dom[k2] = "num"
        for k, vs in cats.items():
            dom[k] = sorted(vs) + ["other"]
        for a in list(dom):
            if dom[a] is None:
                dom[a] = "num" if a in NUM else "bool"
        dom.pop("age", None)
        return dom

    def random_attrs(self, dom):
        out = {}
        for a, d in dom.items():
            if d == "bool":
                out[a] = self.r.random() < P_TRUE
            elif d == "num":
                out[a] = self.sample_num(a)
            else:
                out[a] = self.r.choice(d)
        return out

    def realize_profile(self, key, pid):
        """attrs such that first_profile(key, attrs) is profile pid."""
        prof = next(p for p in IMP[key]["profiles"] if p["id"] == pid)
        dom = self.domains(key)
        m = prof.get("match") or {}
        for _ in range(400):
            a = self.random_attrs(dom)
            for k, v in m.items():
                if k == "any_of":
                    k2, v2 = self.r.choice(list(v.items()))
                    a[k2] = self.satisfy(k2, v2, dom.get(k2))
                elif k != "age":
                    a[k] = self.satisfy(k, v, dom.get(k))
            a["age"] = self.age
            if "age" in m and not pred_ok(self.age, m["age"]):
                break
            got = first_profile(key, a)
            if got and got["id"] == pid:
                return a
        self.log.append(f"could not realize {key}:{pid} exactly")
        a["age"] = self.age
        return a

    def provider(self, specialty, style=None):
        for p in self.providers:
            if p.specialty == specialty:
                return p
        styles = list(self.row["aps_styles"])
        used = {p.aps_style for p in self.providers}
        free = [s for s in styles if s not in used]
        st = style or (free[0] if free else self.r.choice(["epic_progress", "athena_summary", "small_practice_typed"]))
        p = Provider(provider_id=f"{self.row['case_id']}-P{len(self.providers) + 1}",
                     name=f"Dr. {self.fk.first_name()} {self.fk.last_name()}", specialty=specialty,
                     practice=self.fk.company().replace(",", "") + (" Medical Group" if self.r.random() < 0.5 else " Clinic"),
                     aps_style=st, country="US" if st != "foreign_translated" else self.foreign_country or "Mexico")
        self.providers.append(p)
        return p

    # ------------------------------------------------------------------ sections
    def person(self):
        row, r = self.row, self.r
        sex = row["sex"]
        first = self.fk.first_name_male() if sex == "M" else self.fk.first_name_female()
        dob = self.app_date - timedelta(days=int(self.age * 365.25) + r.randint(-180, 180))
        nm = {i["key"]: i for i in row["items"] if i["kind"] == "nm"}
        occ = None
        if "nm_occupation" in nm:
            v = nm["nm_occupation"]["variant"]
            pool = {"occ_4a": ["structural iron worker", "offshore oil rig worker", "tower climber (telecom)", "underground miner"],
                    "occ_4a_hi": ["commercial fisherman", "logger", "crop duster pilot"],
                    "occ_5a": ["bomb disposal technician", "wildland smoke jumper", "private security contractor (overseas)"],
                    "deploying": ["special forces (deploying)"]}[v]
            occ = r.choice(pool)
        elif self.age >= 68 and r.random() < 0.7:
            occ = "retired"
        elif self.age <= 23 and r.random() < 0.5:
            occ = "student"
        else:
            occ = r.choice([o for o, v in OCC.items() if v["class"] in ("1A", "2A", "3A") and o not in ("retired", "student")
                            and "deploying" not in o])
        self.occupation = occ
        # finance: justify face unless FIN item says otherwise (FIN-1)
        mult = next(m for lo, hi, m in load("nonmedical")["financial"]["multiples"] if lo <= min(self.age, 70) <= hi) \
            if self.age <= 70 else None
        face = row["face"]
        fin = nm.get("nm_financial", {}).get("variant")
        if fin == "overins_counter":
            ratio = r.uniform(1.15, 1.9)
        elif fin == "overins_decline":
            ratio = r.uniform(2.2, 4.0)
        else:
            ratio = r.uniform(0.25, 0.95)
        non_earning = OCC[occ].get("tags", []) and "non_earning" in OCC[occ].get("tags", [])
        if mult:
            income = int(face / (mult * ratio) / 1000) * 1000
            income = max(income, 18000)
        else:
            income = int(r.uniform(20000, 90000) / 1000) * 1000
        networth = int(income * r.uniform(1, 12) / 1000) * 1000
        if not mult:   # 71+: net worth basis (50%)
            networth = int(face / (0.5 * ratio) / 1000) * 1000
        if non_earning and occ in ("retired", "homemaker", "unemployed"):
            income = 0 if occ != "retired" else int(networth * 0.04)
        self.fin_ratio = ratio
        # citizenship / foreign
        cit, country, yrs_us, visa = "US", "US", None, None
        self.foreign_country = None
        fv = nm.get("nm_foreign", {}).get("variant")
        if fv == "visa_ineligible":
            visa = r.choice(["F-1", "B-1/B-2"]); cit = r.choice(TIERS["B"] + TIERS["C"]); yrs_us = r1(r.uniform(0.2, 3))
        elif fv == "visa_eligible":
            visa = r.choice(["H-1B", "L-1", "E-2", "O-1", "TN"]); cit = r.choice(TIERS["A"] + TIERS["B"]); yrs_us = r1(r.uniform(1.1, 8))
        elif fv == "citizen_abroad_C":
            country = r.choice(TIERS["C"])
        elif row["foreign"]:
            kind = r.choice(["green_card_recent", "visa_eligible", "naturalized_recent"])
            cit = r.choice(TIERS["A"] + TIERS["B"] + TIERS["C"])
            yrs_us = r1(r.uniform(1.1, 4.9))
            visa = {"green_card_recent": "Permanent Resident", "visa_eligible": r.choice(["H-1B", "L-1"]),
                    "naturalized_recent": None}[kind]
            if kind == "naturalized_recent":
                cit = "US"
        if cit != "US" or country != "US":
            self.foreign_country = cit if cit != "US" else country
        if row["foreign"] and not self.foreign_country:
            self.foreign_country = r.choice(TIERS["B"] + TIERS["C"])
        return Person(first_name=first, last_name=self.fk.last_name(), sex=sex, dob=dob, age=self.age,
                      address_state=r.choice(STATES) if country == "US" else "N/A", country_of_residence=country,
                      citizenship=cit, years_in_us=yrs_us, visa_type=visa, occupation=occ,
                      occupation_class=OCC[occ]["class"], annual_income=income, net_worth=networth,
                      marital_status=r.choice(["married", "married", "single", "divorced", "widowed" if self.age > 55 else "single"]),
                      dependents=r.choice([0, 0, 1, 2, 3]) if self.age < 60 else r.choice([0, 0, 1]))

    def level_for(self, rowname):
        m = self.row["matrix"]
        for rn, lvl in m["fails"]:
            if rn == rowname:
                return lvl
        return m["base"]

    def build(self, nm):
        r = self.r
        h = r.randint(60, 74) if self.row["sex"] == "M" else r.randint(58, 69)
        bands = [b["max_bmi"] for b in BUILD["upper_bands"]]
        labels = [b["label"] for b in BUILD["upper_bands"]]
        it = nm.get("nm_build")
        if it:
            v = it["variant"]
            if v.startswith("over_") and v != "over_decline":
                d = int(v.split("_")[1])
                i = next(i for i, b in enumerate(BUILD["upper_bands"]) if b["debits"] == d)
                lo, hi = bands[i - 1], bands[i]
            elif v == "over_decline":
                lo, hi = 47.2, 52
            elif v == "under_25":
                lo, hi = 17.05, 17.95
            elif v == "under_50":
                lo, hi = 16.05, 16.95
            elif v == "under_postpone":
                lo, hi = 14.5, 15.9
            else:  # bariatric_recent: current BMI ~ Std; pre-op heavy
                lo, hi = 28, 33
        else:
            lvl = self.level_for("build")
            col = {"Elite": "Elite", "Preferred Plus": "Pref Plus", "Preferred": "Preferred", "Standard Plus": "Std Plus",
                   "Standard": "Standard"}.get(lvl, "Standard")
            i = labels.index(col)
            lo, hi = (19.5 if i == 0 else bands[i - 1] + 0.1), bands[i] - 0.05
            if self.row["target"] not in ("Elite", "Preferred Plus", "Preferred", "Standard Plus", "Standard", "Preferred Tobacco") \
                    and not it:
                lo, hi = 20.0, 32.9
        bmi = r.uniform(lo, hi)
        w = round(bmi * h * h / 703)
        self.bmi = bmi
        return h, w

    def bp(self, items):
        r = self.r
        htn = next((i for i in items if i["key"] == "hypertension"), None)
        if htn:
            band = htn["params"].get("bp_band", "<=140/90")
            rng = {"<=140/90": ((118, 138), (72, 88)), "141-150/91-95": ((141, 150), (80, 95)),
                   "151-160/96-100": ((151, 160), (85, 100)), "161-170/101-105": ((161, 170), (90, 105)),
                   "171-180/106-110": ((171, 180), (95, 110)), ">180/110": ((182, 200), (100, 118))}[band]
            if band == "<=140/90" and self.row["target"] in ("Elite", "Preferred Plus", "Preferred", "Standard Plus"):
                lvl = self.row["target"]
                th = CLS["preferred_matrix"]["classes"][lvl]["bp_under60" if self.age < 60 else "bp_60plus"]
                rng = ((max(112, th["sys"] - 12), th["sys"]), (max(68, th["dia"] - 10), th["dia"]))
            return r.randint(*rng[0]), r.randint(*rng[1])
        lvl = self.level_for("bp")
        if lvl not in CLS["preferred_matrix"]["classes"]:
            lvl = "Standard Plus"
        bk = "bp_under60" if self.age < 60 else "bp_60plus"
        th = CLS["preferred_matrix"]["classes"][lvl][bk]
        order = ["Elite", "Preferred Plus", "Preferred", "Standard Plus"]
        if lvl == "Elite":
            sys_, dia = r.randint(th["sys"] - 16, th["sys"]), r.randint(th["dia"] - 12, th["dia"])
        else:   # exact band: within this class, worse than the next-better class on sys or dia
            better = CLS["preferred_matrix"]["classes"][order[order.index(lvl) - 1]][bk]
            if r.random() < 0.6 and better["sys"] < th["sys"]:
                sys_, dia = r.randint(better["sys"] + 1, th["sys"]), r.randint(th["dia"] - 12, th["dia"])
            else:
                sys_, dia = r.randint(th["sys"] - 16, th["sys"]), r.randint(min(better["dia"] + 1, th["dia"]), th["dia"])
        if self.row["target"] not in ("Elite", "Preferred Plus", "Preferred", "Standard Plus", "Standard", "Preferred Tobacco", "Standard Tobacco"):
            sys_, dia = r.randint(110, 140), r.randint(66, 90)
        return sys_, dia

    def lipids(self, nm, statin):
        r = self.r
        it = nm.get("nm_lipids")
        hdl = r.randint(38, 75)
        if it and it["variant"].startswith("lip_"):
            d = int(it["variant"].split("_")[1])
            tc = {25: r.randint(305, 345), 50: r.randint(355, 395), 75: r.randint(405, 460)}[d]
            hdl = max(hdl, math.ceil(tc / 9.5))
        else:
            lvl = self.level_for("lipids")
            if lvl not in CLS["preferred_matrix"]["classes"]:
                tcmax, ratiomax = 300, r.uniform(6.6, 7.0)
            else:
                c = CLS["preferred_matrix"]["classes"][lvl]
                tcmax, ratiomax = c["tc_max"], c["ratio_max"]
            order = ["Elite", "Preferred Plus", "Preferred", "Standard Plus"]
            if lvl in order and lvl != "Elite":
                rlo = CLS["preferred_matrix"]["classes"][order[order.index(lvl) - 1]]["ratio_max"] + 0.05
            elif lvl == "Elite":
                rlo = 2.8
            else:
                rlo = 6.55
            ratio = r.uniform(rlo, ratiomax - 0.03)
            hdl = r.randint(40, 72)
            tc = min(int(ratio * hdl), tcmax - r.randint(0, 25))
            if tc / hdl > ratiomax:
                hdl = math.ceil(tc / (ratiomax - 0.01))
        trig = r.randint(60, 220)
        if it and it["variant"] == "trig_high":
            trig = r.randint(520, 980)
        if it and it["variant"] == "hdl_low":
            hdl = r.randint(22, 29); tc = min(int(hdl * r.uniform(5.0, 6.8)), 199)
        ldl = max(40, int(tc - hdl - trig / 5))
        return tc, hdl, ldl, trig

    def tobacco(self):
        r = self.r
        pat, disc = self.row["tobacco"], self.row["tobacco_disclosure"]
        disc = {"na": "na"}.get(disc, disc)
        out, cot = [], r.uniform(0, 8)
        start = self.ago(r.uniform(5, max(6, self.age - 15)))
        quit_years = {"quit_1_2": (1.05, 1.95), "quit_2_3": (2.05, 2.95), "quit_3_5": (3.05, 4.95), "quit_5_10": (5.05, 9.9),
                      "quit_10plus": (10.1, max(10.2, self.age - 18)), "cig_quit_lt12": (0.1, 0.9)}
        if pat in quit_years:
            q = self.ago(r.uniform(*quit_years[pat]))
            out.append(TobaccoUse(product="cigarette", status="former", frequency=r.choice(["1/2 ppd", "1 ppd", "1.5 ppd", "10/day"]),
                                  start=min(start, q - timedelta(days=400)), quit=q, disclosure=disc if disc != "na" else "honest"))
            if pat == "cig_quit_lt12" and r.random() < 0.5:
                cot = r.uniform(250, 1200)
        elif pat in ("cig_current", "cig_current_heavy"):
            freq = "2 ppd" if pat.endswith("heavy") else r.choice(["1/2 ppd", "1 ppd", "5/day", "1 ppd"])
            out.append(TobaccoUse(product="cigarette", status="current", frequency=freq, start=start, disclosure=disc))
            cot = r.uniform(400, 4000)
        elif pat in ("vape", "chew", "pipe", "nrt"):
            prod = {"vape": "vape", "chew": "chew", "pipe": "pipe", "nrt": "nicotine_gum_patch"}[pat]
            out.append(TobaccoUse(product=prod, status="current", frequency=r.choice(["daily", "several times/day", "weekends"]),
                                  start=self.ago(r.uniform(1, 12)), disclosure=disc))
            cot = r.uniform(250, 2500)
        elif pat in ("cigars_cot_neg", "cigars_cot_pos"):
            out.append(TobaccoUse(product="cigar", status="current", frequency=f"{r.randint(2, 12)}/yr" if pat.endswith("neg") else
                                  f"{r.randint(2, 8)}/month", start=self.ago(r.uniform(2, 20)), disclosure=disc if disc != "na" else "honest"))
            cot = r.uniform(0, 60) if pat.endswith("neg") else r.uniform(220, 900)
        elif pat == "cessation_rx_only":
            q = self.ago(r.uniform(0.2, 0.8))
            out.append(TobaccoUse(product="cigarette", status="former", frequency="1 ppd", start=start, quit=q, disclosure=disc))
            cot = r.uniform(0, 150) if r.random() < 0.6 else r.uniform(300, 900)
            self.cessation_rx = q
        self.cotinine = round(cot)
        return out

    def mvr(self, nm):
        r, out = self.r, []
        codes = load("mvr_codes")["codes"]
        minors = [c for c, v in codes.items() if v["class"] == "minor"]
        majors = [c for c, v in codes.items() if v["class"] == "major" and c != "R06"]
        duis = ["D01", "D03", "D06", "D04"]
        it = nm.get("nm_mvr")
        disc = it["disclosure"] if it else "honest"
        v = it["variant"] if it else None

        def ev(code, y0, y1, d=disc):
            out.append(MvrEvent(date=self.ago(r.uniform(y0, y1)), code=code, disclosure=d if d in ("honest", "omitted", "minimized", "misremembered") else "omitted"))
        if v:
            if v.startswith("minor"):
                n = {"minor4": 4, "minor5_6": r.choice([5, 6]), "minor7": r.randint(7, 9)}[v]
                for _ in range(n):
                    ev(r.choice(minors), 0.1, 2.9)
            elif v.startswith("major"):
                for _ in range({"major1": 1, "major2": 2, "major3": 3}[v]):
                    ev(r.choice(majors), 0.2, 4.8)
            elif v == "dui_two_5y":
                ev(r.choice(duis), 0.5, 2.0); ev(r.choice(duis), 2.5, 4.8)
            else:
                rng = {"dui_lt1y": (0.1, 0.9), "dui_1_2y": (1.05, 1.95), "dui_2_5y": (2.05, 4.9), "dui_5_10y": (5.1, 9.8)}[v]
                ev(r.choice(duis), *rng)
                if v == "dui_lt1y" and r.random() < 0.5:
                    out.append(MvrEvent(date=out[-1].date + timedelta(days=30), code="L02", disclosure=out[-1].disclosure))
        else:
            lvl = self.level_for("mvr")
            allow = {"Elite": 0, "Preferred Plus": 1, "Preferred": 2, "Standard Plus": 3}.get(lvl, 3)
            if self.row["target"] not in ("Elite", "Preferred Plus", "Preferred", "Standard Plus", "Standard"):
                allow = 2
            for _ in range(r.randint(0, allow)):
                ev(r.choice(minors), 0.1, 2.9, "honest")
            if lvl != "Elite" and r.random() < 0.4:   # old, outside lookback / non-moving noise
                ev(r.choice(minors + ["N01", "N02", "N04", "A03", "M08"]), 3.2, 9.0, "honest")
        return out

    def family(self, nm):
        r, out = self.r, []
        lvl = self.level_for("family_history")
        if "nm_family" in nm:
            out += [FamilyHistoryItem(relation="father", condition="MI", age_at_death=r.randint(42, 58), living=False),
                    FamilyHistoryItem(relation=r.choice(["brother", "mother"]), condition="sudden cardiac death",
                                      age_at_death=r.randint(38, 59), living=False)]
        elif lvl == "Standard Plus" and self.age < 70:
            out += [FamilyHistoryItem(relation="mother", condition="breast cancer", age_at_onset=r.randint(40, 52), age_at_death=r.randint(45, 58), living=False),
                    FamilyHistoryItem(relation="father", condition="stroke", age_at_death=r.randint(50, 59), living=False)]
        elif lvl == "Preferred" and r.random() < 0.6:
            out.append(FamilyHistoryItem(relation=r.choice(["father", "mother"]), condition=r.choice(["MI", "colon cancer"]),
                                         age_at_onset=r.randint(45, 57), age_at_death=r.randint(50, 59), living=False))
        elif lvl == "Preferred Plus" and r.random() < 0.5:
            out.append(FamilyHistoryItem(relation=r.choice(["father", "brother"]), condition="CAD", age_at_onset=r.randint(52, 64), living=True))
        # irrelevant family noise (not counted conditions or old ages)
        if r.random() < 0.6:
            out.append(FamilyHistoryItem(relation=r.choice(["mother", "father"]), condition=r.choice(["type 2 diabetes", "Alzheimer's", "COPD", "hypertension", "MI"]),
                                         age_at_onset=r.randint(62, 80), age_at_death=r.choice([None, r.randint(75, 92)]), living=r.random() < 0.5))
        return out

    def condition(self, it):
        r = self.r
        key, var, params = it["key"], it["variant"], it["params"]
        e = IMP[key]
        details, years = {}, None
        if key == "cancer":
            t = params["type"]
            lo, hi = params["years_since_tx"]
            years = r1(r.uniform(lo + 0.05, min(hi, max(lo + 0.5, self.age - 20)) - 0.05))
            details = {"type": t, "years_since_tx": years}
            if t.startswith("prostate"):
                details["gleason"] = 6 if "surveillance" in t else (r.choice([6, 7]) if "le7" in t else r.choice([8, 9]))
                details["psa_undetectable"] = "surgery" in t
            stage = {"melanoma_in_situ": "0", "melanoma_1": "I", "melanoma_2": "II", "melanoma_3_4": "III", "breast_dcis": "0",
                     "breast_1": "I", "breast_2": "II", "breast_3": "III", "colon_1": "I", "colon_2": "II", "colon_3": "III",
                     "hodgkin_1_2": r.choice(["I", "II"]), "testicular_seminoma_1": "I", "thyroid": r.choice(["I", "II"])}.get(t)
            details["stage"] = stage
            if self.row.get("grey") == "GRY-6":
                details["stage_documented"] = False
            years_dx = years + r.uniform(0.2, 1.5)
            onset = self.ago(years_dx)
        elif key in ("cad",) and "age_at_event" in params:
            ab, yb = params["age_at_event"], params["years_since"]
            ylo, yhi = yb[0] + 0.1, min(yb[1], 15) - 0.1
            ys = r1(r.uniform(ylo, yhi))
            ae = int(min(ab[1], max(ab[0], self.age - ys)))
            ys = r1(min(max(self.age - ae, ylo), yhi))
            details = {"age_at_event": ae, "years_since": ys, "event": r.choice(["MI", "stent", "CABG", "stent"]),
                       "ef": r.randint(52, 65), "angina": False, "vessels": r.randint(1, 2), "ldl": r.randint(55, 110),
                       "abnormal_stress": False, "normal_stress_12mo": r.random() < 0.4, "smoker": self.row["ladder"] == "tobacco"}
            if r.random() < 0.15:
                mod = r.choice(["ef", "angina", "vessels"])
                details.update({"ef": r.randint(42, 49)} if mod == "ef" else {"angina": True} if mod == "angina" else {"vessels": 3})
                self.log.append(f"cad modifier {mod}")
            onset = self.ago(ys)
        elif key == "cad" and var == "recent_lt6mo":
            ys = r1(r.uniform(0.05, 0.45)); details = {"age_at_event": self.age, "years_since": ys, "event": "stent", "ef": r.randint(50, 62)}
            onset = self.ago(ys)
        elif key in ("diabetes_t2", "diabetes_t1"):
            a1 = params["a1c_avg"]
            a1c = r1(r.uniform(a1[0] + 0.05, min(a1[1], 12.5) - 0.05)) if a1[1] < 90 else r1(r.uniform(10.1, 12.5))
            dur = r1(r.uniform(0.5, min(15, self.age - 15)))
            details = {"a1c_avg": a1c, "a1c_available": True, "insulin": key == "diabetes_t1" or r.random() < 0.2,
                       "duration_years": dur, "age_at_dx": int(self.age - dur), "microalbuminuria": False, "neuropathy": False,
                       "retinopathy": False, "cad": False}
            if key == "diabetes_t2" and details["age_at_dx"] < 30:
                details["age_at_dx"] = 30; details["duration_years"] = r1(self.age - 30)
            if self.row.get("grey") == "GRY-5":
                details["a1c_available"] = False
            onset = self.ago(details["duration_years"])
        elif key == "hypertension":
            details = {"agents": params.get("agents", 1), "bp_band": params.get("bp_band")}
            onset = self.ago(r.uniform(1, min(20, self.age - 18)))
        elif key == "ckd":
            eg = params.get("egfr")
            lo, hi = (int(x) for x in eg.split("-")) if eg else (50, 59)
            details = {"egfr": r.randint(lo, hi)} if eg else {}
            if not eg:
                details = self.realize_profile(key, var)
            onset = self.ago(r.uniform(1, 10))
        elif key == "proteinuria":
            pr = params["urine_protein"]
            details = {"urine_protein": r.randint(*(int(x) for x in pr.split("-"))) if "-" in pr else r.randint(310, 600)}
            onset = self.ago(r.uniform(0.5, 5))
        elif key == "alcohol_use_disorder":
            yrs = {"abst_lt1": (0.2, 0.9), "abst_1_2": (1.05, 1.95), "abst_2_5": (2.05, 4.9), "abst_gt5": (5.1, 20), "relapse": (1.05, 4.9)}[var]
            details = {"abstinent_years": r1(r.uniform(*yrs)), "treatment": r.choice(["inpatient rehab", "IOP", "outpatient + AA"]),
                       "relapses": 1 if var == "relapse" else 0}
            onset = self.ago(details["abstinent_years"] + r.uniform(1, 8))
        elif key == "substance_use_hard":
            yrs = {"hard_lt5": (0.5, 4.8), "hard_5_10": (5.1, 9.8), "hard_gt10": (10.2, 25), "oud_maint_lt2": (0.3, 1.9), "oud_maint_ge2": (2.1, 8)}[var]
            details = {"substance": "opioids" if var.startswith("oud") else r.choice(["cocaine", "methamphetamine", "heroin", "prescription opioids"]),
                       "years_since_last_use" if var.startswith("hard") else "maintenance_years": r1(r.uniform(*yrs)),
                       "maintenance": var.startswith("oud")}
            onset = self.ago(r.uniform(*yrs) + r.uniform(1, 6))
        elif "profiles" in e:
            details = self.realize_profile(key, var)
            ys = details.get("years_since") or details.get("years_since_dx") or r1(r.uniform(0.5, min(20, self.age - 17)))
            onset = self.ago(ys)
        else:
            onset = self.ago(r.uniform(1, 10))
        details.pop("age", None)
        # status / severity
        out = it["outcome"]
        status = "in_workup" if var in ("cin3_pending",) else "controlled"
        if key in ("cancer",) and out == "postpone":
            status = "active"
        if key in ("hepatitis_c",) and details.get("svr"):
            status = "resolved"
        sev = "severe" if out in ("decline", "postpone") or it["debits"] >= 100 else "moderate" if it["debits"] > 0 else "mild"
        # meds
        meds = self.meds_for(key, details, onset)
        # disclosure
        disc = it["disclosure"]
        untrace = disc == "omitted_untraceable"
        if untrace:
            details["untraceable"] = True
            disc = "omitted"
        if key == "pregnancy":
            details.setdefault("weeks", r.randint(8, 30))
        spec = self.specialty_for(key)
        prov = []
        if not untrace:
            prov.append(self.provider(spec).provider_id if spec else self.provider("family medicine").provider_id)
        return Condition(condition_key=key, label=e["label"], onset=onset, status=status, severity=sev, details=details,
                         meds=meds if not untrace else [], treating_provider_ids=prov, disclosure=disc,
                         in_mib=(not untrace) and r.random() < 0.45)

    def meds_for(self, key, details, onset):
        r = self.r
        rx = IMP[key].get("rx", [])
        if not rx:
            return []
        picks = []
        if key == "hypertension":
            htn = [d for d in rx if d not in ("metoprolol", "spironolactone", "carvedilol")]
            picks = r.sample(htn, min(details.get("agents", 1), len(htn)))
        elif key in ("diabetes_t2",):
            picks = ["metformin"] + (["insulin glargine"] if details.get("insulin") else []) + \
                (r.sample(["glipizide", "sitagliptin", "empagliflozin", "semaglutide", "tirzepatide"], 1) if details.get("a1c_avg", 0) >= 7 else [])
        elif key == "diabetes_t1":
            picks = ["insulin glargine", r.choice(["insulin lispro", "insulin aspart"])]
        elif key == "cancer":
            t = details.get("type", "")
            if t.startswith("breast") and details.get("years_since_tx", 9) < 6:
                picks = [r.choice(["tamoxifen", "anastrozole", "letrozole"])]
            elif t.startswith("thyroid"):
                picks = ["levothyroxine"]
            elif t.startswith("prostate_ge8"):
                picks = ["leuprolide"]
        elif key == "hepatitis_c" and details.get("svr"):
            picks = [r.choice(["sofosbuvir-velpatasvir", "glecaprevir-pibrentasvir"])]
        elif key in ("cad",):
            picks = ["atorvastatin", "aspirin"] + (["clopidogrel"] if details.get("years_since", 5) < 1.5 else []) + \
                (["metoprolol"] if r.random() < 0.6 else [])
        elif key in ("asthma",) and not details.get("controller"):
            picks = ["albuterol"]
        elif r.random() < 0.85:
            picks = r.sample(rx, min(len(rx), r.choice([1, 1, 2])))
        out = []
        for d in picks:
            if d not in RX:
                continue
            st = onset + timedelta(days=r.randint(0, 120))
            st = min(st, self.app_date - timedelta(days=20))
            stop = None
            if key == "hepatitis_c" and details.get("svr"):
                stop = st + timedelta(days=84)
            out.append(MedUse(drug=d, dose=r.choice(RX[d][1]), start=st, stop=stop, indication=key))
        return out

    @staticmethod
    def specialty_for(key):
        ch = IMP[key]["chapter"]
        return {"CV": "cardiology", "CA": "oncology", "MH": "psychiatry", "NEU": "neurology", "GI": "gastroenterology",
                "REN": "nephrology", "RSP": "pulmonology", "IMM": "rheumatology", "END": "endocrinology", "DM": "endocrinology",
                "HEM": "hematology", "ALC": "addiction medicine", "DRG": "addiction medicine", "OBS": "obstetrics/gynecology",
                "GER": "family medicine", "MSK": "family medicine", "HTN": "family medicine", "MISC": "family medicine"}.get(ch)

    def benign(self, name):
        r = self.r
        drugs = IMP["benign_no_rating"]["members"][name]
        onset = self.ago(r.uniform(0.3, min(15, self.age - 16)))
        meds = [MedUse(drug=d, dose=r.choice(RX[d][1]), start=min(onset + timedelta(days=r.randint(0, 60)), self.app_date - timedelta(days=10)),
                       stop=None if r.random() < 0.6 else onset + timedelta(days=r.randint(10, 60)), indication=name)
                for d in r.sample(drugs, min(len(drugs), r.choice([1, 1, 2])))]
        return Condition(condition_key="benign_no_rating", label=name.replace("_", " "), onset=onset, status="controlled",
                         severity="mild", details={"member": name}, meds=meds,
                         treating_provider_ids=[self.provider("family medicine").provider_id], disclosure=r.choice(["honest", "honest", "omitted"]),
                         in_mib=r.random() < 0.1, irrelevant=True)

    def labs(self, conds, tc, hdl, ldl, trig):
        r = self.r
        L = {"tc": tc, "hdl": hdl, "ldl": ldl, "triglycerides": trig, "tc_hdl_ratio": round(tc / hdl, 1),
             "glucose_fasting": r.randint(78, 104), "a1c": r1(r.uniform(4.8, 5.6)), "ast": r.randint(14, 38), "alt": r.randint(12, 42),
             "ggt": r.randint(10, 55), "alk_phos": r.randint(40, 120), "bilirubin": r1(r.uniform(0.3, 1.2)), "albumin": r1(r.uniform(3.8, 4.9)),
             "creatinine": r1(r.uniform(0.7, 1.2)), "egfr": r.randint(70, 115) if self.age < 60 else r.randint(60, 95), "urine_protein": r.choice([0, 0, 10, 20]),
             "hemoglobin": r1(r.uniform(13.5, 16.5) if self.row["sex"] == "M" else r.uniform(12.3, 15.0)), "cdt": r1(r.uniform(0.8, 1.5)),
             "nt_probnp": r.randint(15, 110) if self.age < 75 else r.randint(60, 400), "cotinine_urine": self.cotinine,
             "hiv": 0, "cocaine": 0}
        if self.row["sex"] == "M" and self.age >= 40:
            L["psa"] = r1(r.uniform(0.3, 2.2))
        for c in conds:
            k, d = c.condition_key, c.details
            if k in ("diabetes_t2", "diabetes_t1"):
                L["a1c"] = r1(d["a1c_avg"] + r.uniform(-0.3, 0.3)); L["glucose_fasting"] = int(28.7 * L["a1c"] - 46.7 + r.randint(-10, 10))
            if k == "prediabetes":
                L["a1c"] = r1(r.uniform(5.7, d.get("a1c_avg") or 6.2)); L["glucose_fasting"] = r.randint(100, 124)
            if k == "ckd" and "egfr" in d:
                L["egfr"] = d["egfr"]; L["creatinine"] = r1(min(4.5, 90 / max(d["egfr"], 12)))
            if k == "proteinuria":
                L["urine_protein"] = d["urine_protein"]
            if k in ("hepatitis_c", "hepatitis_b", "fatty_liver") and not d.get("svr"):
                L["alt"] = r.randint(50, 130); L["ast"] = r.randint(42, 100)
            if k == "cardiomyopathy" or (k == "cad" and d.get("ef", 60) < 50):
                L["nt_probnp"] = r.randint(150, 800)
            if k == "hiv":
                L["hiv"] = 1
            if k == "substance_use_hard" and d.get("years_since_last_use", 9) < 1 and d.get("substance") == "cocaine":
                L["cocaine"] = 1
            if k == "cancer" and d.get("type", "").startswith("prostate"):
                L["psa"] = 0.05 if d.get("psa_undetectable") else r1(r.uniform(3, 9))
        nmv = {i["key"]: i["variant"] for i in self.row["items"] if i["kind"] == "nm"}
        if nmv.get("nm_alcohol") in ("dpw_22_35", "dpw_gt35", "cdt_high_denied"):
            L["ggt"] = r.randint(95, 200); L["cdt"] = r1(r.uniform(1.8, 3.4)); L["ast"] = r.randint(35, 70)
        return L

    # ------------------------------------------------------------------ assemble
    def make(self) -> Truth:
        row, r = self.row, self.r
        self.cessation_rx = None
        person = self.person()
        nm = {i["key"]: i for i in row["items"] if i["kind"] == "nm"}
        self.provider("family medicine", style=row["aps_styles"][0] if row["aps_styles"] else None)
        h, w = self.build(nm)
        conds = [self.condition(i) for i in row["items"] if i["kind"] == "med"]
        conds += [self.benign(b) for b in row["benign"]]
        statin = any(m.drug.endswith("statin") for c in conds for m in c.meds)
        sbp, dbp = self.bp(row["items"])
        tc, hdl, ldl, trig = self.lipids(nm, statin)
        tob = self.tobacco()
        # alcohol / drugs
        drinks = r.choice([0, 0, 1, 2, 3, 4, 6, 8, 10, 12])
        av = nm.get("nm_alcohol", {}).get("variant")
        drinks = {"dpw_15_21": r.randint(15, 21), "dpw_22_35": r.randint(22, 35), "dpw_gt35": r.randint(36, 60),
                  "cdt_high_denied": r.randint(25, 40)}.get(av, drinks)
        drug_use = []
        mj = nm.get("nm_marijuana", {}).get("variant")
        if mj:
            drug_use.append({"substance": "marijuana", "per_week": {"mj_le2": r.choice([1, 2]), "mj_3_7": r.randint(3, 7), "mj_daily": r.randint(10, 21)}[mj],
                             "form": r.choice(["smoked", "edible", "vaped"]), "disclosure": nm["nm_marijuana"]["disclosure"]})
        if any(c.condition_key == "alcohol_use_disorder" for c in conds):
            drinks = 0
        # avocations / aviation / travel
        avo, trav = [], []
        if "nm_avocation" in nm:
            v = nm["nm_avocation"]["variant"]
            det = {"scuba_deep": {"max_depth_ft": r.randint(101, 130), "dives_per_year": r.randint(20, 60)},
                   "scuba_cave": {"max_depth_ft": r.randint(131, 190), "cave": True}, "scuba_200": {"max_depth_ft": r.randint(205, 300)},
                   "scuba_rec": {"max_depth_ft": r.randint(40, 100), "dives_per_year": r.randint(5, 40), "certified": True},
                   "skydive": {"jumps_per_year": r.randint(5, 50)}, "skydive_heavy": {"jumps_per_year": r.randint(51, 300)},
                   "base": {"base_jumps": r.randint(5, 80)}, "climb_high": {"max_altitude_ft": r.randint(14100, 20000)},
                   "climb_extreme": {"max_altitude_ft": r.randint(20100, 25900), "technical": True},
                   "climb_8000": {"max_altitude_ft": r.randint(26100, 29000)}, "racing_amateur": {"events_per_year": r.randint(2, 10)},
                   "racing_pro": {"professional": True, "max_mph": r.randint(150, 210)}, "hang_glide": {"flights_per_year": r.randint(5, 25)},
                   "heli_ski": {"days_per_year": r.randint(2, 10)}, "rodeo": {"competitive": True}}[v]
            act = v.split("_")[0].replace("climb", "mountain_climbing").replace("skydive", "skydiving").replace("racing", "motor_racing") \
                .replace("hang", "hang_gliding").replace("heli", "heli_skiing").replace("base", "base_jumping")
            det["intends_to_stop"] = row.get("grey") == "GRY-9"
            avo.append(Avocation(activity=act, details=det, disclosure=nm["nm_avocation"]["disclosure"] if nm["nm_avocation"]["disclosure"] in ("honest", "omitted", "minimized", "misremembered") else "omitted"))
        if "nm_aviation" in nm:
            v = nm["nm_aviation"]["variant"]
            det = {"pilot_ifr": {"total_hours": r.randint(150, 3000), "hours_per_year": r.randint(20, 180), "ifr": True},
                   "pilot_noifr_heavy": {"total_hours": r.randint(200, 2000), "hours_per_year": r.randint(110, 250), "ifr": False},
                   "pilot_student": {"total_hours": r.randint(10, 95), "hours_per_year": r.randint(20, 80), "ifr": False},
                   "pilot_experimental": {"total_hours": r.randint(300, 2000), "aircraft": "homebuilt"},
                   "pilot_aerobatic": {"total_hours": r.randint(500, 4000), "aerobatic": True}}[v]
            avo.append(Avocation(activity="private_aviation", details=det, disclosure="honest"))
        if r.random() < 0.3 and not avo:
            avo.append(Avocation(activity=r.choice(["hiking", "recreational boating", "hunting", "marathon running", "martial arts", "skiing"]), details={}))
        if "nm_travel" in nm:
            v = nm["nm_travel"]["variant"]
            tier, wk = {"tierB_long": ("B", r.randint(14, 30)), "tierC_short": ("C", r.randint(1, 4)), "tierC_mid": ("C", r.randint(5, 13)),
                        "tierC_long": ("C", r.randint(14, 40)), "tierD": ("D", r.randint(1, 12))}[v]
            trav.append(Travel(country=r.choice(TIERS[tier]), weeks_per_year=wk, purpose=r.choice(["business", "family", "volunteer work", "consulting"])))
        elif r.random() < 0.25:
            trav.append(Travel(country=r.choice(TIERS["A"]), weeks_per_year=r.randint(1, 3), purpose="vacation"))
        prior = []
        if r.random() < 0.35:
            prior.append(PriorApplication(year=self.app_date.year - r.randint(1, 8), company=r.choice(["Northstar Life", "Pinecrest Mutual", "Atlas Assurance", "Harborview Life"]),
                                          outcome=r.choice(["issued Standard", "issued Preferred", "postponed", "declined", "issued Table 2", "not taken"])))
        riders = list(row["riders_requested"])
        existing = r.choice([0, 0, 0, 100000, 250000, 500000])
        truth = Truth(
            case_id=row["case_id"], seed=row["seed"], app_date=self.app_date, design=row, person=person,
            coverage=Coverage(face_amount=row["face"], product=row["product"], riders_requested=riders, existing_coverage=existing,
                              replacement=r.random() < 0.08, beneficiary_relation=r.choice(["spouse", "spouse", "children", "trust", "estate", "business partner" if "KPE" in riders else "spouse"])),
            height_in=h, weight_lb=w, bp_systolic=sbp, bp_diastolic=dbp, pulse=r.randint(54, 92),
            tobacco=tob, alcohol_drinks_per_week=drinks, alcohol_treatment=any(c.condition_key == "alcohol_use_disorder" for c in conds),
            drug_use=drug_use, conditions=conds, family_history=self.family(nm), mvr=self.mvr(nm), avocations=avo, travel=trav,
            prior_apps=prior, providers=self.providers, true_labs=self.labs(conds, tc, hdl, ldl, trig),
        )
        # case-level extras the evidence generator needs
        extra = {"log": self.log, "fin_ratio": round(self.fin_ratio, 3), "bmi": round(self.bmi, 1),
                 "foreign_country": self.foreign_country, "cessation_rx_quit": self.cessation_rx.isoformat() if self.cessation_rx else None}
        for k in ("nm_surgery", "nm_workup", "nm_weightloss", "nm_criminal", "nm_misrep"):
            if k in nm:
                extra[k] = nm[k]["variant"]
        if "nm_build" in nm and nm["nm_build"]["variant"] == "bariatric_recent":
            extra["bariatric"] = {"date": self.ago(r.uniform(0.4, 0.95)).isoformat(), "preop_weight": int(w * r.uniform(1.3, 1.6))}
        truth.design = {**row, "_extra": extra}
        return truth


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    rows = [json.loads(l) for l in (ROOT / "data/design/matrix.jsonl").read_text().splitlines()]
    if a.ids:
        want = set(a.ids.split(","))
        rows = [x for x in rows if x["case_id"] in want]
    if a.limit:
        rows = rows[: a.limit]
    out = ROOT / "data/truth"
    out.mkdir(parents=True, exist_ok=True)
    logs, errs, ncond = Counter(), [], Counter()
    for row in rows:
        try:
            t = TruthGen(row).make()
            Truth.model_validate_json(t.model_dump_json())
            (out / f"{row['case_id']}.json").write_text(t.model_dump_json(indent=1))
            for l in t.design["_extra"]["log"]:
                logs[l.split(" exactly")[0]] += 1
            ncond[len(t.conditions)] += 1
        except Exception as ex:  # noqa: BLE001
            errs.append(f"{row['case_id']}: {type(ex).__name__}: {ex}")
    print(f"truth: {len(rows) - len(errs)}/{len(rows)} ok; conditions/case {dict(sorted(ncond.items()))}")
    for e in errs[:15]:
        print("ERR", e)
    for k, v in logs.most_common(15):
        print(f"LOG {v:4d} {k}")


if __name__ == "__main__":
    main()
