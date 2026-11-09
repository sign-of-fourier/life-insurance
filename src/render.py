"""Phase 4c: render structured document content -> source "PDF" text, one layout per doc type x vendor.

APS: full template rendering here (style-specific). src/render_aps_llm.py can replace narrative sections with
LLM prose (facts injected + verified); this template output is the fallback.
Run: python src/render.py [--ids ...]     writes data/source/<case>/<doc_id>.txt
"""
from __future__ import annotations

import argparse
import json
import random
import zlib
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rules import load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VEND = load("vendors")
RX = load("rx_map")["drugs"]
MVRC = load("mvr_codes")["codes"]
LABS = load("labs")
ABB = {"hypertension": "HTN", "Type 2 diabetes": "DM2", "Coronary artery disease / MI / stent / CABG": "CAD", "Atrial fibrillation / flutter": "AFib",
       "Depression / anxiety": "MDD/GAD", "Obstructive sleep apnea": "OSA", "COPD": "COPD", "Hypertension": "HTN"}
STATUTE = {"minor": ["VC 22350", "TC 545.351", "VTL 1180(b)", "ORC 4511.21"], "major": ["VC 23103", "TC 545.401", "VTL 1212"],
           "dui": ["VC 23152(a)", "TC 49.04", "VTL 1192.3", "ORC 4511.19"], "nonmoving": ["VC 4000(a)", "VC 24252"],
           "accident": ["RPT ACC"], "admin": ["ADM SUSP", "FTA"]}


PHRASE = {"ef": "EF {v}%", "recovered_years": "recovered ~{v} yrs", "stable_years": "stable x {v} yrs", "biologic": "on biologic therapy",
          "controller": "on daily controller", "a1c_avg": "A1c {v}", "egfr": "eGFR {v}", "urine_protein": "urine protein {v} mg/dL",
          "years_since": "{v} yrs ago", "years_since_dx": "dx {v} yrs ago", "years_since_tx": "last tx {v} yrs ago", "insulin": "on insulin",
          "duration_years": "duration {v} yrs", "age_at_dx": "dx at age {v}", "age_at_event": "event at age {v}", "vessels": "{v}-vessel disease",
          "fev1_pct": "FEV1 {v}% pred", "ahi": "AHI {v}", "edss": "EDSS {v}", "compliant": "compliant w/ tx", "treated": "treated",
          "meds_count": "{v} meds", "hospitalization_years_ago": "hospitalized {v} yrs ago", "psychiatrist": "followed by psychiatry",
          "seizure_free_years": "seizure-free {v} yrs", "seizures_per_year": "{v} seizures/yr", "svr": "SVR achieved", "agents": "{v} agent(s)",
          "steroid_bursts_per_year": "{v} steroid bursts/yr", "er_years_ago": "ER visit {v} yrs ago", "chads_vasc": "CHA2DS2-VASc {v}",
          "ablation_years": "ablation {v} yrs ago", "echo_normal": "normal echo", "abnormal_stress": "abnormal stress test",
          "normal_stress_12mo": "normal stress test within 12 mo", "angina": "ongoing angina", "smoker": "smoker", "ldl": "LDL {v}",
          "work_loss_months": "{v} mo off work", "cd4": "CD4 {v}", "undetectable_months": "VL undetectable x {v} mo", "art_years": "on ART {v} yrs",
          "size_cm": "{v} cm", "stenosis_pct": "{v}% stenosis", "cac_score": "CAC score {v}", "gleason": "Gleason {v}",
          "abstinent_years": "abstinent {v} yrs", "years_since_last_use": "last use {v} yrs ago", "maintenance_years": "on maintenance {v} yrs"}


def fmt_d(s, f):
    return (date.fromisoformat(s[:10]) if isinstance(s, str) else s).strftime(f)


