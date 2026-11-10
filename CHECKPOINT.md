# CHECKPOINT — handoff for a new session (2026-11-10)

Read in this order: this file → `STATUS.md` (phase log) → `EXPERIMENTS.md` (current work: plan + results) →
`PLAN.md` (original design). Commit at checkpoint: see `git log -1`.

## Where we are

Phases 0–6 are done and gated: guideline + rules, reference dictionaries, 1000 cases (truth → source docs →
noisy extracted JSON), golden decisions with traces, noisy underwriter notes (12 personas, all corruptions logged).

Phase 7 = **experiments on context engineering**: a new application arrives without notes; retrieve similar past
cases and put their notes in context as few-shot examples; compare definitions of "similar". Done so far (all
recorded in `EXPERIMENTS.md`):
- splits (3 × 800 pool / 200 test, stratified grey / partial-evidence / clean) and golden-side scoring labels
- embeddings: Titan v2 (whole, per-doc mean), Cohere v4 (whole) → Cohere v4 chosen
- offline whole-case retrieval: random / cosine / PCA / VAE / PLS / oracle × 4 representations, neighbour vote,
  VAE/PLS learning curve
- condition extraction (Nova Lite, all 1000) → condition chunks → offline chunk retrieval (beats whole-case)
- Cohere Rerank 3.5 on chunks: tested on 50 cases, no gain → not used

**Done since:** worksheet scorer (`src/score_worksheet.py`), G2 frozen (`src/guideline_variants.py`), LLM runner
(`src/run_llm.py`), paired comparisons (`src/compare_runs.py`), 200-case Nova Lite matrix (11 setups) — results in
`EXPERIMENTS.md` and PROJECT_OVERVIEW §6a. **Next:** see PROJECT_OVERVIEW §8 (other seeds, H6, H5). Spent $9.48.

## Decisions made with the user (don't re-litigate)

- Task: application extracted JSON in → decision + worksheet out; scored vs golden; slices grey / partial / clean.
- Model for LLM runs: Nova Lite (testing architectures, not models). Optional small Pro check later.
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

## Credentials / environment (new account may differ)

- `pip install -r requirements.txt` (Python 3.12).
- `src/llm.py` is the only path to Bedrock (region `AWS_REGION`, default `us-east-1`). It reads `.env` (gitignored)
  for `AWS_BEARER_TOKEN_BEDROCK`; **if that variable is absent, boto3's normal credential chain is used**
  (profile, `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`, SSO, instance role). Nothing else needs changing.
- Models needed (enable access in the new account/region): `us.amazon.nova-lite-v1:0`, `us.amazon.nova-pro-v1:0`
  (optional), `cohere.embed-v4:0`, `amazon.titan-embed-text-v2:0` (only to re-embed), `cohere.rerank-v3-5:0`
  (only to revisit the reranker). Ping: `python src/llm.py --ping lite`.
- Spend tracking: `qa/usage.jsonl` (in git) feeds the **global cap** ($25 via `UW_CAP_GLOBAL`), so the running
  total carries across accounts. Spent so far: **$9.48** (`python src/llm.py --spent`). Caps per batch $2,
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

Known gaps: 2 cases (C0362, C0391) have no extracted items (very large files; model hits the output cap);
item ↔ golden-group alignment is by similarity (no ground truth); flat-extra "match" metric is uninformative
(use FE recall in LLM runs).
