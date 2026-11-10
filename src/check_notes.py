"""Phase 6 gate: noisy notes trace back to their golden and corruption rates follow persona parameters.

- every golden has notes; validate.check_notes (corruptions cite real facts/steps; stated != golden only when a
  wrong_final / grey_divergence is logged)
- knockout steps (decline / postpone) are never omitted
- no drug name in the notes that is absent from the case's golden findings (LLM hallucination check)
- persona fidelity: Spearman rank correlation across the 12 personas between the yaml parameter and the observed rate
  (typo, omission, tier-1/2/3 abbreviation density, words per line vs sentences, grey divergence vs |leniency|)
Run: python src/check_notes.py -> qa/phase6_notes.md
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gen_notes import AMAP, APAT  # noqa: E402
from rules import load  # noqa: E402
from schemas import EvidenceBundle, Golden, Notes  # noqa: E402
from validate import check_notes  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PERS = load("uw_personas")["personas"]
RX = load("rx_map")["drugs"]
RXNAMES = {d.lower() for d in RX if len(d) > 4}


def spearman(x, y):
    def rk(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2
            i = j + 1
        return r
    a, b = rk(x), rk(y)
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((p - ma) * (q - mb) for p, q in zip(a, b))
    va = sum((p - ma) ** 2 for p in a) ** 0.5
    vb = sum((q - mb) ** 2 for q in b) ** 0.5
    return cov / (va * vb) if va and vb else 0.0


def main():
    gold = sorted((ROOT / "data/golden").glob("C*.json"))
    errs, halluc, missing = [], [], []
    st = defaultdict(Counter)
    llm = {}
    lp = ROOT / "qa/phase6_notes_llm.jsonl"
    if lp.exists():
        for ln in lp.read_text().splitlines():
            x = json.loads(ln)
            llm[x["case_id"]] = x
    stated_diff = Counter()
    for gp in gold:
        cid = gp.stem
        np_ = ROOT / f"data/notes/{cid}.json"
        if not np_.exists():
            missing.append(cid)
            continue
        g = Golden.model_validate_json(gp.read_text())
        n = Notes.model_validate_json(np_.read_text())
        ev = EvidenceBundle.model_validate_json((ROOT / f"data/source/{cid}/evidence.json").read_text())
        e = check_notes(ev, g, n)
        if e:
            errs.append(f"{cid}: {e[:3]}")
        kinds = Counter(c.kind for c in n.corruptions)
        om = {c.step for c in n.corruptions if c.kind == "omitted_step"}
        for s in g.trace:
            if (s.effect.decline or s.effect.postpone_months) and s.step in om:
                errs.append(f"{cid}: knockout step {s.step} omitted")
        text = " ".join(o.text for o in n.observations).lower()
        ref = " ".join(s.finding for s in g.trace).lower().replace("_", " ")
        for d in RXNAMES:
            if re.search(rf"\b{re.escape(d)}\b", text) and d not in ref:
                halluc.append(f"{cid}: {d}")
        P = n.persona_id
        s_ = st[P]
        s_["cases"] += 1
        s_["steps"] += len([x for x in g.trace if str(getattr(x.stage, "value", x.stage)) != "final"])
        lines = [ln for o in n.observations for ln in re.split(r"\n|; | / ", o.text)]
        s_["lines"] += len(lines)
        s_["words"] += sum(len(ln.split()) for ln in lines)
        for k, v in kinds.items():
            s_[k] += v
        s_["grey_cases"] += bool(g.grey_areas)
        s_["div"] += kinds["grey_divergence"]
        for c in n.corruptions:
            if c.kind == "grey_divergence":
                s_["dir_sum"] += 1 if "more lenient" in c.detail else -1
        full = text + " " + n.worksheet.lower()
        for m in APAT.finditer(full):       # phrases left unabbreviated = missed opportunities
            s_[f"left_t{AMAP[m.group(0).lower()][0]}"] += 1
        if n.stated_decision != g.decision.label():
            stated_diff["grey_divergence" if kinds["grey_divergence"] else "wrong_final"] += 1
        x = llm.get(cid)
        if x:
            s_["voiced"] += x["voiced"]
            s_["vlines"] += x["lines"]
    ps = sorted(st)
    obs = {
        "typo": [st[p]["typo"] / max(1, st[p]["words"]) for p in ps],
        "omit": [st[p]["omitted_step"] / max(1, st[p]["steps"]) for p in ps],
        "t1": [st[p]["abbrev_t1"] / max(1, st[p]["abbrev_t1"] + st[p]["left_t1"]) for p in ps],
        "t2": [st[p]["abbrev_t2"] / max(1, st[p]["abbrev_t2"] + st[p]["left_t2"]) for p in ps],
        "t3": [st[p]["abbrev_t3"] / max(1, st[p]["lines"]) for p in ps],
        "words/line": [st[p]["words"] / max(1, st[p]["lines"]) for p in ps],
        "divergence": [st[p]["div"] / max(1, st[p]["grey_cases"]) for p in ps],
        "div direction": [st[p]["dir_sum"] / max(1, st[p]["div"]) for p in ps],
    }
    par = {
        "typo": [PERS[p]["typo"] for p in ps], "omit": [PERS[p]["omit"] for p in ps],
        "t1": [PERS[p]["abbrev"]["t1"] for p in ps], "t2": [PERS[p]["abbrev"]["t2"] for p in ps],
        "t3": [PERS[p]["abbrev"]["t3"] for p in ps], "words/line": [PERS[p]["sentences"] for p in ps],
        "div direction": [PERS[p]["leniency"] for p in ps],
    }
    del obs["divergence"]
    rho = {k: spearman(par[k], obs[k]) for k in obs}
    tot = Counter()
    for p in ps:
        tot.update(st[p])
    n = len(gold)
    L = ["# Phase 6 notes check", "", f"cases {n}; notes missing {len(missing)}; validation errors {len(errs)}; "
         f"hallucinated drug names {len(halluc)}", "",
         f"LLM-voiced lines {tot['voiced']}/{tot['vlines']} ({tot['voiced'] / max(1, tot['vlines']):.0%}); rest kept the code skeleton", "",
         f"stated decision != golden: {sum(stated_diff.values())} ({dict(stated_diff)}); grey-area cases {tot['grey_cases']}, "
         f"diverged {tot['div']} ({tot['div'] / max(1, tot['grey_cases']):.0%})", "",
         "## Corruptions (all cases)", ""]
    kinds = ["omitted_step", "fragment", "unstated_assumption", "abbrev_t1", "abbrev_t2", "abbrev_t3", "typo", "rider_code",
             "fact_not_in_extraction", "arithmetic_error", "wrong_final", "grey_divergence"]
    L += [f"- {k}: {tot[k]} ({tot[k] / n:.1f}/case)" for k in kinds]
    L += ["", "## Persona fidelity (Spearman rho, parameter vs observed, 12 personas; gate >= 0.6)",
          "t1/t2 = substitutions / (substitutions + phrases left unabbreviated); t3 = tags per line; div direction = mean of "
          "+1 (more lenient alternative) / -1 (stricter) vs leniency", ""]
    L += [f"- {k}: {v:+.2f}" for k, v in rho.items()]
    L += ["", "## Per persona", "", "| persona | cases | omit/step | typo/word | t1 rate | t2 rate | t3/line | words/line | div/grey | div dir |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for i, p in enumerate(ps):
        L.append(f"| {p} {PERS[p]['name']} | {st[p]['cases']} | {obs['omit'][i]:.2f} | {obs['typo'][i]:.3f} | {obs['t1'][i]:.2f} | "
                 f"{obs['t2'][i]:.2f} | {obs['t3'][i]:.2f} | {obs['words/line'][i]:.1f} | {st[p]['div'] / max(1, st[p]['grey_cases']):.2f} | "
                 f"{obs['div direction'][i]:+.2f} |")
    L += ["", "## Validation errors", "", *[f"- {e}" for e in errs[:40]], "", "## Hallucinated drug names", "",
          *[f"- {h}" for h in halluc[:40]], ""]
    (ROOT / "qa/phase6_notes.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:40]))
    ok = not missing and not errs and not halluc and all(v >= 0.6 for v in rho.values())
    print("PHASE 6 GATE:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
