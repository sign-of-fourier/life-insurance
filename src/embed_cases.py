"""Phase 7: embed every application (query-side data only) -> experiments/emb/<name>.npy (rows in exp_data.ids() order).

R1 variants:
  titan_whole   Titan v2, whole case text (truncated at 45K chars; 10 cases longer)
  titan_docmean Titan v2, one embedding per extracted document, mean-pooled
  cohere_whole  Cohere Embed v4, whole case text (long context, no truncation needed)
Run: python src/embed_cases.py [--only titan_whole,...] [--cap 1.0]
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import exp_data as E  # noqa: E402
import llm  # noqa: E402

OUT = E.EXP / "emb"


def norm(v):
    v = np.asarray(v, dtype=np.float32)
    return v / (np.linalg.norm(v) + 1e-9)


def run(name, b, workers=8):
    cids = E.ids()
    if name == "titan_whole":
        f = lambda c: norm(llm.embed("titan-embed", [E.case_text(c)], budget=b, tag=f"emb:{c}:{name}")[0])  # noqa: E731
    elif name == "titan_docmean":
        f = lambda c: norm(np.mean([llm.embed("titan-embed", [t], budget=b, tag=f"emb:{c}:{name}")[0] for t in E.doc_texts(c)], axis=0))  # noqa: E731
    elif name == "cohere_whole":
        f = lambda c: norm(llm.embed("cohere-embed", [E.case_text(c)], budget=b, tag=f"emb:{name}")[0])  # noqa: E731
    else:
        raise SystemExit(name)
    with ThreadPoolExecutor(workers) as ex:
        X = np.stack(list(ex.map(f, cids)))
    OUT.mkdir(parents=True, exist_ok=True)
    np.save(OUT / f"{name}.npy", X)
    n_tr = sum(1 for t in llm.EMBED_TRUNCATED if t.endswith(name))
    print(name, X.shape, f"batch spend ${b.spent:.4f}; inputs truncated to fit model limit (retries): {n_tr}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="titan_whole,titan_docmean,cohere_whole")
    ap.add_argument("--cap", type=float, default=1.0)
    a = ap.parse_args()
    with llm.Budget("phase7-embed", cap=a.cap) as b:
        for n in a.only.split(","):
            if (OUT / f"{n}.npy").exists():
                print(n, "cached")
                continue
            run(n, b, workers=2 if n.startswith("cohere") else 8)


if __name__ == "__main__":
    main()
