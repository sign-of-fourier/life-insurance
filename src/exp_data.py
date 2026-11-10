"""Phase 7 shared data: splits, slices, scoring labels, and query-side representations.

Query side (what a retriever may see): ONLY data/extracted/<case>.json.
Scoring side (never given to a retriever or model as input): golden + evidence truth_ref, used to judge neighbours.

  python src/exp_data.py      # writes experiments/splits.json and experiments/labels.json, prints slice counts
"""
from __future__ import annotations

import json
import math
import random
import re
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schemas import Golden  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments"
SEEDS = [11, 22, 33]
N_TEST = 200
PARTIAL_RULES = {"APS-6", "RX-2.4", "MIB-4", "APS-3", "GRY-2", "GRY-5", "GRY-6", "GRY-8", "TOB-4.2", "GEN-2.2", "GEN-2.3"}


def ids() -> list[str]:
    return sorted(p.stem for p in (ROOT / "data/golden").glob("C*.json"))


def band(label: str) -> str:
    if label.startswith("Table Tobacco"):
        t = int(label.split()[2])
        return "TT1-4" if t <= 4 else "TT5-16"
    if label.startswith("Table"):
        t = int(label.split()[1])
        return "T1-2" if t <= 2 else "T3-4" if t <= 4 else "T5-8" if t <= 8 else "T9-16"
    return label


def rated(e) -> bool:
    return bool(e.debits or e.class_cap or e.ladder or e.flat_extra or e.postpone_months or e.decline)


# --------------------------------------------------------------------------- scoring labels (golden side)
def case_labels(cid: str) -> dict:
    g = Golden.model_validate_json((ROOT / f"data/golden/{cid}.json").read_text())
    ev = json.loads((ROOT / f"data/source/{cid}/evidence.json").read_text())
    truth = json.loads((ROOT / f"data/truth/{cid}.json").read_text())
    ref = {f["fact_id"]: f.get("truth_ref") for f in ev["facts"]}
    conds = truth["conditions"]
    dropped = set()
    for d in json.loads((ROOT / f"data/extracted/{cid}.json").read_text()):
        for l in d.get("losses", []):
            if l.get("fact_id") and l.get("kind") == "dropped":
                dropped.add(l["fact_id"])
    labels, chapters = set(), Counter()
    partial = set()
    for s in g.trace:
        if s.rule_id in PARTIAL_RULES:
            partial.add(s.rule_id)
        if not rated(s.effect):
            continue
        keys = set()
        for f in s.fact_ids:
            m = re.fullmatch(r"conditions\[(\d+)\]", str(ref.get(f)))
            if m and int(m.group(1)) < len(conds):
                keys.add(conds[int(m.group(1))]["condition_key"])
            if f in dropped:
                partial.add("extraction_dropped")
        ch = re.match(r"[A-Z]+", s.rule_id).group(0)
        labels |= {f"cond:{k}" for k in keys} or {f"ch:{ch}"}
        chapters[ch] += s.effect.debits
    grey = sorted({r for ga in g.grey_areas for r in ga.rule_ids if r.startswith("GRY")})
    if any("MISREP" in s.finding for s in g.trace):
        partial.add("misrep")
    d = g.decision
    return {"labels": sorted(labels), "grey": grey, "partial": sorted(partial), "decision": d.label(), "band": band(d.label()),
            "net": d.net_debits, "chapter_debits": dict(chapters), "ladder": str(getattr(d.ladder, "value", d.ladder)),
            "risk_class": d.risk_class}


@lru_cache(maxsize=1)
def labels() -> dict:
    p = EXP / "labels.json"
    if p.exists():
        return json.loads(p.read_text())
    return {cid: case_labels(cid) for cid in ids()}


def slice_of(lab: dict) -> str:
    return "grey" if lab["grey"] else "partial" if lab["partial"] else "clean"


@lru_cache(maxsize=1)
def splits() -> dict:
    p = EXP / "splits.json"
    if p.exists():
        return json.loads(p.read_text())
    lab, out = labels(), {}
    for seed in SEEDS:
        r = random.Random(seed)
        strata = {}
        for cid in ids():
            strata.setdefault(slice_of(lab[cid]), []).append(cid)
        test = []
        for k, v in sorted(strata.items()):
            v = sorted(v)
            r.shuffle(v)
            test += v[:round(N_TEST * len(v) / len(lab))]
        test = sorted(test[:N_TEST])
        out[str(seed)] = {"test": test, "pool": sorted(set(ids()) - set(test))}
    return out


# --------------------------------------------------------------------------- query-side representations
def extracted(cid: str) -> list[dict]:
    return json.loads((ROOT / f"data/extracted/{cid}.json").read_text())


def doc_texts(cid: str) -> list[str]:
    """One compact text per extracted document (R1 per-document input)."""
    return [f"{d['doc_type']} {d['vendor_schema']}: " + json.dumps(d["payload"], ensure_ascii=False, separators=(",", ":"))
            for d in extracted(cid)]


def case_text(cid: str) -> str:
    """Whole application as one text (R1 whole-case input)."""
    return "\n".join(doc_texts(cid))


NUMRX = re.compile(r"-?\d+(?:\.\d+)?")


def _bin(x: float) -> str:
    return "0" if x == 0 else ("-" if x < 0 else "") + str(round(math.log2(abs(x) + 1e-9) * 2))


def tokens(cid: str) -> list[str]:
    """R2: own simple tokenizer. Leaf path (list indices dropped) + value; codes/drugs stay atomic tokens;
    numbers binned on a half-log2 scale; long free text (APS pages) -> lowercase word tokens prefixed by doc type."""
    out = []

    def walk(dt, path, v):
        if isinstance(v, dict):
            for k, x in v.items():
                walk(dt, f"{path}.{k}" if path else str(k), x)
        elif isinstance(v, list):
            for x in v:
                walk(dt, path, x)
        elif v is None:
            return
        else:
            p = f"{dt}.{path}"
            s = str(v).strip()
            if len(s) > 80:              # free text
                out.extend(f"{dt}~{w}" for w in re.findall(r"[a-z][a-z0-9\-]{2,}", s.lower()))
                return
            out.append(p)
            m = NUMRX.fullmatch(s.split(" ")[0]) if s else None
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append(f"{p}={_bin(float(v))}")
            elif m and not re.fullmatch(r"\d{6}", s):
                out.append(f"{p}={_bin(float(m.group(0)))}")
            else:
                out.append(f"{p}:{s.lower()}")

    for d in extracted(cid):
        walk(d["doc_type"], "", d["payload"])
    return out


def vendors(cid: str) -> set[str]:
    return {d["vendor_schema"] for d in extracted(cid)}


def main():
    EXP.mkdir(exist_ok=True)
    lab = {cid: case_labels(cid) for cid in ids()}
    (EXP / "labels.json").write_text(json.dumps(lab, indent=0))
    labels.cache_clear()
    sp = splits()
    (EXP / "splits.json").write_text(json.dumps(sp, indent=0))
    c = Counter(slice_of(v) for v in lab.values())
    print("slices (all):", dict(c), "| partial reasons:", Counter(p for v in lab.values() for p in v["partial"]).most_common())
    for s, v in sp.items():
        print(f"split {s}: test {len(v['test'])} {dict(Counter(slice_of(lab[x]) for x in v['test']))}, pool {len(v['pool'])}")
    print("labels per case:", sum(len(v["labels"]) for v in lab.values()) / len(lab))


if __name__ == "__main__":
    main()
