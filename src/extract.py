"""Phase 4d: source documents -> noisy vendor-specific extracted JSON (the downstream model's view).

We pretend to sit after an OCR/LangChain extraction step. Payload shape differs per vendor (json_schema in vendors.yaml).
Noise per field from vendors.yaml ocr_noise[category] (APS scaled by aps_style ocr multiplier). Every loss is logged as
schemas.ExtractionLoss with the fact_id it damaged. APS: noisy page text + partial entity list.
Run: python src/extract.py [--ids ...]    -> data/extracted/<case>.json  (list of ExtractedDoc)
"""
from __future__ import annotations

import argparse
import json
import random
import zlib
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render import LAB_NAMES, REF, SI, _ints  # noqa: E402
from rules import load  # noqa: E402
from schemas import ExtractedDoc, ExtractionLoss  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VEND = load("vendors")
NOISE = VEND["ocr_noise"]
CONF = NOISE["digit_confusions"]
CAT = {"app_part1": "app", "app_part2": "app", "rx": "rx", "mib": "mib", "mvr": "mvr", "paramed": "paramed", "lab_blood": "lab",
       "lab_urine": "lab", "lab_saliva": "lab", "ekg": "default", "other": "default", "aps": "aps"}


class Noiser:
    def __init__(self, seed, cat, mult=1.0):
        self.r = random.Random(seed)
        self.p = {**NOISE["default"], **NOISE.get(cat, {})}
        self.p = {k: min(0.9, v * mult) for k, v in self.p.items()}
        self.losses: list[ExtractionLoss] = []

    def hit(self, kind):
        return self.r.random() < self.p.get(kind, 0)

    def log(self, kind, fid, orig, ext):
        self.losses.append(ExtractionLoss(fact_id=fid, kind=kind, original=None if orig is None else str(orig)[:200],
                                          extracted=None if ext is None else str(ext)[:200]))

    def misread(self, s: str) -> str:
        digs = [i for i, ch in enumerate(s) if ch in CONF]
        if not digs:
            return s
        i = self.r.choice(digs)
        return s[:i] + self.r.choice(CONF[s[i]]) + s[i + 1:]

    def val(self, v, fid=None, unit=None):
        """apply value-level noise; returns (value, unit, dropped?)"""
        if self.hit("dropped"):
            self.log("dropped", fid, v, None)
            return None, unit, True
        sv = str(v)
        if any(ch.isdigit() for ch in sv) and self.hit("misread_digit"):
            nv = self.misread(sv)
            self.log("misread_digit", fid, sv, nv)
            sv = nv
        if unit and self.hit("unit_lost"):
            self.log("unit_lost", fid, unit, None)
            unit = None
        elif unit and self.hit("unit_wrong"):
            nu = self.r.choice(["mg/L", "mmol/L", "g/L", "%", "U/mL"])
            self.log("unit_wrong", fid, unit, nu)
            unit = nu
        out = sv
        if isinstance(v, (int, float)) and not isinstance(v, bool) and sv == str(v):
            out = v
        return out, unit, False

    def date(self, s, fid=None, dayfirst=False):
        if dayfirst and self.hit("date_garbled") * 0 + (self.r.random() < 0.25):   # day-first misparsed as month-first
            d = date.fromisoformat(s[:10])
            if d.day <= 12:
                g = f"{d.year}-{d.day:02d}-{d.month:02d}"
                self.log("date_garbled", fid, s, g)
                return g
        if self.hit("date_garbled"):
            g = self.misread(s)
            self.log("date_garbled", fid, s, g)
            return g
        return s


def fidx(facts, doc_id):
    idx = {}
    for f in facts:
        if f["doc_id"] == doc_id:
            idx.setdefault(f["key"], f["fact_id"])
    return idx


# --------------------------------------------------------------------------------------------- per-type extractors
def x_app(d, c, n, fx):
    if d["doc_type"] == "app_part1":
        fields = {k: c[k] for k in ("name", "sex", "dob", "state", "country", "citizenship", "years_in_us", "visa", "occupation", "income",
                                    "net_worth", "face", "product", "riders", "existing", "replacement", "beneficiary", "signed")}
        out = {}
        for k, v in fields.items():
            nv, _, drop = n.val(v, fx.get({"income": "income", "face": "face"}.get(k, k)))
            if not drop:
                out[k] = nv
        return {"section_1": out} if c["form"] == "APP-2019" else {"applicant": out}
    med = {}
    for q, num in c["numbering"].items():
        a = c["answers"][q]
        fid = next((v for k, v in fx.items() if k == q or k.startswith(q + ":")), None)
        ans, _, drop = n.val(a["answer"], fid)
        if drop:
            continue
        ent = {"q": num, "a": ans}
        if a.get("details"):
            det = a["details"] if isinstance(a["details"], list) else [a["details"]]
            ent["details"] = [json.dumps(x) if isinstance(x, dict) else x for x in det]
            if n.hit("merged_cells") and len(ent["details"]) > 1:
                ent["details"] = [" ".join(ent["details"])]
                n.log("merged_cells", fid, "multiple details", "merged")
        med[num] = ent
    return {"part2": med} if c["form"] == "APP-2019" else {"medical": med}


