"""Phase 7 worksheet scorer: model output (decision + worksheet JSON) vs the golden trace.

The model under test returns OUTPUT_SCHEMA (below). Scoring is golden-side only and free (no LLM calls).

Golden "rated items" = trace steps with an effect (debits, credits, class cap, ladder move, flat extra, postpone,
decline), excluding the final-stage consequence lines (CLS-3.3 class from net, CLS-8.1 net > +425, CLS-7 postpone
summary, CMB-5 FE summary, CMB-6 total cap) because those follow from the items rather than being items.

Per-case metrics (all in [0, 1] except net_abs_err):
  decision      exact label (class + table, ladder-inclusive)      coarse   debit-scale band (chunks.coarse)
  ladder        tobacco vs non-tobacco                             net_abs_err  |model net - golden net|
  item_recall / item_precision / item_f1   golden rated items matched by model items (chapter + name, greedy)
  rule_acc      matched items whose rule id agrees (model id == golden id or starts with it)
  debit_exact / debit_close   matched items with equal debits / |delta| <= 25 (denominator = golden items)
  arith_ok      model's sum(debits - credits) == model's stated net_debits
  class_follows model's class is what the guideline gives for the model's OWN items (knockouts, postpone, net)
  fe_recall / fe_precision   flat extras ($/1000 + years) in the model decision vs golden
  grey_recall   golden GRY rule ids the model flagged in grey_areas (grey cases only)
  overrate_partial  model rated a condition the golden left unrated pending records (RX-2.4 / MIB-4); lower is better
  derived_coarse / derived_net_err   decision computed in code from the model's own items (separates rating
                judgement from class arithmetic)
  Model items with no effect at all are ignored (allowed, not penalised).
  worksheet     composite = mean(item_f1, debit_close, arith_ok, class_follows, fe_f1 if any FE else omitted)

  python src/score_worksheet.py --selftest     # golden-as-output must score 1.0; perturbations must lower it
"""
from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from exp_data import ROOT, band, rated  # noqa: E402
from rules import table_from_net  # noqa: E402
from schemas import Golden  # noqa: E402

OUTPUT_SCHEMA = """{
  "items": [                          // one line per rated finding (skip findings with no impact)
    {"item": "condition or finding, short", "rule_id": "guideline rule id, e.g. GI or TOB-2.1",
     "debits": 0, "credits": 0, "class_cap": null, "flat_extra": null /* or {"per_thousand": 2.5, "years": 3 or null} */,
     "postpone_months": null, "decline": false}
  ],
  "grey_areas": [{"issue": "...", "rule_ids": ["GRY-..", "..."], "chosen": "..."}],
  "decision": {"ladder": "non_tobacco" | "tobacco",
               "risk_class": "Elite|Preferred Plus|Preferred|Standard Plus|Standard|Preferred Tobacco|Standard Tobacco|Table|Table Tobacco|Postpone|Decline",
               "table": 0, "net_debits": 0, "flat_extras": [{"per_thousand": 2.5, "years": 3}], "postpone_months": null}
}"""

CONSEQUENCE = {"CLS-3.3", "CLS-3.2", "CLS-3.4", "CLS-8.1", "CLS-8.2", "CLS-7", "CMB-5", "CMB-6", "CLS-4"}
STOP = set("""a an and the of for with to in on per by from at or no not only file aps application rx app profile
default attributes documented chapter range debits debit rated rating years yrs since kind none true false""".split())
PARTIAL_UNRATED = {"RX-2.4", "MIB-4"}
PREFERRED_SET = {"Elite", "Preferred Plus", "Preferred", "Standard Plus", "Preferred Tobacco"}


# --------------------------------------------------------------------------- parsing
def parse(text: str) -> dict | None:
    """Model text -> dict (tolerates code fences / prose around one JSON object)."""
    if isinstance(text, dict):
        return text
    s = re.sub(r"```(?:json)?", "", text or "")
    i, j = s.find("{"), s.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(s[i:j + 1])
    except json.JSONDecodeError:
        s2 = re.sub(r"//[^\n]*", "", s[i:j + 1])
        s2 = re.sub(r",\s*([}\]])", r"\1", s2)
        try:
            return json.loads(s2)
        except json.JSONDecodeError:
            return None


def toks(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if t not in STOP and not t.isdigit()}


def chapter(rule: str) -> str:
    m = re.match(r"[A-Z]+", (rule or "").strip().upper())
    return m.group(0) if m else ""


def num(x, d=0):
    try:
        return int(round(float(x)))
    except (TypeError, ValueError):
        return d


# --------------------------------------------------------------------------- golden side
@lru_cache(maxsize=None)
def golden(cid: str) -> Golden:
    return Golden.model_validate_json((ROOT / f"data/golden/{cid}.json").read_text())


