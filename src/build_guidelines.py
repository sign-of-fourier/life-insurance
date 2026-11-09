"""Assemble reference/guidelines.md from reference/guidelines_src/*.md and run consistency checks."""
import re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def main():
    parts = sorted((ROOT / "reference/guidelines_src").glob("*.md"))
    md = "\n".join(p.read_text() for p in parts)
    md = md.replace("{{BUILD_CHART}}", (ROOT / "reference/fragments/build_chart.md").read_text())
    (ROOT / "reference/guidelines.md").write_text(md)

    errs, warns = [], []
    # defined ids: bold "**XXX-1.2" / line-start "- XXX-1.2" / table first cell "| XXX-1 |" / headings "## XXX —"
    defined = set(re.findall(r"(?:^|\n)(?:\s*- |\*\*|\| |#+ )([A-Z]{2,4}-\d+(?:\.\d+)?)", md))
    chapters = set(re.findall(r"\n##+ ([A-Z]{2,4}) —", md))
    refs = set(re.findall(r"`([A-Z]{2,4}(?:-\d+(?:\.\d+)?)?)`", md))
    for r in sorted(refs):
        if "-" in r:
            if r not in defined and r.split("-")[0] not in chapters | {"CLS"}:
                errs.append(f"reference to undefined rule {r}")
            elif r not in defined:
                # chapter exists; allow refs to table-row ids (e.g. LAB-2) only if chapter defines numbered rules
                base = r.split(".")[0]
                if base not in defined and r not in md.replace(f"`{r}`", ""):
                    warns.append(f"ref {r}: chapter exists but id not explicitly defined")
        elif r not in chapters and r not in {"B","U","S","PM","EKG","APS","COG","SSC"}:
            errs.append(f"reference to undefined chapter {r}")
    for cls in ["Elite","Preferred Plus","Preferred","Standard Plus","Standard","Preferred Tobacco",
                "Standard Tobacco","Table Tobacco","Postpone","Decline"]:
        if cls not in md: errs.append(f"class {cls} never mentioned")
    files = sorted(set(re.findall(r"`(reference/[\w./]+)`", md)))
    print(f"guidelines.md: {len(md.splitlines())} lines, {len(md.split())} words, {len(chapters)} chapters, {len(defined)} rule ids")
    print("chapters:", " ".join(sorted(chapters)))
    print("reference files cited (Phase 2 must create):", ", ".join(files))
    for w in warns: print("WARN", w)
    for e in errs: print("ERR ", e)
    print("CONSISTENCY:", "PASS" if not errs else "FAIL")
    sys.exit(1 if errs else 0)

if __name__ == "__main__":
    main()