def x_rx(d, c, n, fx):
    if c["no_history"]:
        return {"result": "NO HISTORY"}
    if c["vendor"] == "SCR":
        rows = []
        for f in c["fills"]:
            for dd in f["fills"]:
                drug, _, drop = n.val(f["drug"].upper(), fx.get(f["drug"]))
                if drop:
                    continue
                rows.append({"date": n.date(dd, fx.get(f["drug"])), "drug": drug, "strength": f["strength"], "days": f["days_supply"],
                             "prescriber": f["prescriber"], "spec": f["specialty"]})
        return {"fills": rows}
    meds = []
    for f in c["fills"]:
        prod = f"{f['brand'].split(' / ')[0].upper()} {f['strength'].upper().replace(' ', '')}"
        prod, _, drop = n.val(prod, fx.get(f["drug"]))
        if drop:
            continue
        meds.append({"product": prod, "first": f["fills"][0], "last": f["fills"][-1], "count": len(f["fills"]), "prescriber": f["prescriber"]})
    return {"medications": meds}


def x_mib(d, c, n, fx):
    codes = []
    for cd in c["codes"]:
        code, _, drop = n.val(cd["code"], fx.get(cd["code"]))
        if drop:
            continue
        codes.append({"code": code, "date": cd["reported"]} if c["vendor"] == "MIBF" else {"code": code, "yr": cd["reported"][:4]})
    return {"codes": codes} if c["vendor"] == "MIBF" else {"hits": len(c["codes"]), "codes": codes}


def x_mvr(d, c, n, fx):
    if c.get("foreign_license"):
        return {"status": "NO US LICENSE"}
    rows = []
    for e in c["events"]:
        fid = fx.get(e["code"])
        if n.hit("dropped"):
            n.log("dropped", fid, e["code"], None)
            continue
        if c["vendor"] == "ACD":
            rows.append({"viol_date": n.date(e["date"], fid), "code": e["code"], "desc": e["desc"]})
        else:
            rows.append({"dt": e["date"].replace("-", "")[2:], "text": e["desc"].upper()[:28]})   # statute-style; code must be inferred
    return {"license_status": c["status"], "violations" if c["vendor"] == "ACD" else "record": rows}


def x_paramed(d, c, n, fx):
    if c["vendor"] == "PMX":
        h, _, _ = n.val(f"{int(c['height_in'] // 12)}'{c['height_in'] % 12:g}\"", fx.get("build"))
        w, _, _ = n.val(c["weight_lb"], fx.get("build"))
        bps = []
        for s, dd in c["bp"]:
            v, _, drop = n.val(f"{s}/{dd}", fx.get("bp"))
            if not drop:
                bps.append(v)
        return {"height": h, "weight_lbs": w, "bp": bps, "pulse": c["pulse"], "remarks": [f"{k}: {v}" for k, v in c["examiner_notes"].items()]}
    out = {"HT_IN": c["height_in"], "WT_KG": round(c["weight_lb"] / 2.2046, 1), "HR": c["pulse"]}
    for i, (s, dd) in enumerate(c["bp"]):
        v, _, drop = n.val(f"{s}/{dd}", fx.get("bp"))
        if not drop:
            out[f"BP_{i + 1}"] = v
    return out


