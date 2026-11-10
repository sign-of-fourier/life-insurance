# EXPERIMENTS — context engineering for underwriting

_Living record: what we test, how, and the results. Update the results tables as runs finish; never edit a
recorded result without noting why._

## Goal

A new application arrives **without notes**. Find past cases that are similar, put their underwriter notes (and
decisions) into context as few-shot examples, and have a model reach the decision and write the worksheet. Compare
different definitions of "similar" (latent-space transformations), different units of retrieval, and different
guideline contexts. The real test is the **grey-area** and **partial-evidence** cases: do notes from similar cases
help there?

Known confound: the notes were generated from golden traces produced by an engine that reads the guideline. With
the full guideline in context, notes can only help as *worked examples*, never as new knowledge. The
**guideline-gap** arm removes that knowledge from the guideline so that only the notes carry it (H2).

## Task (fixed across all runs)

- **Input:** the case's noisy extracted JSON (`data/extracted/<case>.json`) — what is known at application time.
  Never the notes, golden, truth, or source docs of the test case.
- **Context:** guideline text (per arm) + k retrieved examples (per run) + output instructions.
- **Output (JSON):** decision (ladder, class, table, flat extras, postpone/decline, riders) + worksheet
  (list of {finding, rule id, effect}) + grey-area choices with reason.
- **Model:** Nova Lite for the full matrix (we compare architectures, not models; a weaker model also avoids a
  ceiling where the guideline alone solves the case). Optional Pro check later on 2 setups × 50 cases (~$3).
- **Not given in any arm:** `reference/abbreviations.yaml` or the guideline appendix on note conventions. Decoding
  house terminology is part of what is being tested.

## Data and splits

- 1000 cases. Retrieval pool 800 / test 200, stratified so grey-area and partial-evidence cases are represented;
  repeat over 3 random splits (seeds recorded). The test case is never in the pool. Supervised spaces (PLS, VAE,
  fine-tuned) train on the pool split only.
- Slices reported separately:
  - **grey**: case has ≥1 golden grey area (285 cases overall)
  - **partial evidence**: no APS in file (APS-6), Rx-only condition (RX-2.4), MIB-only / uncorroborated, stale
    APS (APS-3), undisclosed condition found by third-party data, facts dropped by extraction
  - **clean**: neither

## Hypotheses

| ID | Hypothesis | Answered by |
|---|---|---|
| H1 | Similar-case notes improve decisions over no examples and over random examples | B0 vs B1 vs S* (full guideline) |
| H2 | When the guideline has a gap, similar-case notes recover the missing knowledge | each setup, full vs gap guideline |
| H3 | Supervised latent spaces (PLS, fine-tuned retriever) retrieve better neighbours than unsupervised (cosine, PCA, VAE) | offline retrieval scores + S* runs |
| H4 | Chunking by condition beats whole-case retrieval, especially on multi-condition and partial-evidence cases | C* vs S* |
| H5 | Gains come from reasoning over the notes, not from copying the neighbours' decision | LLM runs vs neighbour vote (V*) |
| H6 | Noisy notes help less than clean golden write-ups (cost of the noise) | best 2 setups × {noisy, golden} |
| H7 | A fine-tuned model writes better worksheets/explanations than few-shot retrieval | **deferred — not scoped** (see below) |

## Factors

**F1 — Similarity space (how neighbours are chosen)**

| ID | Space | Notes |
|---|---|---|
| B0 | none (no examples) | baseline |
| B1 | random k | control: separates "any worked example" from "similar example" |
| S1 | cosine on embedding | pretrained text embedding of the application |
| S2 | PCA on embedding | run only if its neighbours overlap S1's < 80% (expected ≈ S1) |
| S3 | VAE on representation | unsupervised; expected ≈ PCA on 800 cases, recorded as a measured result |
| S4 | PLS on representation | supervised; targets = debits by chapter, class rank, grey areas fired |
| S5 | fine-tuned retriever | embedding trained so cases with similar golden traces are close — **deferred with fine-tuning** |
| S6 | extract-then-match | LLM turns the application into a structured risk summary; embed/match that |
| O1 | oracle | neighbours by golden-trace similarity — upper bound on retrieval |

