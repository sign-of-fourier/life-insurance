"""Phase 2 gate: run all reference-dictionary validators + cross checks."""
import subprocess, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[1]
ok = True
for script in ["gen_mib.py", "check_rx.py"]:
    r = subprocess.run([sys.executable, str(ROOT / "src" / script)], capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1]); ok &= r.returncode == 0
ab = yaml.safe_load((ROOT / "reference/abbreviations.yaml").read_text())
pe = yaml.safe_load((ROOT / "reference/uw_personas.yaml").read_text())
rid = yaml.safe_load((ROOT / "rules/riders.yaml").read_text())["riders"]
errs = []
t3 = ab["tier3"]
for pid, p in pe["personas"].items():
    for q in p["quirks"]:
        if q not in t3: errs.append(f"{pid}: quirk {q} not in tier3")
    if p["worksheet"] not in pe["formats"]: errs.append(f"{pid}: bad worksheet format")
    for k in ("sentences", "typo", "arith_err", "omit", "wrong_final", "cite_rules"):
        if not 0 <= p[k] <= 1: errs.append(f"{pid}: {k} out of range")
    if not -1 <= p["leniency"] <= 1: errs.append(f"{pid}: leniency out of range")
# every rider has an official code in tier2 or a house variant in tier3
variants = " ".join(str(v) for v in t3.values())
for code in rid:
    if code not in ab["tier2"] and code not in variants: errs.append(f"rider {code} has no abbreviation/variant")
fmts = {p["worksheet"] for p in pe["personas"].values()}
if fmts != set(pe["formats"]): errs.append(f"not all worksheet formats used: {fmts}")
print(f"abbreviations: t1={len(ab['tier1'])} t2={len(ab['tier2'])} t3={len(t3)} | personas={len(pe['personas'])} formats={sorted(fmts)}")
for e in errs: print("ERR", e)
ok &= not errs
# other dictionaries load
for f in ["mvr_codes", "country_tiers", "occupations", "vendors"]:
    yaml.safe_load((ROOT / f"reference/{f}.yaml").read_text())
print("PHASE 2 GATE:", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