def x_lab(d, c, n, fx):
    v = c["vendor"] if d["doc_type"] != "lab_saliva" or c["vendor"] != "NGL" else "MIL"
    res = c["results"]
    units = {k: load("labs")["analytes"].get(k, {}).get("unit") for k in res}
    if v == "APX":
        out = {}
        items = dict(res)
        if {"tc", "hdl", "tc_hdl_ratio"} <= set(items):
            s = f"{items.pop('tc')}/{items.pop('hdl')}/{items.pop('tc_hdl_ratio')}"
            nv, _, drop = n.val(s, fx.get("tc"))
            if not drop:
                out["CHOL/HDL/RATIO"] = nv
        if {"ast", "alt"} <= set(items):
            nv, _, drop = n.val(f"{items.pop('ast')}/{items.pop('alt')}", fx.get("ast"))
            if not drop:
                out["AST/ALT"] = nv
        for k, val in items.items():
            nv, u, drop = n.val(val, fx.get(k), units.get(k))
            if not drop:
                out[VEND["lab_vendors"]["APX"]["aliases"].get(k, LAB_NAMES.get(k, k)).upper()] = nv if u is None else f"{nv} {u}"
        return {"collected": c["collected"], **out}
    if v == "NGL":
        tests = []
        for k, val in res.items():
            if k == "tc_hdl_ratio":
                continue
            unit, disp = units.get(k), val
            if k in SI:
                unit, f = SI[k]
                disp = round(val * f, 2 if f < 1 else 0)
            if k == "a1c":
                unit, disp = "mmol/mol", round((val - 2.15) * 10.929)
            nv, u, drop = n.val(disp, fx.get(k), unit)
            if drop:
                continue
            ent = {"name": VEND["lab_vendors"]["NGL"]["aliases"].get(k, LAB_NAMES.get(k, k)), "result": nv, "unit": u}
            lo, hi = REF.get(k, (None, None))
            if hi is not None and k not in SI and k != "a1c" and isinstance(val, (int, float)) and val > hi:
                if n.hit("flag_lost"):
                    n.log("flag_lost", fx.get(k), "↑", None)
                else:
                    ent["ind"] = "↑"
            tests.append(ent)
        return {"collected": n.date(c["collected"], None, dayfirst=True), "tests": tests}
    results = []
    for k, val in res.items():
        nv, u, drop = n.val(val, fx.get(k), units.get(k))
        if drop:
            continue
        lo, hi = REF.get(k, (None, None))
        flag = "" if lo is None or not isinstance(val, (int, float)) else ("H" if val > hi else "L" if val < lo else "")
        if flag and n.hit("flag_lost"):
            n.log("flag_lost", fx.get(k), flag, None)
            flag = ""
        ent = {"test": VEND["lab_vendors"]["MIL"]["aliases"].get(k, LAB_NAMES.get(k, k)), "value": nv, "flag": flag, "units": u}
        if lo is not None:
            ent["ref"] = f"{lo}-{hi}"
        if n.hit("merged_cells") and results:
            results[-1]["value"] = f"{results[-1]['value']} {nv}"
            n.log("merged_cells", fx.get(k), f"{k}={val}", "merged into previous row")
            continue
        results.append(ent)
    return {"collected": c["collected"], "results": results}


def x_ekg(d, c, n, fx):
    v, _, _ = n.val(c["interpretation"], fx.get("interpretation"))
    return {"interp": v, "rate": c["rate"]}


def x_other(d, c, n, fx):
    out = {}
    for k, v in c.items():
        if k == "type":
            continue
        nv, _, drop = n.val(json.dumps(v, default=str) if isinstance(v, (list, dict)) else v, fx.get(f"{c['type']}:{k}"))
        if not drop:
            out[k] = nv
    return {"form": c["type"], "fields": out}


def x_aps(d, c, n, fx, text, facts):
    pages = [text[i:i + 2600] for i in range(0, len(text), 2600)] or [""]
    out_pages = []
    lost_text = []
    for i, pg in enumerate(pages):
        if i > 0 and n.hit("truncated_page"):
            n.log("truncated_page", None, f"page {i + 1}", None)
            lost_text.append(pg)
            continue
        words = pg.split(" ")
        for j in range(len(words)):
            if any(ch.isdigit() for ch in words[j]) and n.r.random() < n.p["misread_digit"]:
                words[j] = n.misread(words[j])
            elif n.r.random() < n.p["dropped"] * 0.3:
                words[j] = ""
        pg2 = " ".join(w for w in words if w != "")
        if n.hit("header_noise"):
            pg2 = f"{n.r.choice(['RECEIVED', 'FAX', 'Page'])} {n.r.randint(1, 30)}  {n.r.choice(['-- ROI --', 'CONFIDENTIAL', '##'])}\n" + pg2
        out_pages.append({"page": i + 1, "text": pg2})
    kept = "\n".join(p["text"] for p in out_pages).lower()
    # entity extraction (LangChain-style), partial
    ents = []
    for p in c["problems"]:
        if n.r.random() < 0.85:
            ents.append({"type": "diagnosis", "text": p["dx"], "status": p["status"]})
        for m in p["meds"]:
            if n.r.random() < 0.7:
                ents.append({"type": "medication", "text": m})
    # facts whose evidence was lost: dx label / numeric values not present in kept text
    for f in facts:
        if f["doc_id"] != d["doc_id"] or f["kind"] != "aps_finding":
            continue
        probe = []
        v = f["value"]
        if isinstance(v, dict):
            probe = [str(x) for k, x in v.items() if isinstance(x, (int, float)) and not isinstance(x, bool) and k not in ("cond_index",)]
        elif isinstance(v, list):
            probe = [str(x.get("value")) for x in v if isinstance(x, dict)]
        probe = [p for p in probe if len(p) >= 2]
        if probe and not any(p.lower() in kept for p in probe):
            in_lost = any(any(p in lt for p in probe) for lt in lost_text)
            n.log("truncated_page" if in_lost else "dropped", f["fact_id"], probe[0], None)
    return {"provider": c["provider"]["name"], "specialty": c["provider"]["specialty"], "page_count": len(pages), "pages": out_pages, "entities": ents}


