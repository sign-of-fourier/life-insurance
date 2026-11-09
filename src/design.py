"""Phase 3: coverage design. Produces data/design/matrix.jsonl (+ matrix.csv summary) and qa/phase3_coverage.md.

Each row is a case *spec*: target outcome, demographics bands, chosen impairment options (catalog key + variant),
non-medical drivers, tobacco pattern, preferred-matrix placement, disclosure per item, grey-area scenario,
evidence path, persona, vendors. Phase 4 realizes a spec into truth + evidence. The target outcome is a goal;
the Phase 5 engine decides the real outcome from evidence (mismatches are tracked, not forced).

Run: python src/design.py [--n 1000] [--seed 20261109]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
IMP = yaml.safe_load((ROOT / "rules/impairments.yaml").read_text())
REQ = yaml.safe_load((ROOT / "rules/requirements.yaml").read_text())
VEND = yaml.safe_load((ROOT / "reference/vendors.yaml").read_text())
PERS = yaml.safe_load((ROOT / "reference/uw_personas.yaml").read_text())["personas"]
OCC = yaml.safe_load((ROOT / "reference/occupations.yaml").read_text())["occupations"]
TIERS = yaml.safe_load((ROOT / "reference/country_tiers.yaml").read_text())

PREF = ["Elite", "Preferred Plus", "Preferred", "Standard Plus", "Standard"]
ORDER = {c: i for i, c in enumerate(PREF)}
ORDER.update({"Preferred Tobacco": 2, "Standard Tobacco": 4})
AGE_BANDS = [(18, 30), (31, 40), (41, 50), (51, 60), (61, 70), (71, 80)]

# ---------------------------------------------------------------- target outcome quotas (sum = 1000 at n=1000)
TARGETS = [
    ("Elite", 45), ("Preferred Plus", 65), ("Preferred", 75), ("Standard Plus", 75), ("Standard", 85),
    ("Table 1-2", 80), ("Table 3-4", 60), ("Table 5-8", 55), ("Table 9-16", 30),
    ("Preferred Tobacco", 30), ("Standard Tobacco", 65), ("Table Tobacco 1-4", 35), ("Table Tobacco 5-16", 15),
    ("Postpone", 115), ("Decline", 170),
]
GREY_IDS = [f"GRY-{i}" for i in range(1, 13)]


# ---------------------------------------------------------------- option pool
def opt(key, variant, debits=0, outcome="rate", best=None, fe=None, age=(18, 80), sex=None, params=None, chapter=None, kind="med"):
    return dict(key=key, variant=variant, debits=debits, outcome=outcome, best=best, fe=fe, age=list(age), sex=sex,
                params=params or {}, chapter=chapter or IMP.get(key, {}).get("chapter", "NM"), kind=kind)


SEX_AGE = {  # demographic constraints by key or cancer type
    "pregnancy": ("F", (18, 45)), "gestational_dm": ("F", (20, 50)), "cervical_dysplasia": ("F", (21, 65)),
    "cognitive_impairment": (None, (66, 80)), "frailty": (None, (71, 80)), "adhd": (None, (18, 55)),
    "eating_disorder": (None, (18, 45)), "parkinsons": (None, (45, 80)), "brca_lynch": (None, (25, 65)),
}
CANCER_DEMO = {"breast": ("F", (30, 80)), "prostate": ("M", (45, 80)), "testicular": ("M", (18, 50))}


def build_pool():
    pool = []
    for key, e in IMP.items():
        if key == "benign_no_rating":
            continue
        sex, age = SEX_AGE.get(key, (None, (18, 80)))
        if "profiles" in e:
            for p in e["profiles"]:
                d = p.get("debits", 0)
                d = d if isinstance(d, int) else 0
                if "debits_per_item" in p:
                    d = p["debits_per_item"]
                out = p.get("outcome", "rate")
                out = "rate" if out == "md" else out
                a = age
                if key == "hiv" and p["id"] == "insurable":
                    a = (20, 60)
                if key == "parkinsons":
                    a = (40, 55) if p["id"] == "young_onset" else (55, 80)
                pool.append(opt(key, p["id"], d, out, p.get("best", e.get("best")), age=a, sex=sex, params=p.get("match", {})))
        if "grid" in e and key in ("cad", "diabetes_t2"):
            g = e["grid"]
            ab = g["bands_age"]
            cols = g.get("bands_years") or g.get("bands_a1c")
            for i, row in enumerate(g["values"]):
                for j, v in enumerate(row):
                    out, d = ("decline", 0) if v == "decline" else ("rate", v)
                    if key == "cad":   # age_at_event band i, years since band j -> current age >= event + years
                        lo = max(30, ab[i][0]) + int(cols[j][0])
                        hi = min(80, ab[i][1] + int(min(cols[j][1], 15)))
                        if lo > hi:
                            continue
                        pool.append(opt(key, f"ev{ab[i][0]}-{ab[i][1]}_y{cols[j][0]}-{cols[j][1]}", d, out, "Standard",
                                        age=(lo, hi), params={"age_at_event": ab[i], "years_since": cols[j]}))
                    else:
                        pool.append(opt(key, f"age{ab[i][0]}-{ab[i][1]}_a1c{cols[j][0]}-{cols[j][1]}", d, out, "Standard",
                                        age=(max(18, ab[i][0]), min(80, ab[i][1])), params={"a1c_avg": cols[j]}))
            if key == "cad":
                pool.append(opt(key, "recent_lt6mo", 0, "postpone", age=(35, 80), params={"years_since": [0, 0.49]}))
        if key == "diabetes_t1":
            for i, (lo, hi) in enumerate(IMP["diabetes_t2"]["grid"]["bands_age"]):
                for j, v in enumerate(IMP["diabetes_t2"]["grid"]["values"][i]):
                    a1c = IMP["diabetes_t2"]["grid"]["bands_a1c"][j]
                    if v == "decline" or (lo < 30 and a1c[0] >= 8.5):
                        pool.append(opt(key, f"age{lo}-{hi}_a1c{a1c[0]}", 0, "decline", age=(max(18, lo), min(80, hi)), params={"a1c_avg": a1c}))
                    else:
                        pool.append(opt(key, f"age{lo}-{hi}_a1c{a1c[0]}", v + 50, "rate", "Standard", age=(max(18, lo), min(80, hi)), params={"a1c_avg": a1c}))
        if key == "cancer":
            for t, rows in e["types"].items():
                fam = next((f for f in CANCER_DEMO if t.startswith(f)), None)
                sx, ag = CANCER_DEMO.get(fam, (None, (25, 80)))
                for r in rows:
                    lo, hi = r["years"]
                    out = r.get("outcome", "rate")
                    out = "rate" if out == "md" else out
                    d = r.get("debits", 0)
                    if "debits_by_age" in r:
                        d = r["debits_by_age"]["under60"]
                    pool.append(opt(key, f"{t}_y{lo}-{hi}", d if isinstance(d, int) else 0, out,
                                    r.get("best", "Standard") if t != "bcc_scc" else None, r.get("fe"), age=ag, sex=sx,
                                    params={"type": t, "years_since_tx": [lo, min(hi, 25)]}))
    # engine-driven medical keys
    for d, bp in [(0, "<=140/90"), (25, "141-150/91-95"), (50, "151-160/96-100"), (75, "161-170/101-105"), (100, "171-180/106-110")]:
        pool.append(opt("hypertension", f"bp_{d}", d, best="Preferred Plus" if d == 0 else None, age=(25, 80), params={"bp_band": bp, "agents": 1}))
    pool.append(opt("hypertension", "two_agents", 0, best="Preferred", age=(30, 80), params={"agents": 2}))
    pool.append(opt("hypertension", "resistant", 25, best="Standard", age=(35, 80), params={"agents": 3}))
    pool.append(opt("hypertension", "uncontrolled", 0, "postpone", age=(30, 80), params={"bp_band": ">180/110"}))
    for d, eg in [(25, "45-59"), (75, "30-44"), (150, "15-29")]:
        pool.append(opt("ckd", f"egfr_{eg}", d, age=(30 if d == 25 else 40, 59 if d == 25 else 80), params={"egfr": eg}))
    for d, pr in [(25, "31-100"), (50, "101-300"), (100, ">300")]:
        pool.append(opt("proteinuria", f"prot_{pr}", d, age=(25, 80), params={"urine_protein": pr}))
    for v, d, out, best in [("abst_lt1", 0, "postpone", None), ("abst_1_2", 75, "rate", None), ("abst_2_5", 25, "rate", None),
                            ("abst_gt5", 0, "rate", "Preferred"), ("relapse", 125, "rate", None)]:
        pool.append(opt("alcohol_use_disorder", v, d, out, best, age=(25, 80)))
    for v, d, out, best in [("hard_lt5", 0, "decline", None), ("hard_5_10", 50, "rate", None), ("hard_gt10", 0, "rate", "Standard Plus"),
                            ("oud_maint_lt2", 0, "decline", None), ("oud_maint_ge2", 100, "rate", None)]:
        pool.append(opt("substance_use_hard", v, d, out, best, age=(22, 75)))
    # non-medical pseudo-impairments
    NM = lambda *a, **k: opt(*a, kind="nm", **k)  # noqa: E731
    for d in (25, 50, 75, 100, 150, 200, 250):
        pool.append(NM("nm_build", f"over_{d}", d, chapter="BLD"))
    pool += [NM("nm_build", "over_decline", 0, "decline", chapter="BLD"),
             NM("nm_build", "under_25", 25, chapter="BLD"), NM("nm_build", "under_50", 50, chapter="BLD"),
             NM("nm_build", "under_postpone", 0, "postpone", chapter="BLD"),
             NM("nm_build", "bariatric_recent", 50, chapter="BLD", age=(25, 65))]
    for d in (25, 50, 75):
        pool.append(NM("nm_lipids", f"lip_{d}", d, chapter="LIP"))
    pool += [NM("nm_lipids", "hdl_low", 15, chapter="LIP"), NM("nm_lipids", "trig_high", 25, chapter="LIP")]
    pool += [NM("nm_mvr", "minor4", 25, chapter="MVR"), NM("nm_mvr", "minor5_6", 50, chapter="MVR"),
             NM("nm_mvr", "minor7", 0, "decline", chapter="MVR"), NM("nm_mvr", "major1", 25, chapter="MVR"),
             NM("nm_mvr", "major2", 75, chapter="MVR"), NM("nm_mvr", "major3", 0, "decline", chapter="MVR"),
             NM("nm_mvr", "dui_1_2y", 75, best="Standard", chapter="MVR"), NM("nm_mvr", "dui_2_5y", 25, best="Standard Plus", chapter="MVR"),
             NM("nm_mvr", "dui_5_10y", 0, best="Preferred", chapter="MVR"), NM("nm_mvr", "dui_lt1y", 0, "postpone", chapter="MVR"),
             NM("nm_mvr", "dui_two_5y", 0, "decline", chapter="MVR")]
    pool += [NM("nm_alcohol", "dpw_15_21", 25, best="Standard Plus", chapter="ALC"), NM("nm_alcohol", "dpw_22_35", 50, best="Standard", chapter="ALC"),
             NM("nm_alcohol", "dpw_gt35", 100, chapter="ALC"), NM("nm_alcohol", "cdt_high_denied", 50, best="Standard", chapter="ALC")]
    pool += [NM("nm_marijuana", "mj_3_7", 0, best="Standard Plus", chapter="DRG"), NM("nm_marijuana", "mj_daily", 25, best="Standard", chapter="DRG"),
             NM("nm_marijuana", "mj_le2", 0, best="Preferred Plus", chapter="DRG")]
    for v, fe, out in [("scuba_deep", 2.5, "rate"), ("scuba_cave", 5.0, "rate"), ("scuba_200", 0, "decline"), ("skydive", 2.5, "rate"),
                       ("skydive_heavy", 5.0, "rate"), ("base", 0, "decline"), ("climb_high", 3.0, "rate"), ("climb_extreme", 7.5, "rate"),
                       ("climb_8000", 0, "decline"), ("racing_amateur", 2.5, "rate"), ("racing_pro", 5.0, "rate"), ("hang_glide", 2.5, "rate"),
                       ("heli_ski", 2.5, "rate"), ("rodeo", 5.0, "rate"), ("scuba_rec", 0, "rate")]:
        pool.append(NM("nm_avocation", v, 0, out, fe={"per_k": fe, "years": None} if fe else None, chapter="AVO", age=(18, 70)))
    for v, fe in [("pilot_ifr", 0), ("pilot_noifr_heavy", 2.5), ("pilot_student", 2.5), ("pilot_experimental", 5.0), ("pilot_aerobatic", 7.5)]:
        pool.append(NM("nm_aviation", v, 0, fe={"per_k": fe, "years": 2 if v == "pilot_student" else None} if fe else None, chapter="AVI", age=(18, 75)))
    pool += [NM("nm_travel", "tierB_long", 0, best="Preferred", chapter="TRV"), NM("nm_travel", "tierC_short", 0, best="Preferred", chapter="TRV"),
             NM("nm_travel", "tierC_mid", 0, fe={"per_k": 2.5, "years": None}, chapter="TRV"),
             NM("nm_travel", "tierC_long", 0, fe={"per_k": 5.0, "years": None}, chapter="TRV"),
             NM("nm_travel", "tierD", 0, "decline", chapter="TRV")]
    pool += [NM("nm_occupation", "occ_4a", 0, fe={"per_k": 2.5, "years": None}, chapter="OCC", age=(18, 65)),
             NM("nm_occupation", "occ_4a_hi", 0, fe={"per_k": 5.0, "years": None}, chapter="OCC", age=(18, 65)),
             NM("nm_occupation", "occ_5a", 0, fe={"per_k": 7.5, "years": None}, chapter="OCC", age=(20, 55)),
             NM("nm_occupation", "deploying", 0, "postpone", chapter="OCC", age=(19, 45))]
    pool += [NM("nm_family", "fh_two_cvd", 25, chapter="FH", age=(18, 59))]
    pool += [NM("nm_financial", "overins_counter", 0, chapter="FIN"), NM("nm_financial", "overins_decline", 0, "decline", chapter="FIN")]
    pool += [NM("nm_foreign", "visa_ineligible", 0, "decline", chapter="FN", age=(18, 50)),
             NM("nm_foreign", "visa_eligible", 0, best="Preferred", chapter="FN", age=(22, 60)),
             NM("nm_foreign", "citizen_abroad_C", 0, best="Standard", chapter="FN")]
    pool += [NM("nm_criminal", "pending_felony", 0, "postpone", chapter="CLS", age=(18, 65)),
             NM("nm_criminal", "released_lt2", 0, "decline", chapter="CLS", age=(20, 65))]
    pool += [NM("nm_misrep", "multi_misrep", 0, "decline", chapter="GEN")]
    pool += [NM("nm_surgery", "surgery_scheduled", 0, "postpone", chapter="CLS"), NM("nm_workup", "pending_workup", 0, "postpone", chapter="CLS"),
             NM("nm_weightloss", "unexplained_loss", 0, "postpone", chapter="CLS", age=(30, 80))]
    for o in pool:
        o["id"] = f"{o['key']}:{o['variant']}"
    return pool


# ---------------------------------------------------------------- helpers
def band_of_age(a):
    return next(i for i, (lo, hi) in enumerate(AGE_BANDS) if lo <= a <= hi)


def table_range(target):
    """debit range for a table target label."""
    if "Table" not in target:
        return None
    lo_t, hi_t = (int(x) for x in target.split()[-1].split("-"))
    return 25 * lo_t + 1, 25 * hi_t + 25


def requirements_for(age, face):
    ai = next(i for i, (lo, hi) in enumerate(REQ["age_bands"]) if lo <= age <= hi)
    fi = next(i for i, (lo, hi) in enumerate(REQ["amount_bands"]) if face >= lo and (hi is None or face <= hi))
    return REQ["grid"][ai][fi], fi


FACE_BANDS = [100000, 150000, 250000, 300000, 500000, 750000, 1000000, 1500000, 2000000, 3000000, 5000000, 7500000, 12000000]


class Designer:
    def __init__(self, n, seed):
        self.n, self.rng = n, random.Random(seed)
        self.pool = build_pool()
        self.use = Counter()
        self.kuse = Counter()
        self.guse = Counter()
        self.benign = [(k, drugs) for k, drugs in IMP["benign_no_rating"]["members"].items()]

    def pick(self, cands, k=1):
        """inverse-usage weighted choice -> pushes coverage of rare options."""
        if not cands:
            return None
        bykey = defaultdict(lambda: defaultdict(list))
        for c in cands:
            bykey[c["key"]][self.group(c)].append(c)
        keys = list(bykey)
        ng = lambda k: len({self.group(o) for o in self.pool if o["key"] == k})  # noqa: E731
        kw = [math.sqrt(ng(k)) / (1 + self.kuse[k]) ** 2 for k in keys]      # level 1: key
        k = self.rng.choices(keys, weights=kw, k=1)[0]
        groups = list(bykey[k])
        gw = [1.0 / (1 + self.guse[g]) ** 2 for g in groups]                   # level 2: group
        g = self.rng.choices(groups, weights=gw, k=1)[0]
        vs = bykey[k][g]
        w = [1.0 / (1 + self.use[c["id"]]) ** 1.5 for c in vs]               # level 3: variant
        c = self.rng.choices(vs, weights=w, k=1)[0]
        self.use[c["id"]] += 1
        self.kuse[k] += 1
        self.guse[g] += 1
        return c

    @staticmethod
    def group(o):
        """balancing group: cancer by type, grid keys by age row, else key."""
        if o["key"] == "cancer":
            return "cancer/" + o["params"]["type"]
        if o["key"] in ("cad", "diabetes_t2", "diabetes_t1"):
            return o["key"] + "/" + o["variant"].split("_")[0]
        return o["key"]

    def fits(self, o, age, sex):
        return o["age"][0] <= age <= o["age"][1] and (o["sex"] in (None, sex))

    def scale(self, target_counts):
        tot = sum(c for _, c in target_counts)
        out = [(t, max(1, round(c * self.n / tot))) for t, c in target_counts]
        diff = self.n - sum(c for _, c in out)
        out[-1] = (out[-1][0], out[-1][1] + diff)
        return out

    # -------------------------------------------------------- main per-row construction
    def make_row(self, i, target):
        r = self.rng
        ladder = "tobacco" if "Tobacco" in target else "non_tobacco"
        if target in ("Postpone", "Decline") and self.rng.random() < 0.22:
            ladder = "tobacco"   # smokers get postponed/declined too
        # age: Elite <=65; tables 9+ must be <=70 (CLS-3.4); otherwise spread across bands
        lo, hi = 18, 80
        if target == "Elite":
            hi = 65
        if target == "Preferred Plus":
            hi = 75
        if target in ("Table 9-16", "Table Tobacco 5-16"):
            hi = 70
        band = r.choice([b for b in AGE_BANDS if b[1] >= lo and b[0] <= hi])
        age = r.randint(max(lo, band[0]), min(hi, band[1]))
        sex = r.choice("MF")
        items, notes = [], []
        tr = table_range(target)
        cands = lambda pred: [o for o in self.pool if self.fits(o, age, sex) and pred(o)]  # noqa: E731

        if target in PREF + ["Preferred Tobacco", "Standard Tobacco"]:
            tgt_order = ORDER[target]
            # 0-debit conditions whose cap allows target (best None = no cap)
            ok_opt = cands(lambda o: o["outcome"] == "rate" and o["debits"] == 0 and o["fe"] is None and o["kind"] == "med"
                           and (o["best"] is None or ORDER.get(o["best"], 9) <= tgt_order))
            n_cond = {"Elite": 0, "Preferred Plus": r.choice([0, 0, 1]), "Preferred": r.choice([0, 1, 1]),
                      "Standard Plus": r.choice([0, 1, 1, 2]), "Standard": r.choice([0, 1, 2])}.get(
                target, r.choice([0, 1]))
            if target == "Elite":
                ok_opt = []
            # ensure the binding cap equals target for some rows (so the class is explained by a cap)
            exact = [o for o in ok_opt if o["best"] and ORDER.get(o["best"]) == tgt_order]
            if exact and n_cond and r.random() < 0.6:
                items.append(self.pick(exact)); n_cond -= 1
            for _ in range(n_cond):
                c = self.pick([o for o in ok_opt if o not in items])
                if c:
                    items.append(c)
            if target == "Standard" and r.random() < 0.4:   # small debits path (+1..+25)
                c = self.pick(cands(lambda o: o["outcome"] == "rate" and 1 <= o["debits"] <= 25 and o["fe"] is None))
                if c:
                    items.append(c)
            if target in ("Preferred", "Standard Plus", "Standard") and r.random() < 0.15:   # non-medical cap
                c = self.pick(cands(lambda o: o["kind"] == "nm" and o["debits"] == 0 and o["outcome"] == "rate" and o["best"]
                                    and ORDER.get(o["best"], 9) == tgt_order))
                if c:
                    items.append(c)
            if target in ("Preferred", "Standard Plus") and r.random() < 0.15:   # small FE allowed (AVO-1.4)
                c = self.pick(cands(lambda o: o["fe"] and o["fe"]["per_k"] <= 2.5 and o["outcome"] == "rate" and o["kind"] == "nm"))
                if c:
                    items.append(c)
        elif tr:
            lo_d, hi_d = tr
            goal = r.randint(lo_d, hi_d)
            total, tries = 0, 0
            while total < lo_d and tries < 30:
                tries += 1
                need_max = hi_d - total
                c = self.pick(cands(lambda o: o["outcome"] == "rate" and 0 < o["debits"] <= need_max and o not in items
                                    and o["key"] not in {x["key"] for x in items}))
                if not c:
                    break
                if total + c["debits"] > hi_d:
                    continue
                items.append(c); total += c["debits"]
                if total >= goal:
                    break
            if total < lo_d:
                notes.append(f"table target short: {total} < {lo_d}")
            if r.random() < 0.15:
                c = self.pick(cands(lambda o: o["fe"] and o["outcome"] == "rate"))
                if c and c["key"] not in {x["key"] for x in items}:
                    items.append(c)
        elif target == "Postpone":
            items.append(self.pick(cands(lambda o: o["outcome"] == "postpone")))
            if r.random() < 0.4:
                c = self.pick(cands(lambda o: o["outcome"] == "rate" and o["debits"] <= 75 and o["key"] != items[0]["key"]))
                if c:
                    items.append(c)
        elif target == "Decline":
            route = r.random()
            if route < 0.7:
                items.append(self.pick(cands(lambda o: o["outcome"] == "decline")))
            else:   # accumulate > +425 (or > T8 equivalent at 71+)
                limit = 225 if age >= 71 else 425
                total, tries = 0, 0
                while total <= limit and tries < 40:
                    tries += 1
                    c = self.pick(cands(lambda o: o["outcome"] == "rate" and o["debits"] >= 50 and o["key"] not in {x["key"] for x in items}))
                    if not c:
                        break
                    items.append(c); total += c["debits"]
                if total <= limit:
                    notes.append(f"decline-by-debits short: {total}")
            if r.random() < 0.3:
                c = self.pick(cands(lambda o: o["outcome"] == "rate" and o["debits"] <= 50 and o["key"] not in {x["key"] for x in items}))
                if c:
                    items.append(c)
        items = [x for x in items if x]

        # ---- tobacco pattern
        if ladder == "tobacco":
            if target == "Preferred Tobacco":
                tob = r.choice(["vape", "chew", "pipe", "nrt", "cigars_cot_pos"])
            else:
                tob = r.choice(["cig_current", "cig_current", "cig_quit_lt12", "vape", "chew", "cessation_rx_only", "cig_current_heavy"])
        else:
            quit_by_target = {"Elite": ["never", "never", "quit_10plus"], "Preferred Plus": ["never", "quit_5_10", "quit_10plus"],
                              "Preferred": ["never", "never", "quit_3_5", "cigars_cot_neg", "quit_5_10"],
                              "Standard Plus": ["never", "quit_2_3", "quit_3_5"], "Standard": ["never", "quit_1_2", "quit_2_3"]}
            if target in quit_by_target:
                tob = r.choice(quit_by_target[target])
            else:
                tob = r.choices(["never", "quit_1_2", "quit_2_3", "quit_3_5", "quit_5_10", "quit_10plus", "cigars_cot_neg"],
                                [0.5, 0.1, 0.07, 0.08, 0.08, 0.1, 0.07])[0]

        # ---- preferred matrix placement (only meaningful when net <= 0)
        matrix = {"base": target if target in PREF else ("Preferred" if target == "Preferred Tobacco" else "Standard"), "fails": []}
        rows = ["build", "bp", "lipids", "family_history", "mvr"]
        if target == "Standard Plus":
            matrix["base"] = "Preferred"
            for row in r.sample(rows, r.choice([1, 2])):
                matrix["fails"].append([row, "Standard Plus"])
        elif target == "Standard" and not any(x["debits"] for x in items):
            matrix["base"] = "Preferred"
            if r.random() < 0.5:
                matrix["fails"] = [[row, "Standard Plus"] for row in r.sample(rows, 3)]   # >=3 rows fail Preferred (CLS-5.2)
            else:
                matrix["fails"] = [[r.choice(rows), "Standard"]]                           # one row fails SP (CLS-5.3)

        # ---- disclosure per item (+ tobacco)
        disc = {}
        for x in items:
            if x["kind"] == "nm" and x["key"] in ("nm_financial", "nm_foreign", "nm_misrep"):
                disc[x["id"]] = "na"
                continue
            disc[x["id"]] = r.choices(["honest", "omitted", "minimized", "misremembered", "omitted_untraceable"],
                                      [0.56, 0.2, 0.1, 0.11, 0.03])[0]
        tob_disc = "na" if tob == "never" else r.choices(["honest", "omitted", "minimized"], [0.65, 0.2, 0.15])[0]

        # ---- distractors (benign, irrelevant)
        n_ben = r.choices([0, 1, 2, 3, 4], [0.15, 0.3, 0.3, 0.15, 0.1])[0]
        benign = r.sample([k for k, _ in self.benign if self._benign_ok(k, age, sex)], n_ben)

        # ---- face amount (requirements / path / complexity are derived in derive())
        ratable = [x for x in items if x["kind"] == "med" and (x["debits"] >= 1 or x["outcome"] != "rate" or x["best"])]
        if r.random() < 0.3 and age <= 50 and not ratable:
            face = r.choice([100000, 150000, 250000, 500000])     # accel-eligible
        else:
            face = r.choice(FACE_BANDS[: 12 if age < 66 else 9])
        if target == "Elite" and face < 250000:
            face = r.choice([250000, 500000, 1000000])
        foreign = any(x["key"] == "nm_foreign" for x in items) or r.random() < 0.06
        grey = r.choice(GREY_IDS) if r.random() < 0.15 else None
        return dict(
            case_id=f"C{i:04d}", seed=r.randrange(1 << 30), target=target, ladder=ladder, age=age, sex=sex, face=face,
            product=r.choice(["Term 10", "Term 20", "Term 20", "Term 30", "UL", "GUL"] if age <= 50 else ["Term 10", "Term 20", "UL", "GUL"]),
            items=[{k: x[k] for k in ("id", "key", "variant", "chapter", "kind", "debits", "outcome", "best", "fe", "params")} | {"disclosure": disc.get(x["id"], "na")}
                   for x in items],
            tobacco=tob, tobacco_disclosure=tob_disc, matrix=matrix, benign=benign, grey=grey,
            foreign=foreign,
            legacy_lab=r.random() < 0.10, notes=notes,
        )

    def derive(self, row):
        """requirements grid, # APS, evidence path, complexity - recomputed after any item change."""
        r = self.rng
        items = row["items"]
        ratable = [x for x in items if x["kind"] == "med" and (x["debits"] >= 1 or x["outcome"] != "rate" or x["best"])]
        disc = [x["disclosure"] for x in items]
        grid, _ = requirements_for(row["age"], row["face"])
        accel = grid == ["ACCEL"]
        aps_needed = any(x["debits"] >= 50 or x["outcome"] != "rate" for x in ratable) or \
            any(x["disclosure"] in ("omitted", "minimized") for x in ratable) or "APS" in grid
        n_aps = 0
        if aps_needed or (ratable and r.random() < 0.5):
            n_aps = 1 + (len(ratable) >= 2 and r.random() < 0.6) + (len(ratable) >= 3 and r.random() < 0.4)
        accel_breaks = accel and (ratable or row["foreign"] or row["tobacco_disclosure"] in ("omitted", "minimized") or n_aps)
        path = ("accel" if accel and not accel_breaks else "accel_to_fluids" if accel_breaks else "fluids") + \
            ("" if n_aps == 0 else "+aps" if n_aps == 1 else f"+aps{n_aps}")
        nonhonest = sum(d not in ("honest", "na") for d in disc)
        complexity = ("grey" if row["grey"] else
                      "complex" if len(ratable) >= 3 or n_aps >= 2 or nonhonest >= 2 else
                      "simple" if len(ratable) <= 1 and nonhonest == 0 and n_aps <= 1 and len(items) <= 2 else
                      "moderate")
        row.update(requirements_grid=grid, n_aps=n_aps, evidence_path=path, complexity=complexity)

    def _benign_ok(self, k, age, sex):
        if k in ("bph", "erectile_dysfunction") and (sex != "M" or age < 40):
            return False
        if k == "contraception" and (sex != "F" or age > 50):
            return False
        return True

    def assign_balanced(self, rows):
        """personas, vendors, riders, app form, aps styles: balanced shuffles."""
        r = self.rng

        def cycle(values, n):
            out = []
            while len(out) < n:
                v = list(values); r.shuffle(v); out += v
            return out[:n]
        n = len(rows)
        personas = cycle(list(PERS), n)
        rxv = cycle(list(VEND["rx_vendors"]), n)
        mibv = cycle(list(VEND["mib_layouts"]), n)
        mvrv = cycle(list(VEND["mvr_layouts"]), n)
        appv = cycle(list(VEND["app_forms"]), n)
        pmv = cycle(list(VEND["paramed_vendors"]), n)
        labv = cycle(["MIL", "APX", "MIL", "APX", "NGL"], n)
        styles = [s for s in VEND["aps_styles"] if s != "foreign_translated"]
        aps_cycle = cycle(styles * 50, sum(x["n_aps"] for x in rows) + 10)
        riders_all = ["WP", "WMD", "ADB", "CTR", "GIO", "CIA", "XCR", "OIR", "ROP-T", "KPE", "LTA"]
        k = 0
        for j, row in enumerate(rows):
            row["persona"] = personas[j]
            row["vendors"] = {"rx": rxv[j], "mib": mibv[j], "mvr": mvrv[j], "app": appv[j], "paramed": pmv[j],
                              "lab": "NGL" if row["foreign"] else labv[j]}
            if row["vendors"]["lab"] == "NGL" and not row["foreign"]:
                row["vendors"]["lab"] = "MIL"
            st = []
            for _ in range(row["n_aps"]):
                st.append("foreign_translated" if row["foreign"] and not st else aps_cycle[k]); k += 1
            row["aps_styles"] = st
            nr = r.choices([0, 1, 2, 3], [0.25, 0.35, 0.25, 0.15])[0]
            pool = [x for x in riders_all if not (x in ("WMD", "LTA") and row["product"] not in ("UL", "GUL"))
                    and not (x == "ROP-T" and row["product"] not in ("Term 20", "Term 30"))
                    and not (x == "WP" and row["product"] in ("UL", "GUL"))]
            row["riders_requested"] = sorted(r.sample(pool, min(nr, len(pool))))

    def run(self):
        targets = self.scale(TARGETS)
        plan = [t for t, c in targets for _ in range(c)]
        self.rng.shuffle(plan)
        rows = [self.make_row(i + 1, t) for i, t in enumerate(plan)]
        # top up grey-area coverage: every GRY id >= max(4, n*0.008)
        need = max(4, int(self.n * 0.008))
        gc = Counter(x["grey"] for x in rows if x["grey"])
        free = [x for x in rows if not x["grey"]]
        self.rng.shuffle(free)
        for g in GREY_IDS:
            while gc[g] < need and free:
                x = free.pop(); x["grey"] = g; gc[g] += 1
        self.top_up_keys(rows)
        for x in rows:
            self.derive(x)
        self.assign_balanced(rows)
        return rows

    def _target_for(self, o):
        if o["outcome"] == "decline":
            return "Decline"
        if o["outcome"] == "postpone":
            return "Postpone"
        if o["debits"] > 25:
            t = min(16, math.ceil((o["debits"] - 25) / 25))
            return f"Table {t}-{t}"
        if o["debits"] > 0:
            return "Standard"
        return o["best"] if o["best"] in PREF else "Standard"

    def _inject(self, o, rows, keyc, minimum):
        """Replace one compatible row's items with option o. Returns True on success."""
        r = self.rng
        tgt = self._target_for(o)
        fam = tgt.split()[0]
        base = [x for x in rows if x["target"].split()[0] == fam and not x.get("topped") and x["ladder"] == "non_tobacco"
                and len(x["items"]) <= 2 and not any(keyc[i["key"]] - 1 < minimum for i in x["items"])
                and all(self.row_use[i["id"]] > 1 for i in x["items"])]
        if not base:
            return False
        age_hi = o["age"][1]
        if fam == "Table" and int(tgt.split()[-1].split("-")[0]) > 8:
            age_hi = min(age_hi, 70)          # CLS-3.4: no tables > 8 at 71+
            if age_hi < o["age"][0]:
                return False
        fit = [x for x in base if o["age"][0] <= x["age"] <= age_hi and o["sex"] in (None, x["sex"])]
        x = r.choice(fit or base)
        if not fit:
            x["age"] = r.randint(o["age"][0], age_hi)
            if o["sex"]:
                x["sex"] = o["sex"]
        for it in x["items"]:
            keyc[it["key"]] -= 1
            self.row_use[it["id"]] -= 1
        x["items"] = [{k3: o[k3] for k3 in ("id", "key", "variant", "chapter", "kind", "debits", "outcome", "best", "fe", "params")}
                      | {"disclosure": r.choices(["honest", "omitted", "minimized"], [0.6, 0.25, 0.15])[0]}]
        x["target"] = tgt if fam != "Table" else f"Table {self._table_band(tgt)}"
        x["topped"] = True
        x["notes"].append(f"top-up {o['id']}")
        self.use[o["id"]] += 1
        self.row_use[o["id"]] += 1
        keyc[o["key"]] += 1
        return True

    @staticmethod
    def _table_band(tgt):
        t = int(tgt.split()[-1].split("-")[0])
        return "1-2" if t <= 2 else "3-4" if t <= 4 else "5-8" if t <= 8 else "9-16"

    def top_up_keys(self, rows, minimum=6):
        """Floors: every catalog key >= `minimum` cases, then every option (variant) >= 1 case."""
        keyc = Counter(i["key"] for r in rows for i in r["items"])
        self.row_use = Counter(i["id"] for r in rows for i in r["items"])
        for key in sorted({o["key"] for o in self.pool}):
            opts = [o for o in self.pool if o["key"] == key]
            tries = 0
            while keyc[key] < minimum and tries < 50:
                tries += 1
                self._inject(min(opts, key=lambda x: self.use[x["id"]]), rows, keyc, minimum)
        for o in self.pool:
            if not self.row_use[o["id"]]:
                self._inject(o, rows, keyc, minimum)

