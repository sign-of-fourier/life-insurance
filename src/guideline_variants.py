"""Phase 7 guideline arms (factor F4).

G1 full  = reference/guidelines.md minus the notes-conventions appendix (abbreviations are never given to the model).
G2 gap   = G1 minus the rules that RESOLVE grey-area / partial-evidence situations, so only retrieved notes carry them.
           The rating tables themselves stay (the model can still rate); what goes is the instruction for what to do
           when evidence is missing, stale, ambiguous or only an alert. Removed ids are also stripped from cross-references.

  python src/guideline_variants.py            # writes experiments/guidelines/G1.md, G2.md + prints the impact table
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from exp_data import EXP, ROOT, ids, labels, slice_of  # noqa: E402

OUT = EXP / "guidelines"

# id -> why it is in the gap arm.  DRAFT: shown to the user before freezing.
G2_REMOVE = {
    "GRY":    "whole grey-area chapter (permitted ranges + defaults for GRY-0..12)",
    "APS-6":  "no APS in file -> rate on app/Rx/labs, default row when severity undocumented",
    "APS-3":  "stale APS -> rate as uncontrolled / worst documented (and the GEN-5 pointer to it)",
    "APS-2":  "problem-list 'r/o' / 'history of' not rated unless corroborated",
    "RX-2.4": "ambiguous Rx, no APS -> least severe plausible indication",
    "MIB-4":  "undisclosed MIB code -> order APS; if not corroborated, ignore",
    "CA-1":   "unknown cancer stage -> next worse stage",
    "DM-2.4": "no A1c in 12 months -> assume 8.0-8.9 column",
    "RSP-2":  "no FEV1 for COPD -> rate as moderate",
    "ALC-1":  "app vs APS drinks/wk conflict -> use the higher",
}


def g1(md: str) -> str:
    return md.split("\n## Appendix")[0].rstrip() + "\n"


def drop_bullet(md: str, rid: str) -> tuple[str, int]:
    """Remove a '- RID ...' bullet (or '  - RID' sub-bullet) through its continuation lines."""
    pat = re.compile(rf"^(\s*)- {re.escape(rid)}\b.*?(?=^\s*- [A-Z]|^\s*$|^\||^#)", re.M | re.S)
    return pat.subn("", md, count=1)


def g2(md: str) -> tuple[str, dict]:
    log = {}
    md, n = re.subn(r"\n## GRY .*?(?=\n## |\n---\s*\n## |\Z)", "\n", md, flags=re.S)
    log["GRY"] = n
    for rid in G2_REMOVE:
        if rid != "GRY":
            md, log[rid] = drop_bullet(md, rid)
    # cross-references and pointers to removed rules
    md = md.replace(" (order current APS or treat as uncontrolled — `APS-3`)", "")
    md = md.replace("If no rule applies, say so,\n> cite `GRY-0`, and document the reasoning.", "If no rule applies, say so\n> and document the reasoning.")
    md = md.replace("cite `GRY-0`; ", "")
    gone = r"(?:GRY-\d+|" + "|".join(re.escape(r) for r in G2_REMOVE if r != "GRY") + r")"
    md = re.sub(rf"\s*\((?:`{gone}`(?:,\s*)?)+\)", "", md)          # ' (`GRY-5`)', ' (`APS-3`, `GRY-5`)'
    md = re.sub(rf",?\s*and document `{gone}`", "", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    left = sorted(set(re.findall(rf"\b{gone}\b", md)))
    return md, {"removed": log, "dangling": left}


def impact() -> list[tuple]:
    """Which cases cite a removed rule in the golden trace or grey areas, by slice."""
    from score_worksheet import golden
    rm = set(G2_REMOVE) - {"GRY"}
    hit = {k: Counter() for k in G2_REMOVE}
    tot = Counter()
    any_hit = Counter()
    for cid in ids():
        g = golden(cid)
        sl = slice_of(labels()[cid])
        tot[sl] += 1
        # CA-1 is also the engine's id for ordinary (known-stage) cancer rows, which stay in G2: count only the unknown-stage use
        cited = {s.rule_id for s in g.trace if s.rule_id != "CA-1"} | {r for ga in g.grey_areas for r in ga.rule_ids}
        mine = {r for r in cited if r in rm} | ({"GRY"} if any(r.startswith("GRY") for r in cited) else set())
        for r in mine:
            hit[r][sl] += 1
        if mine:
            any_hit[sl] += 1
    rows = [(k, hit[k]["grey"], hit[k]["partial"], hit[k]["clean"]) for k in G2_REMOVE]
    rows.append(("ANY", any_hit["grey"], any_hit["partial"], any_hit["clean"]))
    return rows, tot


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    md = (ROOT / "reference/guidelines.md").read_text()
    a = g1(md)
    b, info = g2(a)
    (OUT / "G1.md").write_text(a)
    (OUT / "G2.md").write_text(b)
    print(f"G1 {len(a.split()):,} words  G2 {len(b.split()):,} words  (~{len(a) // 4:,} / ~{len(b) // 4:,} tokens)")
    print("removed:", info["removed"], " dangling refs:", info["dangling"] or "none")
    rows, tot = impact()
    print(f"\ncases citing the rule (golden trace or grey areas)   grey n={tot['grey']}  partial n={tot['partial']}  clean n={tot['clean']}")
    for k, gr, pa, cl in rows:
        print(f"  {k:8s} grey {gr:4d}  partial {pa:4d}  clean {cl:4d}   {G2_REMOVE.get(k, '')}")


if __name__ == "__main__":
    main()