Dropped: keyword/BM25 (needs a complete dictionary; terminology problem). Hand-built structured features are a
separate workstream.

**F2 — Representation fed to S3/S4 (tokenization question)**

| ID | Representation | Trade-off |
|---|---|---|
| R1 | pretrained embedding vector | general semantics; its subword tokenizer splits invented codes (MIB codes, rider codes, vendor field names) into meaningless pieces |
| R2 | bag of `field:value` tokens (own simple tokenizer, TF-IDF) | every code/drug/field value is an atomic token, so co-occurrence is learned from our data; sparse on 800 cases. Generic, not hand-engineered (unlike structured features) |

Whole JSON is median ~3.5K / p90 ~8.5K tokens; for R1 embed per document and pool, or truncate (decision below).

**F3 — Retrieval unit**

| ID | Unit | How |
|---|---|---|
| U1 | whole case | neighbour = a whole past case: summary + full notes + decision |
| U2 | condition chunk | see "Chunking by condition" below; retrieved per condition, grouped by condition in the prompt |

**F4 — Guideline context**

| ID | Guideline | |
|---|---|---|
| G1 | full (~15.5K tokens) | default |
| G2 | gap | full minus the grey-area chapter (GRY) and the partial-evidence defaults it points to (candidates: RX-2.4, APS-3, APS-6, MIB-4, CA-1 unknown-stage clause, ALC-1 conflict clause; final list frozen before any G2 run) |
| G3 | retrieved (vector DB over rules) | later, if time; risk: misses cross-cutting grey-area rules |

**F6 — Second-stage reranker (optional)**: X0 none · X1 Cohere Rerank on the top ~20-50 candidates of the best
first-stage space. Mainly for U2 (short condition snippet as query, condition chunks as candidates — fits the
reranker's input limits and its query→passage training); whole-case reranking only if input limits allow. Scored
offline first (same neighbour metrics), price checked before use.

**F5 — Example form**: N1 noisy UW notes (default) · N2 clean golden write-up (H6 only).

## Chunking by condition (U2)

- **Pool side (index):** each golden trace groups facts into conditions, and every note line comes from a trace
  step with fact ids. So each pool case's notes split into chunks: one per condition (disclosure, Rx/MIB, labs,
  APS, rating, with its debits/cap) plus case-level chunks (tobacco, build, finance, MVR/avocation, final
  worksheet). Each chunk is stored with its condition label, evidence snippet, and outcome.
  - Caveat: our line→condition alignment is free ground truth from generation. Real notes would need segmenting
    (LLM or rules). Record U2 with oracle segmentation first; add LLM segmentation as a realism check.
- **Query side:** the new application has no notes, so its conditions must be found from the evidence: an LLM
  step lists the impairments implied by the extracted JSON with the evidence for each (cannot reuse the engine's
  clustering — it links facts using truth). Each condition's evidence snippet is embedded and matched against
  chunks of the same kind across the whole pool, in any of the F1 spaces.
- **Risks to measure:** query-side detection misses (Rx-only and undisclosed conditions are exactly the
  partial-evidence slice); interactions between conditions (CMB rules) are lost when chunked — mitigate by adding
  one whole-case neighbour.

## Free scores (no LLM)

- **Offline retrieval quality** for every space × unit: do the top-k neighbours share the test case's rated
  conditions and grey areas (vs golden traces)? Precision@k, condition coverage, and diagnostics (same vendor
  template, same persona) to catch matching on format instead of medicine.
- **V\* neighbour vote (semi-supervised):** predicted decision = majority/weighted vote of the k neighbours'
  golden decisions. One per similarity space. If LLM + neighbours ≈ vote, the notes added nothing (H5).

## Metrics