@lru_cache(maxsize=None)
def age(cid: str) -> int:
    return json.loads((ROOT / f"data/truth/{cid}.json").read_text())["person"]["age"]


def has_effect(e) -> bool:
    """Item-level effect. A ladder move alone is not an item: the ladder is scored at decision level."""
    return bool(e.debits or e.credits or e.class_cap or e.flat_extra or e.postpone_months or e.decline)


def consequence(s) -> bool:
    """Final-stage lines that follow from the items (class from net, summaries); knockouts found at final are kept."""
    e = s.effect
    if s.rule_id in CONSEQUENCE or s.finding.startswith("Knockout:"):
        return True
    return s.stage == "final" and not (e.debits or e.credits or e.decline or e.postpone_months)


def golden_items(g: Golden) -> list[dict]:
    out = []
    for s in g.trace:
        e = s.effect
        if not has_effect(e):
            continue
        if consequence(s):
            continue
        out.append({"step": s.step, "rule_id": s.rule_id, "ch": chapter(s.rule_id), "toks": toks(s.finding.split(" per ")[0]),
                    "debits": e.debits, "credits": e.credits, "decline": e.decline, "postpone": e.postpone_months,
                    "fe": (e.flat_extra.per_thousand, e.flat_extra.years) if e.flat_extra else None, "cap": e.class_cap})
    return out


def golden_output(cid: str) -> dict:
    """The golden decision rendered in OUTPUT_SCHEMA (self-test: must score 1.0)."""
    g = golden(cid)
    items = [{"item": s.finding.split(":")[0], "rule_id": s.rule_id, "debits": s.effect.debits, "credits": s.effect.credits,
              "class_cap": s.effect.class_cap, "postpone_months": s.effect.postpone_months, "decline": s.effect.decline,
              "flat_extra": {"per_thousand": s.effect.flat_extra.per_thousand, "years": s.effect.flat_extra.years} if s.effect.flat_extra else None}
             for s in g.trace if has_effect(s.effect) and not consequence(s)]
    d = g.decision
    return {"items": items, "grey_areas": [{"issue": ga.issue, "rule_ids": ga.rule_ids, "chosen": ga.chosen} for ga in g.grey_areas],
            "decision": {"ladder": str(getattr(d.ladder, "value", d.ladder)), "risk_class": d.risk_class, "table": d.table,
                         "net_debits": d.net_debits, "postpone_months": d.postpone_months,
                         "flat_extras": [{"per_thousand": f.per_thousand, "years": f.years} for f in d.flat_extras]}}


# --------------------------------------------------------------------------- model side
def model_items(out: dict) -> list[dict]:
    res = []
    for it in out.get("items") or []:
        if not isinstance(it, dict):
            continue
        fe = it.get("flat_extra")
        fe = (float(fe.get("per_thousand") or 0), fe.get("years")) if isinstance(fe, dict) and fe.get("per_thousand") else None
        m_ = {"rule_id": str(it.get("rule_id") or ""), "ch": chapter(str(it.get("rule_id") or "")),
                    "toks": toks(str(it.get("item") or "")), "debits": num(it.get("debits")), "credits": num(it.get("credits")),
                    "decline": bool(it.get("decline")), "postpone": it.get("postpone_months") or None, "fe": fe,
                    "cap": it.get("class_cap")}
        if m_["debits"] or m_["credits"] or m_["decline"] or m_["postpone"] or m_["fe"] or m_["cap"]:
            res.append(m_)                          # zero-effect lines are allowed but not scored as items
    return res


def label_of(d: dict) -> str:
    rc = str(d.get("risk_class") or "")
    if rc in ("Table", "Table Tobacco"):
        t = num(d.get("table"))
        return f"{rc} {t} (+{25 * t}%)"
    return rc


def coarse_of(rc: str, table: int, net: int = 0) -> str:
    """Class band: Pref (better than Standard) / Standard / T1-2 / T3-4 / T5-8 / T9-16 / Postpone / Decline.
    For derived decisions rc may be '<=Std' (net <= 0: Standard or better, the matrix decides)."""
    if rc in ("Decline", "Postpone", "<=Std"):
        return rc
    if rc in ("Table", "Table Tobacco"):
        return "T1-2" if table <= 2 else "T3-4" if table <= 4 else "T5-8" if table <= 8 else "T9-16"
    return "Standard" if rc in ("Standard", "Standard Tobacco") else "Pref"


