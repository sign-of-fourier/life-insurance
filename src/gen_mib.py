"""Validate reference/mib_codebook.yaml against rules/impairments.yaml and render reference/mib_codebook.md.
Also exposes decode(code) for generators/renderers."""
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
CB = yaml.safe_load((ROOT / "reference/mib_codebook.yaml").read_text())
IMP = yaml.safe_load((ROOT / "rules/impairments.yaml").read_text())


def decode(code: str) -> str:
    c = CB["conditions"][code[:3]]
    return (f"{code}: {c['label']} | degree: {CB['degree'][int(code[3])]} | source: {CB['source'][int(code[4])]}"
            f" | {CB['qualifier'][int(code[5])]}" + (" | RETIRED" if c.get("retired") else ""))


def validate():
    errs = []
    conds = CB["conditions"]
    for k, v in conds.items():
        if not (len(k) == 3 and k.isdigit()):
            errs.append(f"bad condition code {k}")
        m = v.get("maps")
        if m and m not in IMP and m not in CB["nonmedical_maps"]:
            errs.append(f"{k} maps to unknown key {m}")
    for d in ("degree", "source", "qualifier"):
        if sorted(CB[d]) != list(range(10)):
            errs.append(f"{d} must define digits 0-9")
    mapped = {v.get("maps") for v in conds.values()}
    unmapped = [k for k in IMP if k not in mapped]
    if unmapped:
        errs.append(f"impairments with no MIB code: {unmapped}")
    return errs


def render():
    L = ["# MIB codebook (synthetic) — underwriter reference", "",
         "Generated from `reference/mib_codebook.yaml` by `src/gen_mib.py`. Read with guidelines §MIB.", "",
         "Code format: **S C C D R Q** — `SCC` condition (S = body system), `D` degree, `R` source, `Q` qualifier.",
         "Example: `803416` → Breast cancer · severe · attending physician statement · 1–5 years ago.", "",
         "## Reading rules", *[f"- {r}" for r in CB["reading_rules"]], ""]
    for name in ("degree", "source", "qualifier"):
        pos = {"degree": "4th", "source": "5th", "qualifier": "6th"}[name]
        L += [f"## {name.title()} ({pos} digit)", "", "| Digit | Meaning |", "|---|---|"]
        L += [f"| {k} | {v} |" for k, v in CB[name].items()] + [""]
    L += ["## Condition codes (SCC)", ""]
    for s, sname in CB["systems"].items():
        L += [f"### {s}xx — {sname}", "", "| SCC | Condition | Note |", "|---|---|---|"]
        for k, v in CB["conditions"].items():
            if k[0] == str(s):
                note = (v.get("note") or "") + (" **(retired)**" if v.get("retired") else "")
                L.append(f"| {k} | {v['label']} | {note.strip()} |")
        L.append("")
    (ROOT / "reference/mib_codebook.md").write_text("\n".join(L))


if __name__ == "__main__":
    e = validate()
    for x in e: print("ERR", x)
    render()
    n = len(CB["conditions"])
    print(f"{n} condition codes x 10x10x10 modifiers; md rendered")
    print("example:", decode("803416")); print("example:", decode("120282"))
    print("MIB:", "PASS" if not e else "FAIL"); sys.exit(1 if e else 0)