- **Decision:** exact decision, outcome band, ladder correct, decline/postpone correct, |net debit error|.
- **Worksheet (vs golden trace, no LLM judge):** rated findings recall/precision, rule-id recall, debit
  arithmetic correct, class follows from stated debits, grey-area choice agrees with golden.
- **Retrieval:** offline scores above.
- All reported overall and per slice (grey / partial evidence / clean), mean over splits with spread.

## Run list and cost (Nova Lite, 200 test cases, k=3, ~31K in / 1.5K out per call ≈ $0.0022)

| Block | Setups | Calls | ~Cost |
|---|---|---|---|
| Whole case, full guideline | B0, B1, S1, S2?, S3×R1/R2, S4×R1/R2, S5, S6, O1 | ~11 × 200 | $5 |
| Whole case, gap guideline | same | ~11 × 200 | $5 |
| Chunked (U2), full + gap | best 3 spaces + O1 | 8 × 200 | $3.5 |
| Example form (H6) | best 2 setups × golden write-up | 2 × 200 | $1 |
| Query-side condition extraction (U2), S6 summaries | 1000 cases | 2 × 1000 small | <$1 |
| Embeddings | 1000 cases + chunks | — | <$0.10 |
| Optional Pro check | 2 setups × 50 | 100 | ~$3 |
| **Total (ex fine-tuning)** | | | **~$16 (+ ~$3 optional)** |

Bedrock spent to date: $3.06 of the $25 cap. Each block runs only after a cost dry-run.

## Leakage controls

- The test case is excluded from the pool, the supervised training data, and the oracle.
- The model sees only the test case's extracted JSON; never its notes, golden, truth, or design.
- Supervised targets come from pool golden only. G2 is frozen before any G2 run.
- Neighbours' notes include persona divergence and deliberate errors (they are realistic, not cleaned).

## Open decisions

1. Embedding model for R1 (Bedrock Titan v2 vs Cohere; input limits) and per-document pooling vs truncation.
2. k (fixed at 3 for the main matrix; diversity/k test on the best setup only if time).
3. Final G2 removal list.
4. Embedding pre-test (cheap, no LLM calls): embed all 1000 cases with each candidate model, score offline
   retrieval quality, pick one before any LLM run.

## Deferred: fine-tuning (H7, and S5 if it needs a trained model)

Not started until scoped. Questions to answer first:
- Which model is fine-tuned (generator vs retriever/embedding), and which base model?
- Where it is hosted for training and for inference (Bedrock customization vs local GPU vs other), and what
  inference costs (on-demand vs provisioned).
- Training data: application JSON -> golden write-up, or -> noisy notes; size of the pool split; held-out eval.
- What it is compared against (best few-shot setup) and on which metrics (worksheet metrics above).
- Budget, estimated before anything runs.

## Results

_Recorded per run in `experiments/<run_id>.jsonl` (config + per-case outputs + scores); summary below._

### Offline retrieval quality

Run 2026-11-10, whole-case unit (U1), k=3, mean ± sd over 3 splits. Full table: `experiments/offline_retrieval.md`
(`src/retrieval.py`). Embedding cost $0.62 (Titan v2 whole: 107/1000 inputs truncated to 8K tokens; Cohere v4: none).

Columns: **coverage** = share of the query's rated conditions found in any of the 3 neighbours; **grey** = grey
queries, share of neighbours sharing a GRY rule; **vote** = neighbour-vote band accuracy (majority-band prior 0.157);
**vendor** = vendor-schema overlap with the query (format matching; random 0.274).

