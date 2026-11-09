"""Shared rule utilities: load rules/*.yaml, evaluate catalog `match` predicates, first-match profile lookup.

Used by the truth generator (to realize attributes that land in a chosen profile) and by the Phase 5 engine
(to pick the profile from attributes established in evidence). Keeping one matcher guarantees they agree.
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


@functools.lru_cache(maxsize=None)
def load(name: str) -> dict:
    p = ROOT / "rules" / f"{name}.yaml"
    if not p.exists():
        p = ROOT / "reference" / f"{name}.yaml"
    return yaml.safe_load(p.read_text())


def pred_ok(value: Any, pred: Any) -> bool:
    """Evaluate one predicate against a value. None never satisfies a comparison."""
    if isinstance(pred, dict):
        if value is None:
            return False
        for op, x in pred.items():
            if op == "lt" and not value < x: return False
            if op == "le" and not value <= x: return False
            if op == "gt" and not value > x: return False
            if op == "ge" and not value >= x: return False
            if op == "in" and value not in x: return False
        return True
    if isinstance(pred, list) and len(pred) == 2 and all(isinstance(v, (int, float)) for v in pred):
        return value is not None and pred[0] <= value <= pred[1]
    return value == pred


def match(attrs: dict, m: dict) -> bool:
    for k, pred in (m or {}).items():
        if k == "any_of":
            if not any(pred_ok(attrs.get(k2), p2) for k2, p2 in pred.items()):
                return False
        elif not pred_ok(attrs.get(k), pred):
            return False
    return True


def first_profile(key: str, attrs: dict) -> dict | None:
    e = load("impairments")[key]
    for p in e.get("profiles", []):
        if match(attrs, p.get("match", {})):
            return p
    return None


def grid_lookup(key: str, row_val: float, col_val: float):
    g = load("impairments")[key]["grid"]
    rows = g["bands_age"]
    cols = g.get("bands_years") or g.get("bands_a1c")
    i = next((i for i, (lo, hi) in enumerate(rows) if lo <= row_val <= hi), None)
    j = next((j for j, (lo, hi) in enumerate(cols) if lo <= col_val < hi or (j == len(cols) - 1 and col_val >= lo)), None)
    if i is None or j is None:
        return None
    return g["values"][i][j]


def table_from_net(net: int, age: int) -> tuple[str, int]:
    """CLS-3.3 / CLS-3.4: net debits -> ('Standard'|'Table'|'Decline', table)."""
    dt = load("classes")["debit_table"]
    if net <= dt["standard_max"]:
        return ("Standard", 0)
    if net > dt["decline_above"]:
        return ("Decline", 0)
    t = -(-(net - dt["standard_max"]) // dt["table_step"])
    if age >= dt["age_limit"]["min_age"] and t > dt["age_limit"]["max_table"]:
        return ("Decline", 0)
    return ("Table", t)