# --------------------------------------------------------------------------------------------- application
def r_app1(c, r):
    L = [f"INDIVIDUAL LIFE APPLICATION - PART 1   (Form {c['form']})", "=" * 60,
         f"Proposed Insured: {c['name']}    Sex: {c['sex']}    DOB: {fmt_d(c['dob'], '%m/%d/%Y')}",
         f"Residence: {c['state']}, {c['country']}    Citizenship: {c['citizenship']}" + (f"    Visa: {c['visa']}" if c['visa'] else "") +
         (f"    Years in US: {c['years_in_us']}" if c['years_in_us'] else ""),
         f"Occupation: {c['occupation']}    Annual earned income: ${c['income']:,}    Net worth: ${c['net_worth']:,}",
         f"Marital status: {c['marital']}    Dependents: {c['dependents']}", "",
         f"Plan: {c['product']}    Face amount: ${c['face']:,}    Riders: {', '.join(c['riders']) or 'none'}",
         f"Existing coverage in force: ${c['existing']:,}    Replacement: {'Yes' if c['replacement'] else 'No'}    Beneficiary: {c['beneficiary']}",
         "", f"Signed: {fmt_d(c['signed'], '%m/%d/%Y')}   Signed in US: {'Yes' if c['signed_in_us'] else 'No'}"]
    return "\n".join(L)


def r_app1_facts(evf):
    """append Part 1 question answers (avocation, travel, DUI, criminal, prior apps) from facts."""
    L = ["", "GENERAL QUESTIONS"]
    for f in evf:
        if f["key"] in ("avocation", "hazardous_avocation", "foreign_travel", "dui_10y", "criminal", "prior_application", "residence"):
            v = f["value"]
            if isinstance(v, dict):
                v = ", ".join(f"{k}={x}" for k, x in v.items())
            L.append(f"  {f['key'].replace('_', ' ').title()}: {v}")
    if len(L) == 2:
        L.append("  Hazardous avocations / aviation / foreign travel / DUI / criminal: No")
    return "\n".join(L)


def r_app2(c, r):
    nums = c["numbering"]
    L = [f"PART 2 - MEDICAL QUESTIONNAIRE   (Form {c['form']})", "=" * 60]
    labels = {"tobacco": "Tobacco/nicotine use", "alcohol": "Alcohol use", "alcohol_treatment": "Treatment/counseling for alcohol",
              "drugs": "Use of marijuana or controlled substances", "heart": "Heart disease, chest pain, murmur, irregular heartbeat",
              "bp": "High blood pressure", "diabetes": "Diabetes or elevated blood sugar", "cancer": "Cancer, tumor, or growth",
              "mental": "Anxiety, depression, or other mental health condition", "respiratory": "Asthma, COPD, sleep apnea, lung disorder",
              "digestive": "Liver, stomach, intestinal disorder", "kidney": "Kidney or urinary disorder", "neuro": "Seizure, stroke, MS, or neurological disorder",
              "endocrine": "Thyroid or other gland disorder", "musculoskeletal": "Back, joint, or muscle disorder", "blood_immune": "Blood or immune disorder, lupus",
              "hiv": "Diagnosed with HIV/AIDS", "other": "Any other condition, treatment, or consultation", "pending_tests": "Tests, surgery, or consultation pending",
              "hospitalized_5y": "Hospitalized in the past 5 years", "current_meds": "Current medications", "physician": "Primary physician",
              "family_history": "Family history (parents, siblings)", "weight_change": "Weight change > 10 lbs in past 12 months", "height_weight": "Height / weight"}
    if c["form"] == "APP-2019":
        labels["tobacco"] = "In the past 5 years have you used tobacco or nicotine in any form?"
    else:
        labels["tobacco"] = "Any tobacco/nicotine product in the last 12 months? If no, date of last use"
    for q, n in nums.items():
        a = c["answers"][q]
        L.append(f"{n:>4}. {labels[q]}: {a['answer']}")
        det = a.get("details")
        if det:
            for d in det if isinstance(det, list) else [det]:
                if isinstance(d, dict):
                    L.append(f"        - {d.get('condition')}; dx {d.get('diagnosed')}; tx: {d.get('treatment')}; MD: {d.get('physician') or 'n/a'}")
                else:
                    L.append(f"        - {d}")
    return "\n".join(L)


