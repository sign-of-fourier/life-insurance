"""Single entry point for every Bedrock call, with hard spending caps.

Usage in code:
    from llm import Budget, call
    with Budget("aps-pilot", cap=2.00) as b:
        text = call("pro", system, prompt, max_tokens=3000, budget=b)

CLI:
    python src/llm.py --spent                 # running total from qa/usage.jsonl
    python src/llm.py --estimate pro 2500 4000 200   # model in_tok out_tok n_calls
    python src/llm.py --ping micro            # 5-token connectivity check

Caps (USD, override via env): UW_CAP_BATCH=2  UW_CAP_SESSION=5  UW_CAP_GLOBAL=25
A call is refused BEFORE sending if (spent + worst-case cost of this call) would exceed any cap.
Worst case = estimated input tokens + the full max_tokens of output.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USAGE_LOG = ROOT / "qa" / "usage.jsonl"

# $ per 1M tokens (input, output). us-east-1 on-demand. Verify on AWS pricing page.
PRICES = {
    "micro": ("us.amazon.nova-micro-v1:0", 0.035, 0.14),
    "lite": ("us.amazon.nova-lite-v1:0", 0.06, 0.24),
    "lite2": ("us.amazon.nova-2-lite-v1:0", 0.30, 2.50),
    "pro": ("us.amazon.nova-pro-v1:0", 0.80, 3.20),
}

CAP_BATCH = float(os.environ.get("UW_CAP_BATCH", 2))
CAP_SESSION = float(os.environ.get("UW_CAP_SESSION", 5))
CAP_GLOBAL = float(os.environ.get("UW_CAP_GLOBAL", 25))

SESSION_ID = os.environ.get("UW_SESSION_ID") or uuid.uuid4().hex[:8]
_session_spent = 0.0


class BudgetExceeded(RuntimeError):
    pass


def _load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def cost(model: str, in_tok: int, out_tok: int) -> float:
    _, pin, pout = PRICES[model]
    return in_tok / 1e6 * pin + out_tok / 1e6 * pout


def est_tokens(text: str) -> int:
    return max(1, len(text) // 4 + 1)  # conservative-ish: ~4 chars/token


def global_spent() -> float:
    if not USAGE_LOG.exists():
        return 0.0
    total = 0.0
    for line in USAGE_LOG.read_text().splitlines():
        if line.strip():
            total += json.loads(line)["usd"]
    return total


class Budget:
    """Per-batch spending cap. Use as a context manager around a batch of calls."""

    def __init__(self, name: str, cap: float = CAP_BATCH):
        self.name, self.cap, self.spent, self.calls = name, min(cap, CAP_BATCH), 0.0, 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        print(f"[budget:{self.name}] {self.calls} calls, ${self.spent:.4f} of ${self.cap:.4f} cap", file=sys.stderr)
        return False


def _check(worst: float, budget: Budget | None) -> None:
    g = global_spent()
    if g + worst > CAP_GLOBAL:
        raise BudgetExceeded(f"global cap ${CAP_GLOBAL} (spent ${g:.4f}, call worst-case ${worst:.4f})")
    if _session_spent + worst > CAP_SESSION:
        raise BudgetExceeded(f"session cap ${CAP_SESSION} (spent ${_session_spent:.4f})")
    if budget and budget.spent + worst > budget.cap:
        raise BudgetExceeded(f"batch '{budget.name}' cap ${budget.cap} (spent ${budget.spent:.4f})")


_client = None


def _bedrock():
    global _client
    if _client is None:
        _load_env()
        import boto3
        from botocore.config import Config
        _client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"),
                               config=Config(retries={"max_attempts": 6, "mode": "adaptive"}, read_timeout=300))
    return _client


def call(model: str, system: str, prompt: str, *, max_tokens: int = 2000, temperature: float = 0.7,
         budget: Budget | None = None, tag: str = "") -> str:
    global _session_spent
    model_id = PRICES[model][0]
    worst = cost(model, est_tokens(system) + est_tokens(prompt), max_tokens)
    _check(worst, budget)
    t0 = time.time()
    r = _bedrock().converse(
        modelId=model_id,
        system=[{"text": system}] if system else [],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    u = r["usage"]
    usd = cost(model, u["inputTokens"], u["outputTokens"])
    _session_spent += usd
    if budget:
        budget.spent += usd
        budget.calls += 1
    USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with USAGE_LOG.open("a") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "session": SESSION_ID,
            "batch": budget.name if budget else None, "tag": tag, "model": model,
            "in": u["inputTokens"], "out": u["outputTokens"], "usd": round(usd, 6),
            "secs": round(time.time() - t0, 2), "stop": r.get("stopReason"),
        }) + "\n")
    return "".join(c.get("text", "") for c in r["output"]["message"]["content"])


def estimate(model: str, in_tok: int, out_tok: int, n: int) -> float:
    return cost(model, in_tok, out_tok) * n


def _summary() -> None:
    if not USAGE_LOG.exists():
        print("no usage yet: $0.00")
        return
    rows = [json.loads(l) for l in USAGE_LOG.read_text().splitlines() if l.strip()]
    by: dict[tuple, list] = {}
    for r in rows:
        k = (r["batch"] or "-", r["model"])
        a = by.setdefault(k, [0, 0, 0, 0.0])
        a[0] += 1; a[1] += r["in"]; a[2] += r["out"]; a[3] += r["usd"]
    print(f"{'batch':30} {'model':6} {'calls':>6} {'in_tok':>10} {'out_tok':>10} {'usd':>9}")
    for (b, m), (n, i, o, usd) in sorted(by.items()):
        print(f"{b:30} {m:6} {n:6} {i:10} {o:10} {usd:9.4f}")
    print(f"TOTAL ${sum(r['usd'] for r in rows):.4f}   (global cap ${CAP_GLOBAL})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--spent", action="store_true")
    ap.add_argument("--estimate", nargs=4, metavar=("MODEL", "IN_TOK", "OUT_TOK", "N"))
    ap.add_argument("--ping", metavar="MODEL")
    a = ap.parse_args()
    if a.spent:
        _summary()
    elif a.estimate:
        m, i, o, n = a.estimate
        print(f"{n} x {m} ({i} in / {o} out) = ${estimate(m, int(i), int(o), int(n)):.4f}")
    elif a.ping:
        with Budget("ping", cap=0.01) as b:
            print(call(a.ping, "", "Reply with the word OK.", max_tokens=5, budget=b, tag="ping"))
    else:
        ap.print_help()
