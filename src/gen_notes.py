"""Phase 6: noisy underwriter notes from the golden trace.

Pipeline per case (seeded by case id, so re-runs are reproducible; the LLM pass is cached in qa/phase6_notes_llm.jsonl):
  1. persona assignment (reference/uw_personas.yaml)
  2. structural corruptions in code, all logged: omitted steps, unstated assumptions (reason dropped), grey-area
     divergence (persona leniency picks a GreyArea alternative -> different stated decision), wrong final call,
     worksheet arithmetic errors, rider legacy codes
  3. Nova Lite voices the surviving step lines in the persona's style (full words, no new facts; numbers verified,
     retry once, else keep skeleton)
  4. lexical corruptions in code, all logged: tier1/2/3 abbreviations (reference/abbreviations.yaml), tier-3 status
     tags, typos, case style; timestamps per persona habit
  5. worksheet in persona format A-D (code only: arithmetic must be exactly controlled)
Writes data/notes/<case>.json (schemas.Notes) and data/notes/<case>.txt (what a reader sees).

Run:
  python src/gen_notes.py --dry-run [--ids ...]         # cost estimate, no calls
  python src/gen_notes.py --pilot 10 --cap 0.10         # pilot
  python src/gen_notes.py --all --cap 2.0 --workers 6   # full
  python src/gen_notes.py --all --no-llm                # skeleton-only rendering (offline)
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import llm  # noqa: E402
from rules import load, table_from_net  # noqa: E402
from schemas import Corruption, Golden, NoteEntry, Notes  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PERS = load("uw_personas")["personas"]
ABBR = load("abbreviations")
LOG = ROOT / "qa/phase6_notes_llm.jsonl"
MODEL = "lite"
PROMPT_V = 3          # bump when the prompt changes (invalidates the cache)
OUT = ROOT / "data/notes"

CLASS_ABBR = {"Elite": "E", "Preferred Plus": "PP", "Preferred": "Pref", "Standard Plus": "SP", "Standard": "Std",
              "Preferred Tobacco": "PT", "Standard Tobacco": "ST", "Postpone": "PPN", "Decline": "DEC"}
NT_ORDER = ["Elite", "Preferred Plus", "Preferred", "Standard Plus", "Standard"]
T_ORDER = ["Preferred Tobacco", "Standard Tobacco"]
RIDER_ALIAS = {}
for k, v in ABBR["tier3"].items():
    m = re.fullmatch(r"([A-Z][A-Z0-9-]+)(?: \(.*\))?", str(v))
    if m and m.group(1) in {"WP", "WMD", "ADB", "CTR", "GIO", "ABR", "CIA", "XCR", "OIR", "ROP-T", "KPE", "LTA"}:
        RIDER_ALIAS.setdefault(m.group(1), []).append(k)

SYSTEM = ("You rewrite life-insurance underwriting worklog lines in a specific underwriter's personal style for a synthetic "
          "training dataset. You never add facts, numbers, diagnoses, drugs, or decisions that are not in the line, and you "
          "never drop a number, code, or rule id that is in the line. You return JSON only.")


# --------------------------------------------------------------------------- helpers
def rng_for(cid: str, salt: str) -> random.Random:
    return random.Random(zlib.crc32(f"{cid}:{salt}".encode()))


def assign_persona(cid: str) -> str:
    return rng_for(cid, "persona").choice(sorted(PERS))


def stage(s) -> str:
    return str(getattr(s.stage, "value", s.stage))


def label(cls: str, table: int = 0) -> str:
    return f"{cls} {table} (+{25 * table}%)" if cls in ("Table", "Table Tobacco") else cls


def short(lbl: str) -> str:
    m = re.match(r"(Table Tobacco|Table) (\d+)", lbl)
    if m:
        return ("TT" if m.group(1) == "Table Tobacco" else "T") + m.group(2)
    return CLASS_ABBR.get(lbl, lbl)


def rank_list(tob: bool) -> list[str]:
    base = T_ORDER if tob else NT_ORDER
    tt = "Table Tobacco" if tob else "Table"
    return base + [label(tt, t) for t in range(1, 17)] + ["Decline"]


def from_net(net: int, age: int, tob: bool) -> str:
    if net <= 0:
        return ""
    if net <= 25:
        return "Standard Tobacco" if tob else "Standard"
    kind, t = table_from_net(net, age)
    if kind == "Decline":
        return "Decline"
    return label("Table Tobacco" if tob else "Table", t)


def age_of(p1) -> int:
    d, s = date.fromisoformat(p1["dob"]), date.fromisoformat(p1["signed"])
    return s.year - d.year - ((s.month, s.day) < (d.month, d.day))


def effect_short(e) -> str:
    out = []
    if e.debits:
        out.append(f"+{e.debits}")
    if e.credits:
        out.append(f"-{e.credits} credit")
    if e.class_cap:
        out.append(f"cap {e.class_cap}")
    if e.ladder:
        out.append("tobacco ladder")
    if e.flat_extra:
        f = e.flat_extra
        out.append(f"FE {f.per_thousand:g}/" + (f"{f.years}" if f.years else "perm"))
    if e.postpone_months:
        out.append(f"postpone {e.postpone_months} months")
    if e.decline:
        out.append("decline")
    if e.order_requirement:
        out.append(f"order {e.order_requirement}")
    if e.rider_action:
        out.append(f"rider {e.rider_action.code} {e.rider_action.status}")
    return ", ".join(out)


def rated(s) -> bool:
    e = s.effect
    return bool(e.debits or e.credits or e.class_cap or e.ladder or e.flat_extra or e.postpone_months or e.decline)


# --------------------------------------------------------------------------- grey-area divergence
def alt_outcome(g: Golden, ga, age: int) -> tuple[str, int] | None:
    """(stated label, direction) for taking the first alternative; direction +1 more lenient, -1 stricter."""
    d, gl = g.decision, g.decision.label()
    tob = str(getattr(d.ladder, "value", d.ladder)) == "tobacco"
    alt = ga.alternatives[0]
    ranks = rank_list(tob)
    if re.search(r"\bhold\b", alt):
        if d.risk_class == "Decline":
            return None      # already declined on other grounds: holding for records changes nothing
        return ("Incomplete - holding for APS", -1)
    m = re.search(r"([+-])\s?(\d+)", alt)
    if m:
        dn = int(m.group(2)) * (1 if m.group(1) == "+" else -1)
        if d.risk_class in ("Postpone", "Decline"):
            return None
        new = from_net(d.net_debits + dn, age, tob)
        if not new:
            return None
        if new == gl:
            return None
        return (new, 1 if dn < 0 else -1)
    for c in sorted(NT_ORDER, key=len, reverse=True):
        if alt.startswith(c):
            new = (CLS_TOB.get(c, c) if tob else c)
            if new == gl or gl not in ranks or new not in ranks:
                return None
            return (new, 1 if ranks.index(new) < ranks.index(gl) else -1)
    return None


CLS_TOB = load("classes")["tobacco_equivalent"]


# --------------------------------------------------------------------------- lexical corruption
def _abbr_map():
    """meaning phrase -> (tier, [abbrevs]) ; longest phrase first."""
    out = {}
    for tier in ("tier1", "tier2"):
        for k, v in ABBR[tier].items():
            mean, var = (v["m"], v.get("v", [])) if isinstance(v, dict) else (v, [])
            if not isinstance(mean, str) or mean in ("tobacco", "Preferred", "Standard") or "(" in mean or len(mean) < 4 or not re.fullmatch(r"[A-Za-z0-9 '\-/]+", mean):
                continue
            forms = [str(k)] + [str(x) for x in var]
            if tier == "tier2" and len(str(k)) == 1:
                forms = [str(x) for x in var] or [str(k)]
            out.setdefault(mean.lower(), (int(tier[-1]), forms))
    extra2 = {"paramedical exam": ["PM", "para"], "paramed": ["PM", "para"], "attending physician statement": ["APS"],
              "medical records": ["APS"], "non-tobacco": ["NT", "N/T"], "standard plus": ["SP", "S+", "std+"],
              "preferred plus": ["PP", "pref+"], "standard tobacco": ["ST", "std tob"], "preferred tobacco": ["PT", "pref tob"],
              "standard": ["std", "STD"], "preferred": ["pref"], "postpone": ["PPN", "PP'd"], "decline": ["DEC", "DCL", "decl"],
              "flat extra": ["FE", "f/x"], "counter-offer": ["CO", "cntr"], "cotinine": ["cot", "cotin"],
              "urinalysis": ["u/a"], "prescription": ["Rx"], "history": ["hx"], "diagnosis": ["dx"], "treatment": ["tx"],
              "follow-up": ["f/u"], "negative": ["neg"], "positive": ["pos"], "within normal limits": ["WNL"],
              "years": ["yrs", "y"], "months": ["mos", "mo"], "family history": ["FHx", "fam hx"], "debits": ["db", "dbts"],
              "credit": ["cr"], "rider": ["rdr"], "misrepresentation": ["misrep"], "application": ["app"],
              "questionnaire": ["Q", "quest"], "underwriting": ["UW"], "approximately": ["approx", "~"],
              "blood pressure": ["BP"], "build": ["bld"], "ordered": ["ord"], "order": ["ord"], "with": ["w/"],
              "without": ["w/o"], "because": ["b/c", "d/t"], "due to": ["d/t"], "no impact": ["no impact", "NI"]}
    tier_of_extra = {"history", "diagnosis", "treatment", "follow-up", "negative", "positive", "within normal limits",
                     "years", "months", "family history", "prescription", "with", "without", "because", "due to",
                     "blood pressure", "approximately"}
    for k, v in extra2.items():
        out.setdefault(k, (1 if k in tier_of_extra else 2, v))
    return dict(sorted(out.items(), key=lambda x: -len(x[0])))


AMAP = _abbr_map()
APAT = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(k) for k in AMAP) + r")(?![A-Za-z0-9])", re.I)
T3_PHRASE = {r"results in|->": "→", r"\belevated\b": "^", r"\bconfirmed\b": "√", r"\bper\b": "//", r"\blow\b": "vv"}


def abbreviate(text: str, P, r: random.Random, log: list, step) -> str:
    def sub(m):
        tier, forms = AMAP[m.group(0).lower()]
        if r.random() < P["abbrev"][f"t{tier}"]:
            f = r.choice(forms)
            log.append(Corruption(kind=f"abbrev_t{tier}", step=step, detail=f"{m.group(0)} -> {f}"))
            return f
        return m.group(0)
    text = APAT.sub(sub, text)
    for pat, rep in T3_PHRASE.items():
        def sub3(m, rep=rep):
            if r.random() < P["abbrev"]["t3"]:
                log.append(Corruption(kind="abbrev_t3", step=step, detail=f"{m.group(0)} -> {rep}"))
                return rep
            return m.group(0)
        text = re.sub(pat, sub3, text, flags=re.I)
    return text


def t3_tags(s, g, P, r, log) -> list[str]:
    """Tier-3 house/persona shorthand appended to a step line (meaning is only in abbreviations.yaml)."""
    e, f, tags = s.effect, s.finding, []
    cand = []
    if e.no_impact and not e.order_requirement:
        cand.append(r.choice([q for q in P.get("quirks", []) if q in ("nbd", "zz", "nfz")] or ["nfz", "zz", "nbd"]))
    if e.class_cap:
        cand.append(f"cap@{short(e.class_cap)}")
    if e.ladder:
        cand.append("Tlad")
    if e.decline:
        cand.append("k/o-d")
    if e.postpone_months:
        cand.append("k/o-pp")
    if s.rule_id == "RX-2.4":
        cand.append("lsp")
    if s.rule_id in ("GRY-8", "MIB-4") or "not corroborated" in f:
        cand.append("ghost")
    if "stale" in f:
        cand.append("stale")
    if e.order_requirement == "aps":
        cand.append("KTA")
    if "MISREP" in f or "contradict" in f:
        cand.append("Q-flip")
    if "counter-offer" in f or "approve $" in f:
        cand.append("CTO")
    if s.rule_id.startswith("FIN-2") and e.decline:
        cand.append("FTJ")
    if "just over" in f or "borderline" in f.lower():
        cand.append(r.choice(["BL", "BLu", "BLd"] if P["leniency"] == 0 else (["BLd"] if P["leniency"] > 0 else ["BLu"])))
    if "dbl-ck" in P.get("quirks", []) and s.fact_ids and len(s.fact_ids) >= 2 and not e.no_impact:
        cand.append("dbl-ck")
    for c in cand:
        if r.random() < P["abbrev"]["t3"]:
            tags.append(c)
            log.append(Corruption(kind="abbrev_t3", step=s.step, detail=f"tag {c}"))
    return tags


def typo_word(w: str, r: random.Random) -> str:
    i = r.randrange(1, len(w) - 1)
    op = r.choice("swap drop dup".split())
    if op == "swap":
        return w[:i] + w[i + 1] + w[i] + w[i + 2:]
    if op == "drop":
        return w[:i] + w[i + 1:]
    return w[:i] + w[i] + w[i:]


def typos(text: str, P, r, log, step) -> str:
    def sub(m):
        w = m.group(0)
        if r.random() < P["typo"]:
            t = typo_word(w, r)
            log.append(Corruption(kind="typo", step=step, detail=f"{w} -> {t}"))
            return t
        return w
    return re.sub(r"(?<![\w/@#-])[A-Za-z]{5,}(?![\w/@#-])", sub, text)


def casefix(text: str, P, r) -> str:
    c = P["case"]
    if c == "lower":
        return text.lower()
    if c == "upper":
        return text.upper()
    if c == "mixed" and r.random() < 0.35:
        return text.upper()
    return text


def stamp(at, P, r) -> str:
    style = zlib.crc32(P["name"].encode()) % 4
    if style == 0:
        return f"{at.month}/{at.day}"
    if style == 1:
        return f"{at:%m/%d/%y %H:%M}"
    if style == 2:
        return f"{at:%Y-%m-%d}"
    return f"{at.month}/{at.day} {at:%H%M}"


# --------------------------------------------------------------------------- skeleton
def strip_rule(text: str) -> str:
    return re.sub(r"\s*\((?:[A-Z]{2,4}-?\d+(?:\.\d+)*[,/ ]*)+\)", "", text)


class Plan:
    """Structural decisions for one case (no LLM)."""

    def __init__(self, cid: str):
        self.cid = cid
        self.g = Golden.model_validate_json((ROOT / f"data/golden/{cid}.json").read_text())
        self.content = json.loads((ROOT / f"data/source/{cid}/content.json").read_text())
        self.p1 = next(c for c in self.content["docs"].values() if isinstance(c, dict) and "dob" in c and "signed" in c)
        self.age = age_of(self.p1)
        self.pid = assign_persona(cid)
        self.P = PERS[self.pid]
        self.r = rng_for(cid, "notes")
        self.log: list[Corruption] = []
        lost = set()
        for d in json.loads((ROOT / f"data/extracted/{cid}.json").read_text()):
            for l in d.get("losses", []):
                if l.get("fact_id") and l.get("kind") == "dropped":
                    lost.add(l["fact_id"])
        self.lost = lost
        self.build()

    def build(self):
        g, P, r = self.g, self.P, self.r
        self.stated = g.decision.label()
        self.diverge = None
        for ga in g.grey_areas:
            alt = alt_outcome(g, ga, self.age)
            if not alt:
                continue
            lab, direction = alt
            lv = P["leniency"]
            p = min(0.9, max(0.04, 0.15 + 0.6 * lv * direction))
            if r.random() < p:
                self.diverge = (ga, lab)
                self.stated = lab
                self.log.append(Corruption(kind="grey_divergence", detail=f"{ga.issue}: chose '{ga.alternatives[0]}' instead of "
                                           f"'{ga.chosen}' -> stated {lab} (golden {g.decision.label()}; "
                                           f"{'more lenient' if direction > 0 else 'stricter'})"))
                break
        self.lines = []          # (step, text) to be voiced
        for s in g.trace:
            st = stage(s)
            if st == "final" and not rated(s) and not s.effect.rider_action:
                continue         # restated in worksheet
            imp = rated(s) or s.effect.order_requirement or s.effect.rider_action
            boiler = s.effect.no_impact and re.match(r"(Remaining|Pulse/other|Routine visit|Acute/low|US citizen|EKG normal)", s.finding)
            p_omit = P["omit"] * 0.25 if imp else (0.45 + P["omit"] if boiler else 0.1 + P["omit"])
            if s.effect.decline or s.effect.postpone_months:
                p_omit = 0
            if r.random() < p_omit:
                self.log.append(Corruption(kind="omitted_step", step=s.step, detail=f"not written: {s.finding[:90]}"))
                continue
            txt = s.finding
            if r.random() > P["cite_rules"]:
                txt = strip_rule(txt)
            else:
                txt = f"{txt} [{s.rule_id}]"
            eff = effect_short(s.effect)
            if rated(s) and r.random() < P["omit"] * 0.6:
                txt = re.split(r"[:;(]", s.finding)[0].strip() + (f" {eff}" if eff else "")
                self.log.append(Corruption(kind="unstated_assumption", step=s.step,
                                           detail=f"reasoning dropped, only result written: '{txt[:80]}'"))
            elif eff and eff not in txt and not (s.effect.order_requirement and s.finding.startswith("Order")) and not s.effect.rider_action:
                txt += f" => {eff}"
            if self.diverge and s.rule_id in self.diverge[0].rule_ids:
                txt += f" | going with: {self.diverge[0].alternatives[0]}"
            for fid in s.fact_ids:
                if fid in self.lost:
                    self.log.append(Corruption(kind="fact_not_in_extraction", step=s.step, fact_id=fid,
                                               detail="note relies on a fact the extracted JSON dropped (UW read the source doc)"))
            self.lines.append((s, txt))
        if self.diverge and not any(self.diverge[0].alternatives[0] in t for _, t in self.lines):
            fs = next((s for s in reversed(g.trace) if stage(s) == "final"), g.trace[-1])
            self.lines.append((fs, f"{self.diverge[0].issue} - going with: {self.diverge[0].alternatives[0]}"))
        # wrong final (no grey basis)
        self.ws_net = g.decision.net_debits
        if not self.diverge and r.random() < P["wrong_final"]:
            self._wrong_final("persona slip: picked the adjacent class/table")
        # arithmetic error in the worksheet total
        self.arith = None
        rated_steps = [s for s in g.trace if s.effect.debits or s.effect.credits]
        if len(rated_steps) >= 2 and r.random() < P["arith_err"] * 4:
            delta = r.choice([-25, 25, -10, 10])
            self.arith = delta
            self.ws_net = g.decision.net_debits + delta
            self.log.append(Corruption(kind="arithmetic_error", detail=f"worksheet total written {self.ws_net:+d}, true {g.decision.net_debits:+d}"))
            if not self.diverge and self.stated == g.decision.label() and r.random() < 0.5 and g.decision.risk_class not in ("Postpone", "Decline"):
                tob = str(getattr(g.decision.ladder, "value", g.decision.ladder)) == "tobacco"
                new = from_net(self.ws_net, self.age, tob)
                if new and new != self.stated and g.decision.net_debits > 0:
                    self.stated = new
                    self.log.append(Corruption(kind="wrong_final", detail=f"class carried from wrong total -> {new} (golden {g.decision.label()})"))

    def _wrong_final(self, why):
        g = self.g
        if g.decision.risk_class == "Postpone":
            return
        tob = str(getattr(g.decision.ladder, "value", g.decision.ladder)) == "tobacco"
        ranks = rank_list(tob)
        gl = g.decision.label()
        if gl not in ranks:
            return
        i = ranks.index(gl)
        j = max(0, min(len(ranks) - 1, i + self.r.choice([-1, 1])))
        if j == i:
            return
        self.stated = ranks[j]
        self.log.append(Corruption(kind="wrong_final", detail=f"{why}: stated {ranks[j]} (golden {gl})"))


# --------------------------------------------------------------------------- entries + LLM voice
def group_entries(plan: Plan):
    """[(at, [(step, text)])] per persona timestamp habit."""
    P, groups = plan.P, []
    for s, t in plan.lines:
        key = (stage(s), s.at.date())
        if groups and groups[-1][0] == key:
            groups[-1][2].append((s, t))
            groups[-1][1] = max(groups[-1][1], s.at)
        else:
            groups.append([key, s.at, [(s, t)]])
    if P["entries"] == "batch" and len(groups) > 2:
        cut = max(1, len(groups) // 2)
        groups = [[g0[0], max(x[1] for x in grp), [y for x in grp for y in x[2]]] for g0, grp in
                  ((groups[0], groups[:cut]), (groups[cut], groups[cut:]))]
    elif P["entries"] == "final_only" and groups:
        groups = [[groups[-1][0], max(x[1] for x in groups), [y for x in groups for y in x[2]]]]
    # write time: a little after the evidence arrived
    out, prev = [], None
    for _, at, items in groups:
        w = at + timedelta(minutes=plan.r.randint(5, 240))
        if prev and w <= prev:
            w = prev + timedelta(minutes=plan.r.randint(3, 40))
        out.append((w, items))
        prev = w
    return out


def prompt_for(plan: Plan, entries) -> str:
    P = plan.P
    lines = []
    for ei, (_, items) in enumerate(entries):
        for li, (s, t) in enumerate(items):
            lines.append({"id": f"{ei}.{li}", "text": t})
    sent = P["sentences"]
    style = ("mostly full sentences" if sent >= 0.7 else "a mix of short sentences and fragments" if sent >= 0.35 else
             "almost entirely terse fragments, dropping articles and verbs")
    cap = 22 if sent >= 0.7 else 13 if sent >= 0.35 else 8
    style += f". HARD LIMIT: at most {cap} words per line (bracketed rule ids, codes and numbers do not count)"
    return (f"Underwriter: {P['name']}, {P['level']}, {P['years']} years. Voice: {P['voice']}. Write in {style}.\n"
            "Rewrite each worklog line below in this underwriter's voice as quick personal notes to self.\n"
            "Rules:\n- Keep EVERY number, date, dollar amount, MIB code, drug name and bracketed rule id exactly as given.\n"
            "- Do not add any fact, number, or conclusion that is not in the line. Do not merge or reorder lines.\n"
            "- Keep every +/- debit or credit, dollar amount, 6-digit MIB code and bracketed rule id. Other numbers "
            "(dates, lab values, counts) may be dropped if this underwriter would not bother writing them.\n"
            "- Use full words (do not invent abbreviations; abbreviations are applied later).\n"
            "- Compress like a busy underwriter: drop boilerplate ('reviewed', 'per guideline', 'no impact' explanations), "
            "keep the clinical gist and the result. Vary phrasing; never copy the input wording - restate it the way this person "
            "would jot it in a worklog.\n"
            "Examples of the same line at different terseness:\n"
            "  in: 'Rx metformin x12 (endocrinology) consistent with disclosed type 2 diabetes. [RX-2.2]'\n"
            "  full: 'Pharmacy shows metformin, twelve fills from endocrinology - matches the diabetes on the app. [RX-2.2]'\n"
            "  terse: 'metformin fills match diabetes disclosure [RX-2.2]'\n"
            "  in: 'Build 5\'9\" 214 lb (measured), BMI 31.6: Standard column. => cap Standard'\n"
            "  terse: 'build 5\'9/214 lands standard column => cap Standard'\n"
            '- Return JSON only: {"<id>": "<rewritten line>", ...} with every id.\n\n'
            + json.dumps(lines, ensure_ascii=False))


NUM = re.compile(r"\d+(?:\.\d+)?")


def numset(t: str) -> set[str]:
    out = set()
    for n in NUM.findall(t.replace(",", "")):
        out.add(n.lstrip("0") or "0")
    return out


def must_numbers(src: str) -> set[str]:
    """Numbers the voiced line must keep: effect values after '=>', debit/credit signs, MIB codes, dollar amounts."""
    keep = set()
    if "=>" in src:
        keep |= numset(src.split("=>", 1)[1])
    keep |= {n.lstrip("0") or "0" for n in re.findall(r"(?<![A-Za-z0-9.])[+-](\d+)\b", src)}
    keep |= set(re.findall(r"\b(\d{6})\b", src))
    keep |= numset(" ".join(re.findall(r"\$[\d,]+", src)))
    return keep


def verify(src: str, out: str) -> list[str]:
    a, b = numset(src), numset(out)
    issues = [f"missing number {n}" for n in sorted(must_numbers(src) - b)]
    yrs = {str(int(n) % 100) for n in a if n.isdigit() and len(n) == 4} | {n[-2:] for n in a if n.isdigit() and len(n) == 4}
    extra = {n for n in b - a if n not in yrs}
    issues += [f"new number {n}" for n in sorted(extra)]
    for code in re.findall(r"\[[A-Z]{2,4}-?[\d.]*\]", src):
        if code not in out:
            issues.append(f"missing {code}")
    return issues


def cached():
    out = {}
    if LOG.exists():
        for ln in LOG.read_text().splitlines():
            x = json.loads(ln)
            out[x["case_id"]] = x
    return out


def voice(plan: Plan, entries, budget, use_llm=True, cache=None):
    """Return {id: text} voiced lines (verified), and a record for the log."""
    src = {f"{ei}.{li}": t for ei, (_, items) in enumerate(entries) for li, (_, t) in enumerate(items)}
    if not use_llm:
        return src, None
    c = (cache or {}).get(plan.cid)
    if c and c.get("src") == src and c.get("v") == PROMPT_V:
        return c["out"], None
    p = prompt_for(plan, entries)
    res, issues_all, ok = dict(src), {}, 0
    for attempt in range(2):
        todo = {k: v for k, v in src.items() if k not in issues_all or issues_all[k]} if attempt else src
        if not todo:
            break
        pp = p if attempt == 0 else p + f"\n\nThese lines had problems last time; fix them: {json.dumps({k: issues_all[k] for k in todo})}"
        try:
            raw = llm.call(MODEL, SYSTEM, pp, max_tokens=min(4000, 200 + 90 * len(src)), temperature=0.8, budget=budget,
                           tag=f"notes:{plan.cid}")
        except llm.BudgetExceeded:
            raise
        except Exception as e:  # noqa: BLE001
            print(plan.cid, "call failed", e)
            break
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            got = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            got = {}
        for k in todo:
            v = got.get(k)
            iss = verify(src[k], v) if isinstance(v, str) and v.strip() else ["missing line"]
            issues_all[k] = iss
            if not iss:
                res[k] = v.strip()
    ok = sum(1 for k in src if issues_all.get(k) == [])
    rec = {"case_id": plan.cid, "v": PROMPT_V, "persona": plan.pid, "src": src, "out": res, "voiced": ok, "lines": len(src),
           "fallback": [k for k in src if issues_all.get(k) != []]}
    return res, rec


# --------------------------------------------------------------------------- worksheet
def worksheet(plan: Plan) -> str:
    g, P, r = plan.g, plan.P, plan.r
    d = g.decision
    items = [s for s in g.trace if s.effect.debits or s.effect.credits]
    caps = [s for s in g.trace if s.effect.class_cap]
    fes = d.flat_extras
    omitted = {c.step for c in plan.log if c.kind == "omitted_step"}
    cite = lambda s: (f" {s.rule_id}" if r.random() < P["cite_rules"] else "")  # noqa: E731
    name = lambda s: re.split(r"[:;(]", s.finding)[0].strip()[:48]  # noqa: E731
    val = lambda s: (f"+{s.effect.debits}" if s.effect.debits else "") + (f" -{s.effect.credits}" if s.effect.credits else "")  # noqa: E731
    final = short(plan.stated) if not plan.stated.startswith("Incomplete") else "PEND-R"
    net = plan.ws_net
    riders = [f"{rc.code if r.random() > P['abbrev']['t3'] or rc.code not in RIDER_ALIAS else plan_alias(plan, rc.code)} "
              f"{'ok' if rc.status == 'approved' else 'dcl'}" for rc in d.riders]
    fe_txt = ["FE " + f"{f.per_thousand:g}/" + (str(f.years) if f.years else "perm") for f in fes]
    fmt = P["worksheet"]
    L = []
    if fmt == "A":
        L.append("ITEM | RULE | DB")
        for s in items:
            L.append(f"{name(s)} |{cite(s) or ' -'} | {val(s)}")
        for s in caps:
            L.append(f"{name(s)} |{cite(s) or ' -'} | cap {short(s.effect.class_cap)}")
        L.append(f"TOTAL | | {net:+d}")
        if fe_txt:
            L.append("FE | | " + "; ".join(fe_txt))
        if riders:
            L.append("RIDERS | | " + ", ".join(riders))
        L.append(f"CLASS | | {final}")
    elif fmt == "B":
        for s in items:
            L.append(f"{name(s)} {val(s)}")
        for s in caps:
            L.append(f"{name(s)} → cap {short(s.effect.class_cap)}")
        L.append(f"= {net:+d} → {final}" + (" + " + ", ".join(fe_txt) if fe_txt else ""))
        if riders:
            L.append("rdrs: " + ", ".join(riders))
    elif fmt == "C":
        parts = [f"{name(s).split(' ')[0].lower()} {val(s)}" for s in items]
        L.append((", ".join(parts) or "no debits") + f" = {net:+d}" + (f" so {final}" if parts else f", {final}"))
        if caps:
            L.append("capped " + ", ".join(short(s.effect.class_cap) for s in caps) + " from " +
                     ", ".join(name(s).split(' ')[0].lower() for s in caps))
        if fe_txt:
            L.append("plus " + ", ".join(fe_txt))
        if riders:
            L.append("riders " + ", ".join(riders))
    else:  # D checklist_partial
        steps = load("classes")["worksheet_steps"]
        for i, st in enumerate(steps, 1):
            nm = (st if isinstance(st, str) else st.get("name", str(st))).replace("_", " ")
            blank = r.random() < P["omit"] * 1.5
            if i == len(steps):
                L.append(f"[x] {i}. {nm}: {final}")
            elif blank:
                L.append(f"[ ] {i}. {nm}:")
            else:
                L.append(f"[x] {i}. {nm}")
        L.append("debits: " + (" ".join(val(s) for s in items) or "none") + f" -> net {net:+d}")
        if fe_txt:
            L.append("FE: " + "; ".join(fe_txt))
        if riders:
            L.append("riders: " + ", ".join(riders))
    if d.approved_face_amount:
        L.append(f"CTO ${d.approved_face_amount // 1000}K" if r.random() < P["abbrev"]["t3"] else f"counter-offer ${d.approved_face_amount:,}")
    if d.postpone_months and plan.stated == "Postpone":
        L.append(f"PPN {d.postpone_months} mos")
    if any(s.step in omitted for s in items):
        pass
    return "\n".join(L)


def plan_alias(plan: Plan, code: str) -> str:
    a = plan.r.choice(RIDER_ALIAS[code])
    plan.log.append(Corruption(kind="rider_code", detail=f"{code} written as legacy/house code '{a}'"))
    return a


# --------------------------------------------------------------------------- assemble
def build_notes(cid: str, budget=None, use_llm=True, cache=None):
    plan = Plan(cid)
    entries = group_entries(plan)
    voiced, rec = voice(plan, entries, budget, use_llm, cache)
    r, P = plan.r, plan.P
    obs = []
    for ei, (at, items) in enumerate(entries):
        out = []
        for li, (s, _) in enumerate(items):
            t = voiced[f"{ei}.{li}"]
            t = re.sub(r"\s*\[(?![A-Z]{2,4}(?:-\d+(?:\.\d+)*)?\])[^\]]*\]", "", t).strip()
            src_t = [x for x in items][li][1]
            dropped = sorted(numset(src_t) - numset(t))
            if dropped:
                plan.log.append(Corruption(kind="fragment", step=s.step, detail=f"values not written: {', '.join(dropped[:8])}"))
            t = abbreviate(t, P, r, plan.log, s.step)
            tags = t3_tags(s, plan.g, P, r, plan.log)
            if tags:
                t += " " + " ".join(tags)
            t = typos(t, P, r, plan.log, s.step)
            out.append(casefix(t, P, r))
        sep = "\n" if P["sentences"] >= 0.5 else (" / " if P["entries"] != "per_doc" else "; ")
        obs.append(NoteEntry(at=at, text=f"{stamp(at, P, r)} " + sep.join(out)))
    ws = worksheet(plan)
    ws = casefix(ws, P, r) if P["case"] != "mixed" else ws
    n = Notes(case_id=cid, persona_id=plan.pid, observations=obs, worksheet_format=P["worksheet"], worksheet=ws,
              stated_decision=plan.stated, corruptions=plan.log)
    return n, rec


def write(n: Notes):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{n.case_id}.json").write_text(n.model_dump_json(indent=1))
    P = PERS[n.persona_id]
    txt = [f"UW: {P['name']}"] + [e.text for e in n.observations] + ["", "--- worksheet ---", n.worksheet]
    (OUT / f"{n.case_id}.txt").write_text("\n".join(txt) + "\n")


def all_ids():
    return sorted(p.stem for p in (ROOT / "data/golden").glob("C*.json"))


def estimate(ids):
    tin = tout = 0
    for cid in ids:
        plan = Plan(cid)
        e = group_entries(plan)
        p = prompt_for(plan, e)
        n = sum(len(x[1]) for x in e)
        tin += llm.est_tokens(SYSTEM + p)
        tout += 25 * n + 30
    return tin, tout, llm.cost(MODEL, tin, tout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--cap", type=float, default=0.25)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    ids = all_ids()
    if a.ids:
        ids = [i for i in ids if i in set(a.ids.split(","))]
    elif a.pilot:
        ids = random.Random(6).sample(ids, a.pilot)
    elif not (a.all or a.dry_run):
        ap.error("choose --ids, --pilot N, --all or --dry-run")
    if a.dry_run:
        tin, tout, usd = estimate(ids)
        print(f"{len(ids)} cases: ~{tin} in / ~{tout} out tokens on {MODEL} -> ${usd:.3f} (x2 retry worst ${2 * usd:.3f})")
        return
    cache = cached()
    if a.no_llm:
        for cid in ids:
            write(build_notes(cid, use_llm=False)[0])
        print(f"wrote {len(ids)} skeleton notes")
        return
    stats = {"voiced": 0, "lines": 0}
    with llm.Budget(f"phase6-notes-{len(ids)}", cap=a.cap) as b:
        def one(cid):
            n, rec = build_notes(cid, b, True, cache)
            write(n)
            if rec:
                with llm.LOCK:
                    with LOG.open("a") as f:
                        f.write(json.dumps(rec) + "\n")
                    stats["voiced"] += rec["voiced"]
                    stats["lines"] += rec["lines"]
            return cid
        with ThreadPoolExecutor(a.workers) as ex:
            for i, _ in enumerate(ex.map(one, ids), 1):
                if i % 50 == 0:
                    print(f"{i}/{len(ids)} spent ${b.spent:.3f}", flush=True)
        print(f"done {len(ids)}; lines voiced {stats['voiced']}/{stats['lines']}; batch spend ${b.spent:.3f}")


if __name__ == "__main__":
    main()