# --------------------------------------------------------------------------------------------- third party
def r_rx(c, r):
    v = c["vendor"]
    if c["no_history"]:
        return f"{VEND['rx_vendors'][v]['name']}\nSearch result: NO PRESCRIPTION HISTORY FOUND"
    if v == "SCR":
        rows = []
        for f in c["fills"]:
            for d in f["fills"]:
                rows.append((d, f))
        rows.sort(key=lambda x: x[0], reverse=True)
        L = [f"SCRIPTCHECK Rx HISTORY REPORT   lookback {VEND['rx_vendors']['SCR']['lookback_years']} yrs", "-" * 110,
             f"{'FILL DATE':10} {'DRUG':34} {'STRENGTH':14} {'QTY':>4} {'DAYS':>4}  {'PRESCRIBER':26} {'SPECIALTY':18}"]
        for d, f in rows:
            qty = f["days_supply"] * r.choice([1, 1, 2]) if f["days_supply"] > 10 else r.choice([10, 14, 20, 30])
            L.append(f"{fmt_d(d, '%m/%d/%Y'):10} {f['drug'].upper()[:34]:34} {f['strength'][:14]:14} {qty:>4} {f['days_supply']:>4}  {f['prescriber'][:26]:26} {f['specialty'][:18]:18}")
        return "\n".join(L)
    L = ["RxProfile+  MEDICATION SUMMARY (grouped)", "-" * 100, f"{'MEDICATION':52} {'FIRST':10} {'LAST':10} {'#':>3}  PRESCRIBER"]
    for f in c["fills"]:
        ndc = f"{r.randint(1000, 69999):05d}-{r.randint(100, 9999):04d}-{r.randint(1, 99):02d}"
        name = f"{f['brand'].split(' / ')[0].upper()} {f['strength'].upper().replace(' ', '')} TAB (NDC {ndc})"
        L.append(f"{name[:52]:52} {fmt_d(f['fills'][0], '%m/%d/%y'):10} {fmt_d(f['fills'][-1], '%m/%d/%y'):10} {len(f['fills']):>3}  {f['prescriber']}")
    return "\n".join(L)


def r_mib(c, r):
    if c["vendor"] == "MIBF":
        L = ["MIB, Inc. - CHECKING SERVICE - FULL REPORT", "-" * 60]
        if c["no_hit"]:
            return "\n".join(L + ["RESULT: NO RECORD FOUND"])
        L.append(f"{'CODE':8} {'REPORTED':12} MEMBER TYPE")
        for cd in c["codes"]:
            L.append(f"{cd['code']:8} {fmt_d(cd['reported'], '%m/%d/%Y'):12} {r.choice(['LIFE', 'LIFE', 'DI', 'HEALTH'])}")
        return "\n".join(L)
    L = ["MIB CHECK - SUMMARY", f"HITS: {len(c['codes'])}"]
    for cd in c["codes"]:
        L.append(f"  {cd['code']}  ({cd['reported'][:4]})")
    return "\n".join(L)


def r_mvr(c, r):
    if c["foreign_license"]:
        return "MVR REQUEST: NO US LICENSE ON FILE (foreign license stated)"
    if c["vendor"] == "ACD":
        L = [f"MOTOR VEHICLE REPORT  State: {c['license_state']}  License status: {c['status']}", "-" * 70]
        if c["no_record"]:
            return "\n".join(L + ["NO VIOLATIONS ON RECORD"])
        L.append(f"{'VIOL DATE':10} {'CONV DATE':10} {'CODE':5} {'DESCRIPTION':40} PTS")
        for e in sorted(c["events"], key=lambda e: e["date"], reverse=True):
            conv = date.fromisoformat(e["date"]).toordinal() + r.randint(20, 90)
            L.append(f"{fmt_d(e['date'], '%m/%d/%Y'):10} {date.fromordinal(conv).strftime('%m/%d/%Y'):10} {e['code']:5} {e['desc'][:40]:40} {r.choice([0, 1, 2, 3]) if e['code'][0] in 'SMRA' else 0}")
        return "\n".join(L)
    L = [f"{c['license_state']} DEPT OF MOTOR VEHICLES - DRIVER RECORD    STATUS {c['status']}"]
    if c["no_record"]:
        return "\n".join(L + ["*** CLEAR ***"])
    for e in sorted(c["events"], key=lambda e: e["date"], reverse=True):
        cls = MVRC[e["code"]]["class"]
        abbrev = e["desc"].upper().replace("SPEEDING ", "SPD ").replace(" OVER LIMIT", "").replace("ACCIDENT", "ACC").replace("DRIVING", "DRV")[:28]
        L.append(f"{fmt_d(e['date'], '%m%d%y')}  {r.choice(STATUTE.get(cls, ['MISC']))}  {abbrev}")
    return "\n".join(L)