def report(rows, pool, path):
    L = [f"# Phase 3 coverage report ({len(rows)} cases)", ""]

    def tab(title, counter, total=None, sort=True):
        L.extend([f"## {title}", "", "| value | n | % |", "|---|---|---|"])
        items = sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0]))) if sort else counter.items()
        for k, v in items:
            L.append(f"| {k} | {v} | {100 * v / (total or len(rows)):.1f} |")
        L.append("")
    tab("Target outcome", Counter(r["target"] for r in rows))
    tab("Complexity", Counter(r["complexity"] for r in rows))
    tab("Evidence path", Counter(r["evidence_path"] for r in rows))
    tab("Age band", Counter(f"{AGE_BANDS[band_of_age(r['age'])]}" for r in rows))
    tab("Sex", Counter(r["sex"] for r in rows))
    tab("Face", Counter(r["face"] for r in rows))
    tab("Tobacco pattern", Counter(r["tobacco"] for r in rows))
    disc = Counter(i["disclosure"] for r in rows for i in r["items"])
    tab("Disclosure (per item)", disc, total=sum(disc.values()))
    tab("Cases with >=1 non-honest item", Counter(any(i["disclosure"] not in ("honest", "na") for i in r["items"]) for r in rows))
    tab("Grey-area scenario", Counter(r["grey"] or "-" for r in rows))
    tab("Persona", Counter(r["persona"] for r in rows))
    for v in ("lab", "rx", "mib", "mvr", "app", "paramed"):
        tab(f"Vendor: {v}", Counter(r["vendors"][v] for r in rows))
    tab("APS styles (per doc)", Counter(s for r in rows for s in r["aps_styles"]), total=sum(len(r["aps_styles"]) for r in rows))
    tab("# rated items per case", Counter(len(r["items"]) for r in rows))
    tab("# benign distractors per case", Counter(len(r["benign"]) for r in rows))
    tab("Riders requested", Counter(x for r in rows for x in r["riders_requested"]), total=len(rows))
    # catalog coverage
    keyc = Counter(i["key"] for r in rows for i in r["items"])
    allkeys = sorted({o["key"] for o in pool})
    low = {k: keyc[k] for k in allkeys if keyc[k] < 5}
    L += ["## Catalog key coverage", "", f"{len([k for k in allkeys if keyc[k]])}/{len(allkeys)} keys used; "
          f"min {min(keyc[k] for k in allkeys)}, median {sorted(keyc[k] for k in allkeys)[len(allkeys)//2]}, max {max(keyc.values())}.", ""]
    L += ["Keys with < 5 cases: " + (", ".join(f"{k} ({v})" for k, v in low.items()) or "none"), ""]
    optc = Counter(i["id"] for r in rows for i in r["items"])
    L += [f"Options (key:variant) used: {len(optc)}/{len(pool)} ({100*len(optc)/len(pool):.0f}%).", ""]
    unused = [o["id"] for o in pool if o["id"] not in optc]
    L += ["Unused options: " + (", ".join(unused[:80]) + (" ..." if len(unused) > 80 else "")), ""]
    # chapter x target
    L += ["## Chapter x target (counts of items)", ""]
    tg = [t for t, _ in TARGETS]
    chs = sorted({i["chapter"] for r in rows for i in r["items"]})
    L.append("| chapter | " + " | ".join(t.replace("Tobacco", "Tob") for t in tg) + " |")
    L.append("|---" * (len(tg) + 1) + "|")
    ct = Counter((i["chapter"], r["target"]) for r in rows for i in r["items"])
    for c in chs:
        L.append(f"| {c} | " + " | ".join(str(ct[(c, t)] or "") for t in tg) + " |")
    L.append("")
    # pairwise coverage on key dims
    dims = {"age_band": lambda r: band_of_age(r["age"]), "sex": lambda r: r["sex"], "target": lambda r: r["target"],
            "complexity": lambda r: r["complexity"], "persona": lambda r: r["persona"], "path": lambda r: r["evidence_path"].split("+")[0]}
    L += ["## Pairwise coverage (key dims)", "", "| pair | combos seen | possible | % |", "|---|---|---|---|"]
    names = list(dims)
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            fa, fb = dims[names[a]], dims[names[b]]
            va, vb = {fa(r) for r in rows}, {fb(r) for r in rows}
            seen = {(fa(r), fb(r)) for r in rows}
            L.append(f"| {names[a]} x {names[b]} | {len(seen)} | {len(va)*len(vb)} | {100*len(seen)/(len(va)*len(vb)):.0f} |")
    notes = [n for r in rows for n in r["notes"]]
    L += ["", f"## Design notes ({len(notes)})", "", *[f"- {n}" for n in Counter(notes)]]
    path.write_text("\n".join(L) + "\n")


