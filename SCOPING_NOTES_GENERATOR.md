# Scoping — clean-notes generator (fine-tuning backlog item)

Status: **scoping only, nothing trained or started.** Written 2026-11-10 after H6.

## Why

H6 showed that clean golden-style write-ups of the past cases help more than the noisy notes (cosine neighbours,
seed 11: decision band from the model's own items 0.17 → 0.29, class follows items +0.24, rule names +0.15,
grey-area flags +0.19). Those write-ups do not exist at run time. The idea: generate them for every past case from
what *does* exist — the past case's application and its noisy notes — then use them as the few-shot examples.

## What the generator sees and writes

- Input: past case application (extracted JSON) + its noisy UW notes (+ the guideline, which the underwriting model
  sees anyway). Never the golden of that case.
- Output: a write-up in the golden format (items, debits, grey areas, worksheet, decision).
- Use: replace N1 (noisy notes) with N4 (generated) in the prompt; compare against N1 and N2 (golden, upper bound).

## Realism constraint (important)

A real company has no golden for its past cases either. Training a generator needs *some* golden-labelled cases —
in practice a small expert-reviewed sample. So the training set should be small (e.g. 100-200 cases), drawn only
from cases outside every test split (510 of the 1000 are in no test set), and the learning curve reported.

## Options, cheapest first

| Option | What | Cost | Needs |
|---|---|---|---|
| **A. Prompt-only rewrite** (no training) | Nova Lite/Pro rewrites noisy notes → golden format, with 2-3 golden examples from the training sample as few-shot | Lite ~800 pool cases × ~$0.003 ≈ $2.5 per split (Pro ≈ 13×); then one 200-case run ≈ $0.55 | nothing new |
| B. Bedrock fine-tune (Nova Micro/Lite) | Supervised fine-tune on (application + notes → golden write-up) pairs | Training priced per token; custom-model inference has historically needed provisioned throughput (hourly). **Verify current pricing before deciding**; likely well over the remaining $7 cap | budget increase |
| C. Local LoRA, open 7-8B model | LoRA on an open instruct model | Compute only | **GPU** (24 GB+; inputs are 15-25K tokens, so long-context memory is the constraint, likely 40-80 GB) |

## Evaluation

1. Intrinsic: score the generated write-up against golden with `score_worksheet` (item recall, debits, decision).
2. Extrinsic (the real test): S1-G1-N4 on the 200 seed-11 test cases, paired against S1-G1 (noisy) and
   S1-G1-N2 (golden). Success = recovers a meaningful share of the N1 → N2 gap.

## Recommendation

Do **A** first (about $3-4 with Lite for one split, inside the current cap). Only consider B or C if A recovers
little of the gap. Both need a decision from the user (budget for B, GPU for C).