# --------------------------------------------------------------------------------------------- exam / labs
def r_paramed(c, r):
    v = c["vendor"]
    h, w = c["height_in"], c["weight_lb"]
    if v == "PMX":
        L = [f"PARAMEDEX EXAMINATION REPORT   Exam date {fmt_d(c['exam_date'], '%m/%d/%Y')}", "-" * 50,
             f"Ht {int(h // 12)}'{h % 12:g}\"  Wt {w} lbs", *[f"BP#{i + 1}: {s}/{d}" for i, (s, d) in enumerate(c["bp"])], f"Pulse: {c['pulse']}"]
        if c["examiner_notes"]:
            L.append("Examiner remarks:")
            L += [f"  - {k}: {v2}" for k, v2 in c["examiner_notes"].items()]
        return "\n".join(L)
    return "\n".join([f"HEALTHSCREEN MOBILE  {fmt_d(c['exam_date'], '%d %b %Y')}", f"HEIGHT {h:g} in / WEIGHT {w / 2.2046:.1f} kg",
                      *[f"{s}/{d} ({r.choice(['sitting', 'sitting', 'standing'])})" for s, d in c["bp"]], f"HR {c['pulse']}"])


LAB_NAMES = {"tc": "Cholesterol", "hdl": "HDL", "ldl": "LDL (calc)", "triglycerides": "Triglycerides", "tc_hdl_ratio": "Chol/HDL ratio",
             "glucose_fasting": "Glucose, fasting", "glucose_random": "Glucose", "a1c": "Hemoglobin A1c", "ast": "AST (SGOT)", "alt": "ALT (SGPT)",
             "ggt": "GGT", "alk_phos": "Alkaline phosphatase", "bilirubin": "Bilirubin, total", "albumin": "Albumin", "creatinine": "Creatinine",
             "egfr": "eGFR", "hemoglobin": "Hemoglobin", "hiv": "HIV-1/2 Ab", "cdt": "%CDT", "psa": "PSA", "nt_probnp": "NT-proBNP",
             "cotinine_urine": "Cotinine", "urine_protein": "Protein, urine", "cocaine": "Cocaine metabolite", "urine_glucose": "Glucose, urine",
             "urine_rbc": "RBC, urine", "cotinine_saliva": "Cotinine (oral fluid)"}
REF = {"tc": (0, 199), "hdl": (40, 999), "ldl": (0, 99), "triglycerides": (0, 149), "tc_hdl_ratio": (0, 5.0), "glucose_fasting": (65, 99),
       "glucose_random": (65, 139), "a1c": (4.0, 5.6), "ast": (10, 40), "alt": (7, 45), "ggt": (8, 60), "alk_phos": (40, 130), "bilirubin": (0.2, 1.2),
       "albumin": (3.5, 5.0), "creatinine": (0.6, 1.3), "egfr": (60, 200), "hemoglobin": (12.0, 17.5), "cdt": (0, 1.6), "psa": (0, 4.0),
       "nt_probnp": (0, 124), "cotinine_urine": (0, 199), "urine_protein": (0, 30), "urine_rbc": (0, 5), "cotinine_saliva": (0, 29)}