def validate_rows(rows):
    """Structural sanity of the design (not outcome correctness - that is Phase 5)."""
    errs = []
    for r in rows:
        cid = r["case_id"]
        for it in r["items"]:
            o = next(o for o in POOL if o["id"] == it["id"])
            if not (o["age"][0] <= r["age"] <= o["age"][1]):
                errs.append(f"{cid}: {it['id']} age {r['age']} outside {o['age']}")
            if o["sex"] and o["sex"] != r["sex"]:
                errs.append(f"{cid}: {it['id']} requires sex {o['sex']}")
        if r["target"] == "Elite" and (r["age"] > 65 or r["face"] < 250000 or r["items"]):
            errs.append(f"{cid}: Elite constraints")
        if r["target"] in ("Table 9-16", "Table Tobacco 5-16") and r["age"] > 70:
            errs.append(f"{cid}: high table at age {r['age']} (CLS-3.4)")
        if r["target"] == "Preferred Tobacco" and r["tobacco"].startswith("cig_"):
            errs.append(f"{cid}: cigarette smoker targeted Preferred Tobacco (TOB-2.1)")
        if (r["ladder"] == "tobacco") != (r["tobacco"] in TOB_LADDER):
            errs.append(f"{cid}: ladder {r['ladder']} vs tobacco {r['tobacco']}")
        if r["target"] == "Postpone" and not any(i["outcome"] == "postpone" for i in r["items"]):
            errs.append(f"{cid}: Postpone target without postpone item")
        if r["target"] == "Decline" and not any(i["outcome"] == "decline" for i in r["items"]) and \
                sum(i["debits"] for i in r["items"]) <= (225 if r["age"] >= 71 else 425):
            errs.append(f"{cid}: Decline target without decline route")
        tr = table_range(r["target"])
        if tr and not (tr[0] <= sum(i["debits"] for i in r["items"]) <= tr[1]):
            errs.append(f"{cid}: {r['target']} debits {sum(i['debits'] for i in r['items'])} outside {tr}")
    return errs