def jacc(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def match(G: list[dict], M: list[dict]) -> list[tuple[int, int]]:
    """Greedy one-to-one: same chapter (+name overlap, +rule, +debits) or strong name overlap across chapters."""
    cand = []
    for i, g in enumerate(G):
        for j, m in enumerate(M):
            jc = jacc(g["toks"], m["toks"])
            same = g["ch"] and g["ch"] == m["ch"]
            if not same and jc < 0.34:
                continue
            sc = 2.0 * same + jc + 0.5 * (m["rule_id"].upper().startswith(g["rule_id"].upper())) + 0.25 * (g["debits"] == m["debits"])
            cand.append((sc, i, j))
    used_g, used_m, pairs = set(), set(), []
    for sc, i, j in sorted(cand, reverse=True):
        if i in used_g or j in used_m:
            continue
        used_g.add(i)
        used_m.add(j)
        pairs.append((i, j))
    return pairs


def implied_class(M: list[dict], d: dict, a: int) -> set[str]:
    """Classes the guideline allows given the model's OWN items and net (CLS-3 / 7 / 8)."""
    if any(m["decline"] for m in M):
        return {"Decline"}
    if any(m["postpone"] for m in M):
        return {"Postpone"}
    net = num(d.get("net_debits"))
    tob = str(d.get("ladder")) == "tobacco"
    if net > 25:
        kind, t = table_from_net(net, a)
        return {"Decline"} if kind == "Decline" else {("Table Tobacco" if tob else "Table") + f" {t}"}
    if net > 0:
        return {"Standard Tobacco" if tob else "Standard"}
    return ({"Preferred Tobacco", "Standard Tobacco"} if tob else PREFERRED_SET - {"Preferred Tobacco"} | {"Standard"})


def derived(M: list[dict], d: dict, a: int) -> tuple[str, int, int]:
    """Decision computed in code from the model's OWN items (CLS-3/7/8): (risk class, table, net)."""
    net = sum(m["debits"] - m["credits"] for m in M)
    if any(m["decline"] for m in M):
        return "Decline", 0, net
    if any(m["postpone"] for m in M):
        return "Postpone", 0, net
    tob = str(d.get("ladder")) == "tobacco"
    if net > 25:
        kind, t = table_from_net(net, a)
        return ("Decline", 0, net) if kind == "Decline" else ("Table Tobacco" if tob else "Table", t, net)
    if net > 0:
        return ("Standard Tobacco" if tob else "Standard"), 0, net
    return "<=Std", 0, net


def fe_set(fes) -> list[tuple]:
    out = []
    for f in fes or []:
        if isinstance(f, dict) and f.get("per_thousand"):
            out.append((round(float(f["per_thousand"]), 2), num(f.get("years"), None) if f.get("years") else None))
        elif isinstance(f, tuple):
            out.append((round(float(f[0]), 2), f[1] or None))
    return out


def score(cid: str, output) -> dict:
    g = golden(cid)
    out = parse(output)
    if not out or not isinstance(out.get("decision"), dict):
        return {"case_id": cid, "parsed": 0.0}
    d = out["decision"]
    gd = g.decision
    G, M = golden_items(g), model_items(out)
    pairs = match(G, M)
    r = {"case_id": cid, "parsed": 1.0}
    mlab = label_of(d)
    r["decision"] = float(mlab == gd.label())
    gnet, mnet = gd.net_debits, num(d.get("net_debits"))
    r["coarse"] = float(coarse_of(str(d.get("risk_class")), num(d.get("table"))) == coarse_of(gd.risk_class, gd.table or 0))
    r["band"] = float(mlab in (gd.label(),) or (band(mlab) == band(gd.label()) if mlab else False))
    r["ladder"] = float(str(d.get("ladder")) == str(getattr(gd.ladder, "value", gd.ladder)))
    r["net_abs_err"] = float(abs(mnet - gnet))
    dc, dt, dn = derived(M, d, age(cid))
    gc, gt, gn = derived(G, {"ladder": str(getattr(gd.ladder, "value", gd.ladder))}, age(cid))   # same derivation on golden items
    r["derived_coarse"] = float(coarse_of(dc, dt) == coarse_of(gc, gt))
    r["derived_net_err"] = float(abs(dn - gn))
    nG, nM, nP = len(G), len(M), len(pairs)
    r["item_recall"] = nP / nG if nG else float(nM == 0)
    r["item_precision"] = nP / nM if nM else float(nG == 0)
    pr, rc = r["item_precision"], r["item_recall"]
    r["item_f1"] = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
    if nP:
        r["rule_acc"] = sum(M[j]["rule_id"].upper().startswith(G[i]["rule_id"].upper()) for i, j in pairs) / nP
    r["debit_exact"] = sum(G[i]["debits"] == M[j]["debits"] and G[i]["credits"] == M[j]["credits"] for i, j in pairs) / nG if nG else float(nM == 0)
    r["debit_close"] = sum(abs((G[i]["debits"] - G[i]["credits"]) - (M[j]["debits"] - M[j]["credits"])) <= 25 for i, j in pairs) / nG if nG else float(nM == 0)
    r["arith_ok"] = float(sum(m["debits"] - m["credits"] for m in M) == mnet)
    allowed = implied_class(M, d, age(cid))
    mc = str(d.get("risk_class"))
    r["class_follows"] = float((f"{mc} {num(d.get('table'))}" if mc in ("Table", "Table Tobacco") else mc) in allowed)
    gfe, mfe = fe_set([(f.per_thousand, f.years) for f in gd.flat_extras]), fe_set(d.get("flat_extras"))
    if gfe:
        r["fe_recall"] = sum(f in mfe for f in gfe) / len(gfe)
    if mfe:
        r["fe_precision"] = sum(f in gfe for f in mfe) / len(mfe)
    if gfe or mfe:
        p_, q_ = r.get("fe_precision", 0.0), r.get("fe_recall", 0.0)
        r["fe_f1"] = 2 * p_ * q_ / (p_ + q_) if p_ + q_ else 0.0
    ggry = {x for ga in g.grey_areas for x in ga.rule_ids if x.startswith("GRY")}
    if ggry:
        mg = {str(x).upper() for ga in out.get("grey_areas") or [] if isinstance(ga, dict) for x in ga.get("rule_ids") or []}
        r["grey_recall"] = len(ggry & mg) / len(ggry)
    partial = [toks(s.finding) for s in g.trace if s.rule_id in PARTIAL_UNRATED]
    if partial:
        matched_m = {j for _, j in pairs}
        r["overrate_partial"] = float(any(m["debits"] > 0 and any(jacc(m["toks"], p) >= 0.2 or (m["toks"] and m["toks"] <= p) for p in partial)
                                          for j, m in enumerate(M) if j not in matched_m))
    parts = [r["item_f1"], r["debit_close"], r["arith_ok"], r["class_follows"]] + ([r["fe_f1"]] if "fe_f1" in r else [])
    r["worksheet"] = sum(parts) / len(parts)
    return r


def aggregate(rows: list[dict], keys=None) -> dict:
    keys = keys or ["parsed", "decision", "coarse", "derived_coarse", "band", "ladder", "net_abs_err", "derived_net_err", "item_recall", "item_precision", "item_f1",
                    "rule_acc", "debit_exact", "debit_close", "arith_ok", "class_follows", "fe_recall", "fe_precision",
                    "grey_recall", "overrate_partial", "worksheet"]
    agg = {}
    for k in keys:
        v = [r[k] for r in rows if k in r]
        if v:
            agg[k] = round(sum(v) / len(v), 3)
            agg[f"n_{k}"] = len(v)
    return agg


# --------------------------------------------------------------------------- self-test
def selftest() -> int:
    import copy
    from exp_data import ids
    bad = []
    rows = []
    for cid in ids():
        r = score(cid, json.dumps(golden_output(cid)))
        rows.append(r)
        fails = {k: v for k, v in r.items() if k not in ("case_id", "net_abs_err", "derived_net_err", "overrate_partial") and v != 1.0}
        if fails or r.get("net_abs_err") or r.get("derived_net_err") or r.get("overrate_partial"):
            bad.append((cid, fails))
    print(f"golden-as-output: {len(ids()) - len(bad)}/{len(ids())} score 1.0 on every metric")
    for cid, f in bad[:10]:
        print("  ", cid, f)
    # perturbations on a few rated cases
    cases = [c for c in ids() if len(golden_items(golden(c))) >= 3][:50]
    def mean(f, key):
        v = [score(c, json.dumps(f(c))).get(key, 0) for c in cases]
        return sum(v) / len(v)
    def drop(c):
        o = golden_output(c); o["items"] = o["items"][1:]; return o
    def bump(c):
        o = copy.deepcopy(golden_output(c)); o["items"][0]["debits"] += 50; return o
    def badnet(c):
        o = golden_output(c); o["decision"]["net_debits"] += 25; return o
    def empty(c):
        o = golden_output(c); o["items"] = []; return o
    checks = [("drop first item", drop, "item_recall"), ("+50 on one item", bump, "debit_close"),
              ("net off by 25", badnet, "arith_ok"), ("no items", empty, "worksheet")]
    ok = True
    for name, f, key in checks:
        m = mean(f, key)
        print(f"  perturb {name:18s} -> {key} {m:.3f} (golden 1.000)")
        ok &= m < 1.0
    print("unparseable ->", score(cases[0], "sorry, no JSON"))
    ok &= not bad
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print(__doc__)