SI = {"tc": ("mmol/L", 1 / 38.67), "hdl": ("mmol/L", 1 / 38.67), "ldl": ("mmol/L", 1 / 38.67), "triglycerides": ("mmol/L", 1 / 88.57),
      "glucose_fasting": ("mmol/L", 1 / 18), "glucose_random": ("mmol/L", 1 / 18), "creatinine": ("umol/L", 88.4)}


def qual(k, v):
    if k in ("hiv", "cocaine", "urine_glucose"):
        return "REACTIVE" if k == "hiv" and v else "POSITIVE" if v else ("NONREACTIVE" if k == "hiv" else "NEGATIVE")
    return None


def r_lab(c, r, doc_type):
    v = c["vendor"] if doc_type != "lab_saliva" else c["vendor"] if c["vendor"] != "NGL" else "MIL"
    res = c["results"]
    vend = VEND["lab_vendors"][v]
    df = vend["date_format"]
    head = f"{vend['name'].upper()}   {'BLOOD PROFILE' if doc_type == 'lab_blood' else 'URINALYSIS' if doc_type == 'lab_urine' else 'ORAL FLUID PANEL'}"
    L = [head, f"Collected: {fmt_d(c['collected'], df)}" + (f"   Fasting: {'Y' if c.get('fasting') else 'N'}" if "fasting" in c else ""), "-" * 72]
    items = dict(res)
    if v == "APX":     # never flags; combined cells; units often omitted
        if {"tc", "hdl", "tc_hdl_ratio"} <= set(items):
            L.append(f"{'LIPID (CHOL/HDL/RATIO)':28} {items.pop('tc')}/{items.pop('hdl')}/{items.pop('tc_hdl_ratio')}")
        if {"ast", "alt"} <= set(items):
            L.append(f"{'AST/ALT':28} {items.pop('ast')}/{items.pop('alt')}")
        for k, val in items.items():
            q = qual(k, val)
            unit = LABS["analytes"].get(k, {}).get("unit", "") if r.random() < 0.6 else ""
            L.append(f"{vend['aliases'].get(k, LAB_NAMES.get(k, k)).upper():28} {q or val} {unit if not q else ''}".rstrip())
        return "\n".join(L)
    if v == "NGL":     # SI units, arrows, non-HDL instead of ratio
        if "tc_hdl_ratio" in items:
            items.pop("tc_hdl_ratio")
            items["non_hdl"] = None
        L.append(f"{'TEST':28} {'RESULT':>10}  {'UNITS':10} REFERENCE")
        for k, val in items.items():
            if k == "non_hdl":
                nh = (res["tc"] - res["hdl"]) / 38.67
                L.append(f"{'Non-HDL cholesterol':28} {nh:>10.2f}  {'mmol/L':10} <3.4" + ("  ↑" if nh > 3.4 else ""))
                continue
            q = qual(k, val)
            if q:
                L.append(f"{LAB_NAMES.get(k, k):28} {q:>10}")
                continue
            unit = LABS["analytes"].get(k, {}).get("unit", "")
            disp, lo, hi = val, *REF.get(k, (None, None))
            if k in SI:
                unit, f = SI[k]
                disp = round(val * f, 2 if f < 1 else 0); lo = round(lo * f, 2) if lo is not None else None; hi = round(hi * f, 2) if hi is not None else None
            if k == "a1c":
                unit, disp = "mmol/mol", round((val - 2.15) * 10.929)
                lo, hi = 20, 38
            arrow = "  ↑" if hi is not None and disp > hi else "  ↓" if lo is not None and disp < lo else ""
            L.append(f"{vend['aliases'].get(k, LAB_NAMES.get(k, k)):28} {disp:>10}  {unit:10} {lo}-{hi}{arrow}")
        return "\n".join(L)
    # MIL: letter flags + reference ranges
    L.append(f"{'TEST':28} {'RESULT':>10} {'FLAG':4}  {'UNITS':10} REF RANGE")
    for k, val in items.items():
        q = qual(k, val)
        lo, hi = REF.get(k, (None, None))
        flag = "" if q or lo is None else ("H" if val > hi else "L" if val < lo else "")
        if q:
            flag = "C" if q in ("POSITIVE", "REACTIVE") else ""
        unit = LABS["analytes"].get(k, {}).get("unit", "")
        L.append(f"{vend['aliases'].get(k, LAB_NAMES.get(k, k)):28} {q or val:>10} {flag:4}  {unit if not q else '':10} {'' if lo is None else f'{lo}-{hi}'}")
    return "\n".join(L)


