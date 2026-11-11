# CHECKPOINT — handoff for a new session (2026-11-11)

Read in this order: this file → `PROJECT_OVERVIEW.md` §6 (conclusions, plain) → `EXPERIMENTS.md` (full results,
paired CIs) → `SCOPING_NOTES_GENERATOR.md` → `STATUS.md` / `PLAN.md` (history). Commit: see `git log -1`.

## Where we are

Phases 0–6 are done and gated: guideline + rules, reference dictionaries, 1000 synthetic cases (truth → source docs
→ noisy extracted JSON), golden decisions with traces, noisy underwriter notes (12 personas, corruptions logged).

Phase 7 = **context engineering**: a new application arrives without notes; find similar past cases from the
application alone; put *their* notes in the prompt as few-shot examples. Model: Nova Lite (testing the
architecture, not the model). 200 test cases per split, 3 splits (seeds 11/22/33), scored against golden in code
(no LLM judge), paired bootstrap CIs. Spent **$20.36 of $25**.

### What the numbers mean

- **Exact decision**: share of cases where the final written decision equals golden.
- **Decision level** (`derived_coarse`): ignore the model's written decision, add up its own item debits in code,
  turn that into a broad band (Preferred / Standard / T1-2 / T3-4 / T5-8 / T9-16 / Postpone / Decline), compare
  with golden's band computed the same way. Measures rating judgement without Lite's arithmetic. Share of cases.
- **Worksheet**: partial-credit score 0–1 per case, averaged: found the right items, debits within 25,
  arithmetic adds up, class follows the total (+ flat extras when present). Not a share of cases right.

## Conclusions so far

1. **Notes from similar past cases make the worksheet clearly better** (0.21 → ~0.31), on all 3 splits and every
   slice (grey / partial / clean). **The decision barely moves** (exact +0.03 to +0.085, significant on 1 split).
2. **Similar beats random notes** on debits and on partial / clean cases. On grey cases any worked file helps as
   much: the gain there is the format.
3. **No definition of "similar" beats plain cosine on Cohere v4 embeddings.** VAE, PLS (on embeddings or our own
   tokens) and condition chunks all help about equally. PLS looked better on the decision on split 11; it did not
   replicate on 22 / 33 → withdrawn.
4. **Better retrieval is the lever.** Oracle neighbours (picked with golden, an upper bound) beat cosine on the
   decision on all 3 splits (exact +0.07 to +0.11). No practical method gets close.
5. **For the decision, the LLM adds nothing over a free vote** of the same 3 neighbours' known outcomes (vote ≈
   LLM on all splits; with PLS neighbours the vote is better on partial cases). The LLM's value is the worksheet.
6. **Gap guideline** (grey-area / partial-evidence rules removed): notes seemed to restore full performance, but
   that was mostly rule names leaking through the notes. With rule names stripped, notes still help the worksheet
   (+0.07) but no longer restore the decision level.
7. **Perfect notes beat messy notes** (golden write-ups; not available in real life): decision level 0.17 → 0.29,
   worksheet 0.33 → 0.40 (split 11). The mess costs consistency and some decision quality.
8. **A cheap rewrite of the messy notes** (Nova Lite, 2 examples from a 150-case "reviewed" sample, ~$0.75 per
   split) gets the worksheet most of the way to perfect notes on all 3 splits (+0.06 to +0.07, significant) but
   moves the decision level only a little (+0.02 to +0.06, never clearly significant). Rewrites tend to drop flat
   extras.
9. **A stronger model (Nova Pro, 50 cases) shows the same pattern**: notes help its worksheet by the same amount
   and leave the decision unchanged; Pro's worksheets and arithmetic are much better than Lite's.
10. Absolute levels are low (Lite exact 11–20%), but off the floor; differences between setups are measurable.

## Outstanding questions

1. **Does a stronger rewriter close the decision gap?** Lite rewrite 0.21 vs perfect 0.29 (split 11). ← next
2. **Is fine-tuning worth it?** Decided with the user: start with a good model; fine-tuning **deferred, probably
   out** (Bedrock training + hosting likely over budget; 150 training cases make a weak result inconclusive; the
   strong-model rewrite answers most of the same question). If ever done, fine-tune a good model.