| Space | Repr | Coverage | Grey share | Vote (all) | Vote (grey) | Vote (partial) | Vendor |
|---|---|---|---|---|---|---|---|
| oracle | golden | 0.80 | 0.85 | 0.95 | 0.99 | 0.93 | 0.30 |
| cosine | Cohere v4 | **0.60** | 0.24 | 0.21 | 0.25 | 0.20 | 0.37 |
| PCA | Cohere v4 | 0.58 | 0.22 | 0.18 | 0.19 | 0.18 | 0.37 |
| PLS | Cohere v4 | 0.56 | 0.29 | 0.17 | 0.18 | 0.19 | 0.37 |
| VAE | Cohere v4 | 0.53 | 0.25 | 0.18 | 0.16 | 0.18 | 0.36 |
| cosine | own tokens (R2) | 0.55 | 0.17 | 0.17 | 0.14 | 0.19 | 0.48 |
| PLS | own tokens (R2) | 0.51 | **0.39** | **0.23** | 0.17 | **0.32** | 0.30 |
| VAE | own tokens (R2) | 0.50 | 0.19 | 0.16 | 0.13 | 0.15 | 0.34 |
| PCA (LSA) | own tokens (R2) | 0.46 | 0.21 | 0.15 | 0.09 | 0.19 | 0.53 |
| cosine | Titan whole | 0.48 | 0.26 | 0.16 | 0.14 | 0.16 | 0.39 |
| cosine | Titan per-doc mean | 0.49 | 0.17 | 0.14 | 0.11 | 0.14 | **0.60** |
| random | - | 0.29 | 0.18 | 0.09 | 0.09 | 0.09 | 0.27 |

Findings:
1. Every space beats random on finding cases with the same conditions (0.45-0.60 vs 0.29), but all are far below
   the oracle (0.80). Best: plain cosine on Cohere v4.
2. As predicted, PCA and the VAE do not beat raw cosine (slightly worse on every representation).
3. Whole-case similarity barely predicts the outcome: neighbour vote 0.14-0.23 vs a 0.16 majority prior. Cases
   share conditions but not severity/combination, which is what sets the decision. Argues for chunking by condition.
4. Supervision helps the outcome-relevant parts: PLS on own tokens is best on grey-area sharing (0.39 vs 0.18
   random) and on the partial-evidence vote (0.32), at some cost in condition coverage.
5. Format matching is real: Titan per-doc mean and own-token cosine/LSA retrieve by vendor schema (0.48-0.63 vs
   0.27 random). Cohere v4 and PLS are least affected.
6. No unsupervised space finds cases with the same partial-evidence pattern (≈ random), as expected: it is an
   absence (missing APS, undisclosed condition), not something present in the text.

Decision: Cohere v4 is the embedding for R1. Candidates for LLM runs: random, cosine-Cohere, PLS-own-tokens,
VAE-Cohere (the VAE hypothesis), oracle. PCA dropped from LLM runs (dominated by cosine).

#### Rerun 2026-11-10 (labels without worksheet-mechanics chapters; table/net/FE added to PLS targets)

Same ranking as above (full table `experiments/offline_retrieval.md`). Coverage: cosine-Cohere 0.64, PCA-Cohere 0.60,
PLS-Cohere 0.57, VAE-Cohere 0.55, PLS-own-tokens 0.51, random 0.29, oracle 0.81. PLS-own-tokens: grey share 0.36,
partial-evidence vote 0.36. Exact-decision vote ≈ band vote minus 0.01-0.03. Flat-extra match is uninformative as a
rate (only 74 cases have a flat extra, so "no FE" dominates; random 0.86) — to be replaced by FE recall in LLM runs.

**Learning curve (VAE / PLS fit on 200 / 400 / 800 pool cases; neighbours always from the full pool):**

| Space | Repr | Coverage 200 / 400 / 800 | Grey share | Partial vote |
|---|---|---|---|---|
| VAE | Cohere | 0.50 / 0.53 / 0.55 | 0.24 / 0.21 / 0.25 | 0.17 / 0.17 / 0.18 |
| VAE | own tokens | 0.43 / 0.45 / 0.52 | 0.19 / 0.17 / 0.19 | 0.12 / 0.14 / 0.15 |
| PLS | Cohere | 0.52 / 0.57 / 0.57 | 0.25 / 0.26 / 0.28 | 0.17 / 0.22 / 0.22 |
| PLS | own tokens | 0.49 / 0.50 / 0.51 | 0.27 / 0.30 / 0.36 | 0.14 / 0.20 / 0.36 |