def r_ekg(c, r):
    return f"RESTING 12-LEAD ECG\nVentricular rate: {c['rate']} bpm\nInterpretation: {c['interpretation'].upper()}\nComputer-read; confirm clinically."


def r_other(c, r):
    t = c["type"]
    title = {"ALCQ": "ALCOHOL USE QUESTIONNAIRE", "AVOQ": "AVIATION / AVOCATION QUESTIONNAIRE", "FORQ": "FOREIGN TRAVEL & RESIDENCE QUESTIONNAIRE",
             "FINQ": "FINANCIAL SUPPLEMENT"}[t]
    L = [title, "-" * len(title)]
    for k, v in c.items():
        if k == "type":
            continue
        if isinstance(v, list):
            for it in v:
                L.append(f"  {k}: " + ", ".join(f"{a}={b}" for a, b in it.items()))
        else:
            L.append(f"  {k.replace('_', ' ')}: {v:,}" if isinstance(v, int) and v > 9999 else f"  {k.replace('_', ' ')}: {v}")
    return "\n".join(L)


# --------------------------------------------------------------------------------------------- APS (template)
def dx_phrase(p, r, abbrev):
    d = p["details"]
    k = p["key"]
    label = ABB.get(p["dx"], p["dx"]) if r.random() < abbrev else p["dx"]
    bits = []
    for a, v in d.items():
        if a in ("type", "member", "stage_documented", "a1c_available") or v in (None, False):
            continue
        ph = PHRASE.get(a)
        if ph:
            bits.append(ph.format(v=v) if not isinstance(v, bool) else ph.split("{")[0].strip())
        elif isinstance(v, bool):
            bits.append(a.replace("_", " "))
        else:
            bits.append(f"{a.replace('_', ' ')} {v}")
    if k == "cancer":
        t = d.get("type", "")
        label = f"{t.split('_')[0].title()} cancer" + (f", stage {d['stage']}" if d.get("stage") else ", stage not stated")
        bits = [f"s/p treatment ~{d.get('years_since_tx')} yrs ago"] + ([f"Gleason {d['gleason']}"] if "gleason" in d else [])
    return f"{label}" + (f" ({'; '.join(bits[:6])})" if bits else "")