3. **Can anything move the decision itself?** Only oracle retrieval and perfect notes did. Open ideas: use the
   neighbour vote as a decision hint next to the LLM worksheet (free, offline); a stronger underwriting model;
   retrieval trained on outcomes (needs fine-tuning, deferred).
4. **Why do rewrites drop flat extras?** Consistent on 3 splits (small n ≈ 15–20 cases each). Check a few files;
   maybe add a "keep every flat extra" line to the rewrite prompt.
5. Does the gap-guideline result hold on other splits? (Only split 11 run for G2.)
6. Low priority: hybrid cosine + PLS neighbours; PLS / rewrite combination (N4 with S4R neighbours).

## Next step: stronger rewriter in the other environment (Sonnet / Haiku)

That environment only runs the rewrites; the test stays here (same Nova Lite underwriter, so only the rewriter
changes).
1. Input: `experiments/rewrite_prompts_S1_s11.jsonl` — 327 lines, one per past case that is a cosine neighbour of a
   split-11 test case: `{case_id, system, prompt, max_tokens: 4000, temperature: 0, save_as}`. Each prompt already
   holds the guideline, the case's application and messy notes, and 2 worked examples. The guideline is the same
   prefix in every prompt → use prompt caching. Size: ~28M characters ≈ 9M input tokens + ~0.5M output in total;
   check current model prices before running, and pilot ~5 prompts first.
2. Send `system` as the system prompt and `prompt` as the user message. Save the reply text as
   `experiments/rewrites_<model>/<case_id>.md` (e.g. `rewrites_sonnet/C0056.md`). Check for repetition loops /
   missing "Decision" (see `looping()` / `ok()` in `src/rewrite_notes.py`).
3. Back here, with the files in place:
   `python src/run_llm.py --setups S1-G1-N4sonnet --n 0 --cap 0.6` (~$0.42), then
   `python src/compare_runs.py --pairs S1-G1-N4sonnet:S1-G1-N4,S1-G1-N4sonnet:S1-G1,S1-G1-N2:S1-G1-N4sonnet`.
   Form `N4<model>` reads `experiments/rewrites_<model>/`.
4. Alternative if that environment has Bedrock with Claude models: add the model to `PRICES` in `src/llm.py`
   (verify the model id and price) and run `python src/rewrite_notes.py --seed 11 --model <key>` directly.
   `run_llm` also accepts `S1-G1@<key>` to use that model as the underwriter.

**Cost estimates:** Bedrock bills ~1.4× our `est_tokens`; `run_llm` / `rewrite_notes` apply `TOK_FACTOR = 1.4`.
Transient Bedrock `ModelErrorException`s happen (2 so far); rerunning the same command resumes from the cache.

## Decisions made with the user (don't re-litigate)

- Task: application extracted JSON in → decision + worksheet out; scored vs golden; slices grey / partial / clean.
- Model for LLM runs: Nova Lite (testing architectures, not models). Pro check done (50 cases).
- Accept low absolute scores; the question is whether few-shot helps, not how good Lite is.
- Similarity is computed from the application only; examples are past cases' noisy notes, never golden.
- Start with a good model before any fine-tuning; fine-tuning deferred / probably out (see above).
- Two guideline arms: full and **gap** (grey-area / partial-evidence rules removed so only notes carry them).
- Neighbour vote is a free score for every retriever. Keyword/BM25 dropped (needs a complete dictionary).
  Structured features = separate workstream. PCA dropped from LLM runs (dominated by cosine).
- **Fine-tuning is deferred until scoped** (which model, where hosted, training data, cost, eval). Do not start it.
- Abbreviation dictionary / note-convention appendix is never given to the model.

## How the user wants to work

- **Estimate cost before any LLM/embedding spend; pilot small, then scale.** Stay under the caps.
- Commit and push at phase/milestone ends (they asked to push this checkpoint).
- A GPU / bigger machine is available **on request** — say when a step needs it. Current work runs fine on CPU.
- The original dev box is small and shared with the user's other jobs; never kill processes you didn't start.
- Never print or commit credentials. Keep user personal info out of anything sent to external services.
- Explain results in short, plain sentences first; tables and CIs in the docs.

