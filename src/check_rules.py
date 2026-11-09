"""Phase 1 step 5: rules/*.yaml <-> guidelines.md consistency.

1. Every rule id referenced in yaml exists in the markdown.
2. Key numeric tables are parsed out of the markdown and compared cell-by-cell with yaml.
Run: python src/check_rules.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MD = (ROOT / "reference/guidelines.md").read_text()
Y = {p.stem: yaml.safe_load(p.read_text()) for p in (ROOT / "rules").glob("*.yaml")}
errs: list[str] = []
ok: list[str] = []


def table_after(anchor: str, nth: int = 0) -> list[list[str]]:
    """Return rows (cells) of the first markdown table after `anchor`."""
    i = MD.index(anchor)
    lines = MD[i:].splitlines()
    rows, started = [], False
    for ln in lines[1:]:
        if ln.startswith("|"):
            started = True
            if re.match(r"^\|[-\s|]+\|$", ln):
                continue
            rows.append([c.strip() for c in ln.strip().strip("|").split("|")])
        elif started:
            if nth == 0:
                break
            nth -= 1
            started = False
            rows = []
    return rows[1:]  # drop header


def nums(s: str) -> list[float]:
    return [float(x) for x in re.findall(r"(?<![A-Za-z])[+-]?\d+(?:\.\d+)?", s.replace(",", "").replace("−", "-"))]


def cell_val(s: str):
    s = s.strip()
    if s.lower().startswith("decline"):
        return "decline"
    n = nums(s)
    return n[0] if n else s


def _n(v):
    if isinstance(v, (list, tuple)):
        return [_n(x) for x in v]
    return v if isinstance(v, str) else float(v)


def cmp(name: str, md_vals, y_vals):
    if _n(md_vals) == _n(y_vals):
        ok.append(name)
    else:
        errs.append(f"{name}: md={md_vals} yaml={y_vals}")


# ---- 1. rule ids
defined = set(re.findall(r"(?:^|\n)(?:\s*- |\*\*|\| |#+ )([A-Z]{2,4}-\d+(?:\.\d+)?)", MD))
chapters = set(re.findall(r"\n##+ ([A-Z]{2,4}) —", MD))


def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("rule", "id") and isinstance(v, str):
                yield v
            elif k == "rule_ids":
                yield from v
            else:
                yield from walk(v)
            if k == "requires" and isinstance(v, list):
                yield from (x for x in v if re.match(r"^[A-Z]{2,4}-\d", x))
    elif isinstance(o, list):
        for x in o:
            yield from walk(x)


bad_ids = sorted({r for r in walk(Y) if re.match(r"^[A-Z]{2,4}(-\d|$)", r) and r not in defined and r not in chapters and r != "terminal"})
if bad_ids:
    errs.append(f"yaml rule ids not in md: {bad_ids}")
else:
    ok.append("rule ids")

# chapter coverage: every medical chapter in md has >=1 catalog entry
med_chapters = {"HTN", "CV", "DM", "CA", "MH", "RSP", "GI", "REN", "NEU", "END", "MSK", "HEM", "IMM", "GER", "OBS", "MISC", "ALC", "DRG"}
cat_ch = {v["chapter"] for v in Y["impairments"].values()}
missing = med_chapters - cat_ch
(errs.append(f"chapters without catalog entries: {missing}") if missing else ok.append("chapter coverage"))

# ---- 2. tables
# CV-1 grid
rows = table_after("**CV-1 Coronary artery disease")
cmp("CV-1 grid", [cell_val(c) for r in rows for c in r[1:]],
    [v for r in Y["impairments"]["cad"]["grid"]["values"] for v in r])

# DM-2 grid
rows = table_after("Base debits by age at application and average A1c")
cmp("DM-2 grid", [cell_val(c) for r in rows for c in r[1:]],
    [v for r in Y["impairments"]["diabetes_t2"]["grid"]["values"] for v in r])

# HTN rows
rows = table_after("## HTN — Hypertension")
md_h = [[nums(r[0])[1] if len(nums(r[0])) > 2 else nums(r[0])[0], cell_val(r[1])] for r in rows if nums(r[1])]
md_h = [[nums(r[0])[-2] if len(nums(r[0])) >= 2 else nums(r[0])[0], cell_val(r[1])] for r in rows if nums(r[1])]
cmp("HTN debits", [r[1] for r in md_h], [r[2] for r in Y["nonmedical"]["htn"]["rows"]])

# LIP-3
rows = table_after("- LIP-3 Debits")
cmp("LIP-3 debits", [cell_val(r[1]) for r in rows[:3]], [r[2] for r in Y["nonmedical"]["lipids"]["rows"]])

# CLS-5 matrix: compare TC, ratio, nicotine years, ages
rows = {r[0]: r[1:] for r in table_after("### CLS-5 Preferred criteria matrix")}
cm = Y["classes"]["preferred_matrix"]["classes"]
order = ["Elite", "Preferred Plus", "Preferred", "Standard Plus"]
cmp("CLS-5 TC", [nums(c)[0] for c in rows["Total cholesterol"]], [cm[c]["tc_max"] for c in order])
cmp("CLS-5 ratio", [nums(c)[0] for c in rows["TC/HDL ratio"]], [cm[c]["ratio_max"] for c in order])
cmp("CLS-5 nicotine", [nums(c)[0] for c in rows["Nicotine-free"]], [cm[c]["nicotine_free_years"] for c in order])
cmp("CLS-5 ages", [nums(c) for c in rows["Ages eligible"]], [[float(x) for x in cm[c]["ages"]] for c in order])
cmp("CLS-5 BP<60", [nums(c)[:2] for c in rows["BP, ages 18–59"]], [[cm[c]["bp_under60"]["sys"], cm[c]["bp_under60"]["dia"]] for c in order])
cmp("CLS-5 BP60+", [nums(c)[-2:] if "60" not in c[:3] else nums(c)[:2] for c in rows["BP, ages 60+"]],
    [[cm[c]["bp_60plus"]["sys"], cm[c]["bp_60plus"]["dia"]] for c in order])

# CLS-6 credits
rows = table_after("### CLS-6 Credits")
cmp("CLS-6 credits", [(r[0], nums(r[2])[0]) for r in rows], [(c["id"], c["amount"]) for c in Y["classes"]["credits"]["items"]])

# REQ-1 grid (normalize codes)
norm = lambda s: sorted(set(re.sub(r"\+ ?", "", s).replace("2 yr ", "").replace("inspection report", "INSP")
                            .replace("stress test (MD)", "STRESS").replace("FIN-Q", "FINQ").replace("NT-proBNP", "NTPROBNP")
                            .replace("Accel", "ACCEL").replace(" ", "").split(",")))
rows = table_after("**REQ-1 Age/amount grid")
md_g = [[norm(c) for c in r[1:]] for r in rows]
y_g = [[sorted(set(c)) for c in r] for r in Y["requirements"]["grid"]]
# md uses "+ X" meaning "previous column plus X"; expand
for r in range(len(md_g)):
    for c in range(len(md_g[r])):
        if rows[r][c + 1].strip().startswith("+"):
            md_g[r][c] = sorted(set(md_g[r][c - 1]) | set(md_g[r][c]))
cmp("REQ-1 grid", md_g, y_g)

# FIN-1
rows = table_after("- FIN-1 **Income replacement multiples**")
cmp("FIN-1 multiples", [nums(r[1])[0] for r in rows[:5]], [m[2] for m in Y["nonmedical"]["financial"]["multiples"]])

# CLS-3.3 decline threshold & table formula
cmp("CLS-3.3 T16 upper", [425.0], [Y["classes"]["debit_table"]["decline_above"]])

# build chart: md fragment embedded == generated yaml
frag = (ROOT / "reference/fragments/build_chart.md").read_text()
(ok.append("build chart embedded") if frag.strip() in MD else errs.append("build chart fragment not embedded / stale"))

# cancer table spot checks: years windows & FE values per row present in md text
ca = Y["impairments"]["cancer"]["types"]
spot = {"breast_1": "1–3: FE $10 ×4", "breast_2": "2–5: FE $15 ×5", "melanoma_1": "0–2 yrs: FE $10 ×3",
        "colon_2": "2–5: FE $15 ×4", "prostate_ge8": "3–5: FE $15 ×5", "nhl_aggressive": "3–5: FE $15 ×5"}
for k, s in spot.items():
    (ok.append(f"CA {k}") if s in MD and k in ca else errs.append(f"CA {k}: '{s}' not found or type missing"))

print(f"OK ({len(ok)}): " + ", ".join(ok))
for e in errs:
    print("ERR", e)
print("RULES CONSISTENCY:", "PASS" if not errs else "FAIL")
sys.exit(1 if errs else 0)