def r_aps(c, r):
    st = c["style"]
    prov = c["provider"]
    pt = c["patient"]
    ab = VEND["aps_styles"][st]["abbrev"]
    hdr = f"{prov['practice']}  |  {prov['name']}, {prov['specialty']}"
    pat = f"Patient: {pt['name']}   DOB: {fmt_d(pt['dob'], '%m/%d/%Y')}   Sex: {pt['sex']}   MRN: {r.randint(100000, 999999)}"
    probs = c["problems"]
    L: list[str] = []
    if st == "epic_progress":
        L += [hdr, pat, "", "PROBLEM LIST"]
        L += [f"  - {dx_phrase(p, r, ab)}  [{p['status']}]  onset {fmt_d(p['onset'], '%m/%Y')}" for p in probs]
        for ro in c["rule_outs"]:
            L.append(f"  - r/o {ro}")
        L += ["", "MEDICATIONS"] + [f"  {m}" for p in probs for m in p["meds"]] + ["", "ENCOUNTERS"]
        for v in c["visits"]:
            L += [f"--- {fmt_d(v['date'], '%m/%d/%Y')}  Office Visit  ---", f"S: f/u {v['reason']}.", f"O: BP {v['bp']}  Wt {v['weight_lb']} lb",
                  f"A: {v['reason']} - " + r.choice(["stable", "improving", "unchanged", "fair control"]), "P: continue current tx; RTC 3-6 mo", ""]
    elif st == "athena_summary":
        L += [f"CLINICAL SUMMARY - {prov['practice']}", pat, "", "Encounters:"]
        L += [f"  {fmt_d(v['date'], '%Y-%m-%d')}  {v['reason']}  BP {v['bp']}  Wt {v['weight_lb']}" for v in c["visits"]]
        L += ["", "Assessment/Plan:"] + [f"  • {dx_phrase(p, r, ab)} - {p['status']}; meds: {', '.join(p['meds']) or 'none'}" for p in probs]
    elif st == "ecw_problem_heavy":
        L += [hdr, pat, "", "PROBLEM LIST (active + resolved)"]
        L += [f"  {i + 1}. {dx_phrase(p, r, ab)}" for i, p in enumerate(probs)]
        for ro in c["rule_outs"] + r.sample(["hx of syncope", "r/o OSA", "elevated LFTs (resolved)", "chest pain NOS"], 2):
            L.append(f"  {len(L)}. {ro}")
        para = "Pt here for f/u. " + " ".join(f"{dx_phrase(p, r, ab)} - {p['status']}." for p in probs[:3])
        for v in c["visits"]:
            L += ["", f"{fmt_d(v['date'], '%m/%d/%y')} PN: {para if c['copy_forward'] else v['reason']} BP {v['bp']}. Wt {v['weight_lb']}."]
    elif st == "small_practice_typed":
        L += [f"{prov['practice']}", f"Re: {pt['name']} (DOB {fmt_d(pt['dob'], '%m/%d/%Y')})", ""]
        for v in c["visits"]:
            L.append(f"{fmt_d(v['date'], '%B %d, %Y')}: Seen today regarding {v['reason']}. Blood pressure {v['bp']}, weight {v['weight_lb']} pounds. "
                     + (" ".join(f"Known {dx_phrase(p, r, 0.1)}." for p in probs[:2]) if r.random() < 0.6 else "Doing well."))
            L.append("")
    elif st == "handwritten_scan":
        L += ["[FAX] p.1  ----  " + prov["practice"][:30], f"pt {pt['name'].split()[-1]}  dob {fmt_d(pt['dob'], '%m/%d/%y')}"]
        for v in c["visits"]:
            L.append(f"{fmt_d(v['date'], '%m/%d')} - {v['reason'][:25]} bp {v['bp']} wt {v['weight_lb']} " + r.choice(["ok", "f/u 3mo", "cont meds", "[illegible]"]))
        L += ["Dx: " + "; ".join(dx_phrase(p, r, 0.9) for p in probs)]
    elif st == "specialist_letter":
        L += [prov["practice"], "", "Dear Colleague,", "",
              f"I saw {pt['name']} in consultation on {fmt_d(c['visits'][0]['date'], '%B %d, %Y')}." if c["visits"] else ""]
        for p in probs:
            L.append(f"Regarding {dx_phrase(p, r, ab)}: currently {p['status']}; medications {', '.join(p['meds']) or 'none'}.")
        L += ["", "Impression and recommendations as above. Thank you for this referral.", "", f"{prov['name']}"]
    elif st == "hospital_discharge":
        main = probs[0] if probs else {"dx": "observation", "details": {}, "key": "", "meds": [], "status": "", "onset": c["last_visit"]}
        L += [f"{prov['practice'].upper()} - DISCHARGE SUMMARY", pat, f"Admit: {fmt_d(main['onset'], '%m/%d/%Y')}", "",
              f"Principal diagnosis: {dx_phrase(main, r, ab)}", "Secondary: " + "; ".join(dx_phrase(p, r, ab) for p in probs[1:]),
              "", "Hospital course: uneventful. Discharged home in stable condition.", "Discharge meds: " + ", ".join(m for p in probs for m in p["meds"])]
    elif st == "foreign_translated":
        L += ["CERTIFIED TRANSLATION - original in " + r.choice(["Spanish", "Portuguese", "Mandarin", "Hindi", "Tagalog"]),
              f"Translator: {r.choice(['M. Ortega', 'L. Chen', 'R. Iyer', 'A. Santos'])}, cert #{r.randint(10000, 99999)}", "", f"Patient: {pt['name']}"]
        for p in probs:
            L.append(f"- {dx_phrase(p, r, 0.2)} (since {fmt_d(p['onset'], '%d/%m/%Y')})")
    # common tail sections
    for k, s in c["series"].items():
        L.append(f"{k.upper()} trend: " + ", ".join(f"{fmt_d(x['date'], '%m/%y')} {x['value']}" for x in s))
    if c["noncompliant"]:
        L.append("Note: patient non-compliant with medications; missed follow-up appointments x2.")
    if c["exercise_documented"]:
        L.append("Exercise: runs 3-4x/week.")
    if c["tobacco_documented"]:
        u = c["tobacco_documented"][0]
        L.append(f"Social: tobacco - {u['product']} {u['status']} {u['frequency']}" + (f", quit {u['quit'][:7]}" if u.get("quit") else ""))
    if c["alcohol_dpw"]:
        L.append(f"Social: alcohol ~{c['alcohol_dpw']} drinks/week")
    if c["legacy_lab"]:
        ll = c["legacy_lab"]
        L += ["", f"[attached outside lab - Heritage Diagnostic Services {fmt_d(ll['date'], '%m-%d-%y')}]",
              f"  CHOL / HDL  {ll['results']['tc']} / {ll['results']['hdl']}", f"  FRUCTOSAMINE  {ll['results']['fructosamine']}",
              f"  NICOTINE METAB  {ll['results']['cotinine_qual']}", f"  GAMMA GT  {ll['results']['ggt']}"]
    if c["stale"]:
        L.append(f"(Records end {fmt_d(c['last_visit'], '%m/%d/%Y')}; no subsequent visits on file.)")
    noise = VEND["aps_styles"][st].get("page_noise", [])
    if noise:
        L = [f"Printed by: ROI_{r.randint(10, 99)} {datetime.now():%m/%d/%Y}", "CONFIDENTIAL - Contains PHI"] + L + [f"Page {c['pages']} of {c['pages']}"]
    return "\n".join(x for x in L if x is not None)


