"""Validate reference/rx_map.yaml: covers every catalog drug; indications resolve; ambiguous list matches RX-2.3."""
import sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[1]
RX = yaml.safe_load((ROOT / "reference/rx_map.yaml").read_text())
IMP = yaml.safe_load((ROOT / "rules/impairments.yaml").read_text())
errs = []
drugs = RX["drugs"]
need = set()
for k, v in IMP.items():
    need |= set(v.get("rx", []))
    for rs in (v.get("members") or {}).values():
        need |= set(rs)
need |= set(yaml.safe_load((ROOT / "rules/nonmedical.yaml").read_text())["tobacco"]["cessation_rx"])
miss = sorted(need - set(drugs))
if miss: errs.append(f"catalog drugs missing from rx_map: {miss}")
tags = set(IMP) | set(RX["nonimpairment_tags"]) | set(IMP["benign_no_rating"]["members"])
for d, (brand, strengths, impact, inds) in drugs.items():
    if impact not in ("high", "ambiguous", "low"): errs.append(f"{d}: bad impact {impact}")
    if not strengths: errs.append(f"{d}: no strengths")
    for i in inds:
        if i not in tags: errs.append(f"{d}: unknown indication {i}")
    if impact == "ambiguous" and len(inds) < 2: errs.append(f"{d}: ambiguous but 1 indication")
# RX-2.3 named ambiguous drugs
for d in ["metoprolol", "propranolol", "gabapentin", "bupropion", "trazodone", "prednisone", "metformin",
          "spironolactone", "hydroxychloroquine", "amitriptyline", "clonidine", "topiramate"]:
    if drugs.get(d, [None, None, None])[2] != "ambiguous": errs.append(f"RX-2.3 drug {d} not tagged ambiguous")
unordered = {i for v in drugs.values() if v[2] == "ambiguous" for i in v[3]} - set(RX["least_severe_order"])
if unordered: errs.append(f"ambiguous indications missing from least_severe_order: {sorted(unordered)}")
from collections import Counter
c = Counter(v[2] for v in drugs.values())
print(f"{len(drugs)} drugs: {dict(c)}")
for e in errs: print("ERR", e)
print("RX:", "PASS" if not errs else "FAIL"); sys.exit(1 if errs else 0)