TOB_LADDER = {"cig_current", "cig_current_heavy", "cig_quit_lt12", "vape", "chew", "pipe", "nrt", "cigars_cot_pos", "cessation_rx_only"}
POOL = []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261109)
    a = ap.parse_args()
    d = Designer(a.n, a.seed)
    rows = d.run()
    out = ROOT / "data/design"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "matrix.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    with (out / "matrix.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "target", "ladder", "age", "sex", "face", "product", "items", "tobacco", "grey", "complexity",
                    "evidence_path", "persona", "lab", "aps_styles", "riders"])
        for r in rows:
            w.writerow([r["case_id"], r["target"], r["ladder"], r["age"], r["sex"], r["face"], r["product"],
                        "; ".join(f"{i['id']}[{i['disclosure']}]" for i in r["items"]), r["tobacco"], r["grey"] or "",
                        r["complexity"], r["evidence_path"], r["persona"], r["vendors"]["lab"], "|".join(r["aps_styles"]),
                        " ".join(r["riders_requested"])])
    report(rows, d.pool, ROOT / "qa/phase3_coverage.md")
    POOL.extend(d.pool)
    errs = validate_rows(rows)
    for e in errs[:40]:
        print("ERR", e)
    print(f"design validation: {len(errs)} errors ->", "PASS" if not errs else "FAIL")
    print(f"{len(rows)} rows, pool {len(d.pool)} options -> data/design/matrix.jsonl, qa/phase3_coverage.md")


if __name__ == "__main__":
    main()