RENDER = {"app_part1": r_app1, "app_part2": r_app2, "rx": r_rx, "mib": r_mib, "mvr": r_mvr, "paramed": r_paramed, "ekg": r_ekg,
          "other": r_other, "aps": r_aps}


def _ints(o):
    if isinstance(o, float) and o.is_integer():
        return int(o)
    if isinstance(o, dict):
        return {k: _ints(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_ints(v) for v in o]
    return o


def render_case(cdir: Path):
    ev = json.loads((cdir / "evidence.json").read_text())
    content = _ints(json.loads((cdir / "content.json").read_text())["docs"])
    facts_by_doc = {}
    for f in ev["facts"]:
        facts_by_doc.setdefault(f["doc_id"], []).append(f)
    n = 0
    llm_done = set()
    log = ROOT / "qa/phase4c_aps_llm.jsonl"
    if log.exists():
        llm_done = {j["doc_id"] for j in map(json.loads, log.read_text().splitlines()) if j["status"].startswith("llm")}
    for d in ev["docs"]:
        if d["doc_id"] in llm_done:
            continue      # keep LLM-rendered APS
        r = random.Random(zlib.crc32((d["doc_id"]).encode()))
        c = content[d["doc_id"]]
        if d["doc_type"].startswith("lab_"):
            txt = r_lab(c, r, d["doc_type"])
        else:
            txt = RENDER[d["doc_type"]](c, r)
        if d["doc_type"] == "app_part1":
            txt += "\n" + r_app1_facts(facts_by_doc.get(d["doc_id"], []))
        (ROOT / d["text_path"]).write_text(txt + "\n")
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    a = ap.parse_args()
    dirs = sorted((ROOT / "data/source").glob("C*"))
    if a.ids:
        dirs = [d for d in dirs if d.name in set(a.ids.split(","))]
    tot = sum(render_case(d) for d in dirs)
    print(f"rendered {tot} docs for {len(dirs)} cases")


if __name__ == "__main__":
    main()
