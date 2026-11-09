"""Phase 4a gate: truth files realize their design specs.

Checks (per case): every catalog-profile condition re-matches its intended profile via rules.first_profile;
grid conditions (CAD, DM) look up the intended debits; build/BP/lipids land in the intended preferred-matrix
level (for net-0 preferred targets); tobacco pattern consistent with ladder; schema-valid.
Run: python src/check_truth.py   -> qa/phase4a_truth.md
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rules import first_profile, grid_lookup, load  # noqa: E402
from schemas import Truth  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CLS = load("classes")
BUILD = load("build")
PREF = ["Elite", "Preferred Plus", "Preferred", "Standard Plus", "Standard"]


def build_col(h, w):
    bmi = w * 703 / (h * h)
    for b in BUILD["upper_bands"]:
        if bmi <= b["max_bmi"] + 1e-9:
            return b["label"], b["debits"], bmi
    return "decline", None, bmi


def bp_level(s, d, age):
    for c in PREF[:4]:
        th = CLS["preferred_matrix"]["classes"][c]["bp_under60" if age < 60 else "bp_60plus"]
        if s <= th["sys"] and d <= th["dia"]:
            return c
    return "Standard"


def lip_level(tc, ratio):
    for c in PREF[:4]:
        m = CLS["preferred_matrix"]["classes"][c]
        if tc <= m["tc_max"] and ratio <= m["ratio_max"]:
            return c
    return "Standard"


COLMAP = {"Elite": "Elite", "Pref Plus": "Preferred Plus", "Preferred": "Preferred", "Std Plus": "Standard Plus", "Standard": "Standard"}


def main():
    files = sorted((ROOT / "data/truth").glob("C*.json"))
    errs, warn, stats = [], [], Counter()
    for f in files:
        t = Truth.model_validate_json(f.read_text())
        row = t.design
        cid = t.case_id
        meds = [i for i in row["items"] if i["kind"] == "med"]
        conds = [c for c in t.conditions if not c.irrelevant]
        if len(conds) != len(meds):
            errs.append(f"{cid}: {len(conds)} conditions vs {len(meds)} med items")
        for it, c in zip(meds, conds):
            key, var = it["key"], it["variant"]
            e = load("impairments")[key]
            if key == "cad" and var == "recent_lt6mo":
                continue
            if key in ("cad",) and "age_at_event" in c.details:
                v = grid_lookup("cad", c.details["age_at_event"], c.details["years_since"])
                exp = "decline" if it["outcome"] == "decline" else it["debits"]
                stats["grid_checked"] += 1
                if v != exp:
                    errs.append(f"{cid}: cad grid {v} != design {exp} ({c.details['age_at_event']}, {c.details['years_since']})")
            elif key in ("diabetes_t2", "diabetes_t1"):
                v = grid_lookup("diabetes_t2", t.person.age, c.details["a1c_avg"])
                exp = it["debits"] - (50 if key == "diabetes_t1" else 0) if it["outcome"] == "rate" else "decline"
                stats["grid_checked"] += 1
                if key == "diabetes_t1" and it["outcome"] == "decline":
                    continue
                if v != exp:
                    errs.append(f"{cid}: {key} grid {v} != design {exp} (age {t.person.age}, a1c {c.details['a1c_avg']})")
            elif "profiles" in e and key not in ("ckd",):
                p = first_profile(key, {**c.details, "age": t.person.age})
                stats["profile_checked"] += 1
                if not p or p["id"] != var:
                    errs.append(f"{cid}: {key} re-matched {p and p['id']} != {var}")
        # preferred-matrix placement (net-0 preferred targets only)
        tgt = row["target"]
        if tgt in PREF and not any(i["debits"] for i in row["items"]):
            col, d, bmi = build_col(t.height_in, t.weight_lb)
            lv = {"build": COLMAP.get(col, col), "bp": bp_level(t.bp_systolic, t.bp_diastolic, t.person.age),
                  "lipids": lip_level(t.true_labs["tc"], t.true_labs["tc_hdl_ratio"])}
            want = {r: row["matrix"]["base"] for r in lv}
            for rn, lvl in row["matrix"]["fails"]:
                if rn in want:
                    want[rn] = lvl
            if any(i["key"] == "hypertension" for i in row["items"]):
                lv.pop("bp"); want.pop("bp")
            for rn in lv:
                stats["matrix_checked"] += 1
                if PREF.index(lv[rn]) > PREF.index(want[rn]) if lv[rn] in PREF and want[rn] in PREF else lv[rn] != want[rn]:
                    errs.append(f"{cid}: {rn} at {lv[rn]} worse than intended {want[rn]}")
                elif lv[rn] != want[rn]:
                    warn.append(f"{cid}: {rn} at {lv[rn]} better than intended {want[rn]}")
        tob_ladder = row["ladder"] == "tobacco"
        cot = t.true_labs["cotinine_urine"]
        if tob_ladder and row["tobacco"] not in ("cessation_rx_only", "cig_quit_lt12") and cot < 200:
            errs.append(f"{cid}: tobacco ladder but cotinine {cot}")
        if not tob_ladder and cot >= 200:
            errs.append(f"{cid}: non-tobacco ladder but cotinine {cot}")
        stats["cases"] += 1
    lines = [f"# Phase 4a truth check", "", f"cases {stats['cases']}, profile re-matches {stats['profile_checked']}, "
             f"grid lookups {stats['grid_checked']}, matrix rows {stats['matrix_checked']}", "",
             f"errors: {len(errs)}", *[f"- {e}" for e in errs], "", f"warnings (better than intended): {len(warn)}",
             *[f"- {w}" for w in warn[:50]]]
    (ROOT / "qa/phase4a_truth.md").write_text("\n".join(lines) + "\n")
    print(lines[2])
    print(f"errors {len(errs)}, warnings {len(warn)}")
    for e in errs[:20]:
        print("ERR", e)
    for w in warn[:8]:
        print("WARN", w)
    print("PHASE 4a GATE:", "PASS" if not errs else "FAIL")


if __name__ == "__main__":
    main()