SCHEMA = {"app_part1": lambda d, c: VEND["app_forms"][c["form"]]["json_schema"], "app_part2": lambda d, c: VEND["app_forms"][c["form"]]["json_schema"],
          "rx": lambda d, c: VEND["rx_vendors"][c["vendor"]]["json_schema"], "mib": lambda d, c: VEND["mib_layouts"][c["vendor"]]["json_schema"],
          "mvr": lambda d, c: VEND["mvr_layouts"][c["vendor"]]["json_schema"], "paramed": lambda d, c: VEND["paramed_vendors"][c["vendor"]]["json_schema"],
          "lab_blood": lambda d, c: VEND["lab_vendors"][c["vendor"]]["json_schema"], "lab_urine": lambda d, c: VEND["lab_vendors"][c["vendor"]]["json_schema"],
          "lab_saliva": lambda d, c: "saliva.v1", "ekg": lambda d, c: "ekg.v1", "other": lambda d, c: f"q.{c['type'].lower()}",
          "aps": lambda d, c: f"aps.{c['style']}"}
FN = {"app_part1": x_app, "app_part2": x_app, "rx": x_rx, "mib": x_mib, "mvr": x_mvr, "paramed": x_paramed, "lab_blood": x_lab,
      "lab_urine": x_lab, "lab_saliva": x_lab, "ekg": x_ekg, "other": x_other}


def extract_case(cdir: Path) -> list[ExtractedDoc]:
    ev = json.loads((cdir / "evidence.json").read_text())
    content = _ints(json.loads((cdir / "content.json").read_text())["docs"])
    out = []
    for d in ev["docs"]:
        c = content[d["doc_id"]]
        mult = VEND["aps_styles"][c["style"]]["ocr"] if d["doc_type"] == "aps" else 1.0
        n = Noiser(zlib.crc32((d["doc_id"] + "x").encode()), CAT[d["doc_type"]], mult)
        fx = fidx(ev["facts"], d["doc_id"])
        if d["doc_type"] == "aps":
            text = (ROOT / d["text_path"]).read_text()
            payload = x_aps(d, c, n, fx, text, ev["facts"])
        else:
            payload = FN[d["doc_type"]](d, c, n, fx)
        out.append(ExtractedDoc(doc_id=d["doc_id"], case_id=ev["case_id"], doc_type=d["doc_type"], vendor_schema=SCHEMA[d["doc_type"]](d, c),
                                payload=payload, losses=n.losses))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    a = ap.parse_args()
    dirs = sorted((ROOT / "data/source").glob("C*"))
    if a.ids:
        dirs = [d for d in dirs if d.name in set(a.ids.split(","))]
    outdir = ROOT / "data/extracted"
    outdir.mkdir(parents=True, exist_ok=True)
    from collections import Counter
    st, kinds = Counter(), Counter()
    for cdir in dirs:
        xs = extract_case(cdir)
        (outdir / f"{cdir.name}.json").write_text(json.dumps([x.model_dump(mode="json") for x in xs], indent=1, ensure_ascii=False))
        st["docs"] += len(xs)
        for x in xs:
            for l in x.losses:
                kinds[l.kind] += 1
                st["losses_with_fact"] += l.fact_id is not None
    print(f"extracted {st['docs']} docs for {len(dirs)} cases; losses {sum(kinds.values())} ({st['losses_with_fact']} tied to facts)")
    print(dict(kinds.most_common()))


if __name__ == "__main__":
    main()