## Credentials / environment (new account may differ)

- `pip install -r requirements.txt` (Python 3.12).
- `src/llm.py` is the only path to Bedrock (region `AWS_REGION`, default `us-east-1`). It reads `.env` (gitignored)
  for `AWS_BEARER_TOKEN_BEDROCK`; **if that variable is absent, boto3's normal credential chain is used**
  (profile, `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`, SSO, instance role). Nothing else needs changing.
- Models needed (enable access in the new account/region): `us.amazon.nova-lite-v1:0`, `us.amazon.nova-pro-v1:0`
  (optional), `cohere.embed-v4:0`, `amazon.titan-embed-text-v2:0` (only to re-embed), `cohere.rerank-v3-5:0`
  (only to revisit the reranker). Ping: `python src/llm.py --ping lite`.
- Spend tracking: `qa/usage.jsonl` (in git) feeds the **global cap** ($25 via `UW_CAP_GLOBAL`), so the running
  total carries across accounts. Spent so far: **$20.36** (`python src/llm.py --spent`). Caps per batch $2,
  per session $5 (`UW_CAP_BATCH`, `UW_CAP_SESSION`).

## What is in git (and what is not)

- In git: all code, guideline + rules, reference dictionaries, generated data (`data/`), golden, notes, LLM caches
  (`qa/*_llm.jsonl`), experiment outputs (`experiments/`: splits, labels, embeddings, condition extractions,
  chunk index + chunk embeddings, results tables). Resuming needs **no** re-spend.
- Not in git: `.env` (credentials), `__pycache__/`, `experiments/*.log`.
- Largest files: `experiments/chunks/emb_groups.npz` (58 MB, GitHub warns > 50 MB). If more embeddings are added,
  move them to S3 or store float16.

## Sanity checks after cloning (all free, no LLM calls)

```
python src/selftest.py            # Phase 0 gate
python src/check_rules.py         # guideline md <-> rules yaml
python src/check_golden.py        # Phase 5 gate (integrity PASS, 84% target-band agreement)
python src/check_notes.py         # Phase 6 gate PASS
python src/gen_notes.py --all --cap 0.01   # regenerates notes from cache: "lines voiced 0/0", files unchanged
python src/retrieval.py           # offline whole-case retrieval (~25 min on 2 CPUs) -> experiments/offline_retrieval.md
python src/chunks.py              # chunk index + offline chunk scores (uses cached embeddings) -> experiments/offline_chunks.md
```

## Key files for Phase 7

| File | Role |
|---|---|
| `EXPERIMENTS.md` | hypotheses, factors, run list, costs, all results so far |
| `src/exp_data.py` | splits, slices, golden-side labels, query-side text and own tokenizer |
| `src/embed_cases.py` | whole-case embeddings (cached in `experiments/emb/`) |
| `src/retrieval.py` | similarity spaces, offline neighbour scores, neighbour vote, learning curve |
| `src/extract_conditions.py` | Nova Lite lists risk items per application (`experiments/conditions/`) |
| `src/chunks.py` | condition chunks, alignment to golden groups, offline chunk scores, `--rerank` comparison |
| `data/notes/<case>.lines.json` | which golden step each note line came from (for chunking) |
| `src/score_worksheet.py` | golden-side scorer (decision, decision level, worksheet, items, consistency); `--selftest` |
| `src/run_llm.py` | LLM runner: setups `SPACE-GUIDELINE[-FORM][@model]`, `--seed`, `--score-only`, cache in `experiments/runs/` |
| `src/compare_runs.py` | paired bootstrap per slice |
| `src/h5_vote.py` | LLM vs free neighbour vote |
| `src/rewrite_notes.py` | notes rewrite (N4), `--model`, `--export` prompts |
| `src/guideline_variants.py` | G1 (full) / G2 (gap) guidelines |

Known gaps: 2 cases (C0362, C0391) have no extracted items (very large files; model hits the output cap);
item ↔ golden-group alignment is by similarity (no ground truth); flat-extra "match" metric is uninformative
(use FE recall in LLM runs).