Both are still improving at 800. The VAE gains on coverage but stays below plain cosine (0.64); PLS-own-tokens gains
most on exactly the grey / partial-evidence targets. More (cheap, generated) cases would likely help both, PLS most.

### Offline condition-chunk retrieval (U2)

Run 2026-11-10. Query side: Nova Lite lists risk items from the extracted JSON (`src/extract_conditions.py`, all
1000 cases, $0.55, 8.8 items/case; 2 very large files returned nothing — known gap). Index side: each item aligned
to a golden condition group of its case by Cohere similarity (≥ 0.35); payload = that group's note lines + outcome
(`src/chunks.py`, 8886 chunks, 2332 rated). Retrieval: Cohere cosine item → pool chunks, k=3. Full table:
`experiments/offline_chunks.md`.

| Metric | All | Grey | Partial | Clean |
|---|---|---|---|---|
| detect: rated conditions found by the extraction | 0.93 | 0.94 | 0.96 | 0.90 |
| label@3: retrieved chunks are the same condition | 0.84 | 0.81 | 0.82 | 0.86 |
| debit@3: ... and the same debit bucket | 0.68 | 0.61 | 0.68 | 0.73 |
| vote: decision built from condition votes | **0.48** | **0.43** | **0.43** | **0.55** |
| reference: whole-case vote, same coarse scale | 0.42 | 0.40 | 0.40 | 0.45 |
| reference: majority prior, same coarse scale | 0.39 | | | |
| net debit error (non-decline/postpone) | 28 | 40 | 34 | 17 |

(Coarse scale: <=Std / Standard / T1-2 / T3-4 / T5-8 / T9-16 / Postpone / Decline; ladder-agnostic.)

Findings:
1. Chunking finds the right kind of evidence: 84% of retrieved chunks are about the same condition (whole-case
   neighbours share a condition far less often).
2. A decision assembled from per-condition votes beats the whole-case vote (0.48 vs 0.42) and the prior (0.39),
   on every slice. Whole-case vote barely beats the prior.
3. Severity is the hard part: same condition but a different debit level in a third of retrieved chunks, worst on
   grey cases (0.61) — exactly where the notes' reasoning should matter.
4. Query-side detection misses 7% of rated conditions (10% on clean cases, mostly non-medical items).
5. Caveat: alignment of items to golden groups is by similarity (no ground truth), on both sides; label@3 includes
   alignment noise.

### Reranker on condition chunks (F6)

Run 2026-11-10: Cohere Rerank 3.5 on the top-30 cosine candidates per extracted item, paired with cosine alone on
the same queries (split 11, first 50 test cases; `python src/chunks.py --rerank --limit 50`; table
`experiments/offline_chunks_rerank_pilot.md`). Price $2.00 / 1000 queries (Bedrock pricing page).

| Metric | Slice | Cosine | + Rerank |
|---|---|---|---|
| label@3 (same condition) | all / grey / partial | 0.87 / 0.82 / 0.87 | 0.84 / 0.75 / 0.90 |
| debit@3 (same severity) | all / grey / partial | 0.66 / 0.66 / 0.57 | 0.62 / 0.57 / 0.59 |
| vote (coarse) | all / grey / partial | 0.50 / 0.41 / 0.44 | 0.40 / 0.35 / 0.31 |

Finding: the reranker does not help and hurts most on grey cases. Likely reason (hypothesis): the top-30 cosine
candidates are already about the right condition, so the reranker re-orders them by topical/lexical overlap, which
says nothing about severity; it was trained for query -> passage relevance, not case-to-case similarity. Not run on
the full split (would cost ~$3.50) since the 50-case result was consistent with the 10-case pilot. Not carried into
LLM runs. Possible revisit: rerank with richer text (item + outcome-relevant values) or a reranker tuned on golden.

### Decisions and worksheets

| Run | Space | Unit | Guideline | Examples | Exact | Band | Grey: exact | Partial: exact | Rule recall | vs vote | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
