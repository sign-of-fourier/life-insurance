# Agentic UW Synthetic Dataset — Master Plan

Goal: a synthetic life-insurance underwriting corpus (~1000 cases) where each case has
application + evidence → **noisy human UW notes** (hard for foundation models) paired with a
**golden, clearly-reasoned decision** (for fine-tuning / VAE structure recovery).

This file is the source of truth across sessions. Progress lives in `STATUS.md`.
Every session starts by reading `PLAN.md` + `STATUS.md` and nothing else unless needed.

---

## Core design principles

1. **Truth → Source docs → Extracted JSON → Golden → Noise.** Generated in that order, never backwards.
   - *Latent truth*: the person's real health/risk profile (some of it never disclosed).
   - *Source documents* ("the PDFs"): what the UW actually reads — app, MVR, Rx, MIB, lab
     reports, APS — derived from truth with disclosure gaps, contradictions, irrelevant noise.
     Stored as rendered text documents, each in its **vendor/provider-specific layout**.
   - *Extracted JSON*: what the downstream model gets — we pretend we sit after an OCR/
     LangChain extraction step. Schema differs per source/vendor, with OCR-style noise
     (dropped fields, misread digits/units, merged table cells, lost flags, truncated APS
     pages). Every extraction loss is logged. Consequence: UW notes may cite facts that are
     in the source doc but **missing from the JSON** — that is intended.
   - *Vendor variation (labs/APS, low error but inconsistent)*: one lab flags out-of-range
     values, another doesn't; one reports a combined panel (e.g. TC/HDL/ratio), another
     separate values; units differ (mg/dL vs mmol/L); old reports use superseded test
     methods/cutoffs; APS formats vary by EMR/practice (SOAP, letters, discharge summaries,
     faxed scans with headers/footers).
   - *Golden decision*: a deterministic rules engine applies the guidelines to the **evidence**
     (not the truth) and emits a full reasoning trace → clean narrative.
   - *Noisy notes*: rendered from the golden trace through an underwriter "persona" that
     abbreviates, omits, staggers, and occasionally errs. Every corruption is logged.
2. **Code generates, the LLM designs.** Structured data (people, MIB, Rx, MVR, labs, decisions)
   is produced by seeded Python scripts so it is reproducible and validatable. LLM effort goes to
   designing rulebooks/templates and to free-text (APS, notes) in small batches.
3. **Machine-readable rules mirror the prose guideline.** `guidelines.md` is for humans;
   `rules/*.yaml` encodes the same tables for the engine. A check confirms they agree.
4. **Coverage over realism.** Cases come from a coverage design (pairwise/stratified), not a
   population distribution, so every class, impairment, and edge case is represented.
5. **Everything on disk, small batches, checkpoint often.** No phase requires holding more than
   one batch (~50 cases) or one reference file in context.

## Directory layout

```
PLAN.md  STATUS.md  README.md
reference/      guidelines.md, mib_codebook.md/.yaml, rx_map.yaml, mvr_codes.yaml,
                lab_ranges.yaml, riders.yaml, abbreviations.yaml, uw_personas.yaml
rules/          machine-readable guideline tables (build, BP, lipids, tobacco, impairments,
                requirements-by-age/amount, debit/credit, table ratings, flat extras)
src/            generators, engine, renderers, validators (python, seeded)
data/
  design/       coverage matrix (case_id → target attributes)
  truth/        case_XXXX.json  latent profile
  source/       case_XXXX/  rendered source docs (app, mvr, rx, mib, lab_<vendor>, aps_<n>)
  extracted/    case_XXXX/  noisy per-vendor JSON + extraction_loss.json
  golden/       case_XXXX.json (decision + trace) and case_XXXX.md (clean narrative)
  notes/        case_XXXX.txt (observations + worksheet, noisy) + corruption log
  packaged/     train/val/test JSONL
qa/             validation reports, coverage reports, spot-check reviews
```

---

## Phases

### Phase 0 — Scaffolding (short)
- Create layout, `STATUS.md`, `README.md`, python env (`pydantic`, `pyyaml`, `numpy`, `faker`).
- Define **schemas** (pydantic) for: Truth, Part1, Part2, MVR, Rx, MIB, Labs, APS meta,
  Decision/Trace, Notes. Schemas freeze early; everything downstream validates against them.
- ✅ Gate: schemas import and round-trip a hand-written example case.

### Phase 1 — Underwriting guideline (`reference/guidelines.md`)
Sub-plan:
1. Survey 2–4 publicly available carrier/reinsurer field guides and preferred-criteria charts;
   note structure only (not copied text).
2. Fix the risk-class taxonomy, e.g. Elite / Preferred Plus / Preferred / Standard Plus /
   Standard / Pref Smoker / Standard Smoker / Table 1–16 (+25% each) / Table Smoker /
   Postpone / Decline, plus flat extras ($/1000).
3. Write sections: class criteria matrix; build chart; BP; cholesterol; tobacco/nicotine
   (types, lookbacks, cotinine rules, "admits cigs in last 12 mo → best = Std Smoker");
   family history; MVR; alcohol/drugs; avocations & aviation; occupation; foreign travel &
   foreign nationals; financial justification; age/amount requirements grid (when labs/APS/
   paramed/EKG are required); impairment chapters (cardiac, HTN, diabetes/A1c, cancer, mental
   health, respiratory, GI/liver, renal, neuro, sleep apnea, substance, etc.) with debit tables;
   debit/credit method; combining multiple impairments; grey-area guidance; riders (≈10
   invented, with codes and eligibility rules); requirement-ordering rules.
4. Extract tables into `rules/*.yaml`.
- ✅ Gate: completeness checklist (every taxonomy class reachable, every impairment has a
  rule, every rider has eligibility); yaml ↔ md consistency script.

### Phase 2 — Reference dictionaries (each its own mini-task, own file)
- **MIB codebook**: 6-digit scheme (digit1 body system, d1–3 condition, d4 severity/degree,
  d5 source: labs/APS/3rd-party/eMed/app admission/…, d6 qualifier: surgical/treated/
  severe/history-of/…). ~150–250 condition codes + decoding rules. Include codes that are
  irrelevant to life UW, stale, or ambiguous. Foreign-national sparsity rule.
- **Rx map**: drug → indication(s) (often ambiguous: e.g. gabapentin, metoprolol, trazodone),
  dosage, fill patterns; distractor drugs (antibiotics, allergy).
- **MVR codes**: violation codes, points, lookback.
- **Lab ranges**: blood chem, lipids, LFTs, A1c, NT-proBNP, PSA, urine (protein, glucose,
  cotinine, cocaine), saliva (cotinine, HIV); reference vs. UW thresholds.
- **Riders**: ~10 invented riders with opaque codes (e.g. `XCR`, `ADB-2`, `GIO`), terms,
  eligibility by class/age.
- **Abbreviations**: three tiers — (a) common medical (HTN, DM2, d/t, s/p), (b) industry
  (build, 5.10.130, +125, TBL B, FE 2.5/5, APS, PM, NTH, NOT), (c) **house/personal shorthand**
  only defined in this file (invented). Tier (c) is the "AI can't decode alone" layer.
- **UW personas**: ~10–12 underwriters with style params (sentence completeness, abbreviation
  density by tier, typo rate, arithmetic error rate, omission rate, leniency bias on grey
  areas, worksheet format A/B/C/D, timestamp habits).
- ✅ Gate: each dictionary validates; cross-refs resolve (every MIB/Rx code used by an
  impairment chapter exists).

### Phase 3 — Case design (coverage matrix)
- Dimensions: age band, sex, state/country, citizenship/foreign national, occupation risk,
  income/face amount (drives requirements), tobacco status & type & recency, build band,
  BP/lipid band, # impairments (0–4) × type × severity, family history, MVR, avocations/aviation,
  travel, **disclosure pattern** (honest / omitted / contradicted by Rx/MIB/APS / misremembered),
  **complexity tier** (simple / moderate / complex / grey-area), **evidence path**
  (app+3rd-party only / + labs / + APS / + both / staggered arrivals).
- Method: pairwise covering array on key dims + quotas so each final class has ≥ N cases and
  each impairment appears in ≥ M cases; remainder randomized. Seeded.
- Output `data/design/matrix.csv` (~1000 rows) + coverage report.
- ✅ Gate: coverage report shows all quotas met; reviewed by user.

### Phase 4 — Person + evidence generation (batches of 50–100)
- `gen_truth.py` → latent profile from matrix row (demographics via faker, conditions with
  onset dates/treatment/control, true lab values).
- `gen_evidence.py` → Part 1, Part 2 (answers distorted per disclosure pattern), MVR, Rx
  (true meds + distractors), MIB (codes from prior apps/3rd parties; incomplete; sparse for
  foreign nationals), labs (only if requirements grid or UW triggers order them), with
  irrelevant findings sprinkled in.
- **APS** (free text, varied formats: SOAP progress notes, discharge summaries, specialist
  letters, lab printouts, handwritten-style transcriptions; 1–10 pages). Generated from a
  structured APS spec (visits, findings, meds) built by code, then rendered to prose either by
  templates or Bedrock LLM (see Decisions). Batches of ~20.
- Staggering: evidence gets arrival timestamps so notes can be written incrementally.
- **Vendor profiles** (`reference/vendors.yaml`): ~3–4 lab vendors (flagging on/off, panel
  grouping, units, legacy test methods by date), ~3 Rx/MIB/MVR report layouts, ~6–8 APS
  practice/EMR styles.
- `extract.py` → source doc → vendor-specific JSON with OCR noise (rates per source type:
  low for labs, higher for APS/scans) + `extraction_loss.json` log.
- ✅ Gate per batch: schema validation; truth↔evidence consistency checks (every undisclosed
  condition has a discoverable trace in ≥1 source unless deliberately "hidden"); spot-check 3.

### Phase 5 — Golden decisions (Step 4, done BEFORE noisy notes)
- `engine.py` applies `rules/` to evidence in arrival order: preliminary class from app →
  adjustments from 3rd-party → requirement ordering → final from labs/APS. Emits a trace:
  each fact used, rule ID cited, debits/credits, ruled-out items, irrelevant evidence noted
  as irrelevant, final class/table/flat extra/riders allowed/declined, and **grey-area flags
  with acceptable alternative outcomes**.
- `render_golden.py` → clean narrative markdown from the trace (templated, optionally LLM
  polished under a "no new facts" constraint, verified by fact-matching against trace).
- ✅ Gate: engine determinism; distribution of final classes vs. design targets; 10 manual
  reviews against `guidelines.md`.

### Phase 6 — Noisy UW notes (Step 3)
- Each case assigned a persona. Renderer takes golden trace →
  - **Observations**: staggered entries per evidence arrival ("11/2 app rcvd… 11/6 Rx back,
    metformin ?DM not discl, ord A1c"), some sentences, many fragments.
  - **Worksheet**: persona's format (debit grid, shorthand list, freeform math, partial).
- Corruptions (all logged to `notes/case_XXXX.corruptions.json`): abbreviation substitution
  by tier, dropped steps, unstated assumptions, typos, wrong arithmetic, occasional wrong final
  call (labeled), rider codes, grey-area divergence (persona leniency picks an alternative).
- Mostly template + stochastic rewriting in code; LLM only for a style-variation pass in
  batches if chosen (see Decisions).
- ✅ Gate: every notes file traces back to its golden; corruption rates match persona params.

### Phase 7 — QA & adversarial baseline
- Full validation sweep; coverage + class distribution report; random 2% human-style review.
- **Baseline test**: give a foundation model notes (+/- evidence) and ask for the decision &
  rationale; score vs. golden. Confirms the noise is actually hard. Tune corruption if too easy.

### Phase 8 — Packaging
- JSONL records `{case_id, extracted_json, noisy_notes, golden_decision, golden_narrative,
  corruption_log, extraction_loss, persona_id, vendor_ids, template_ids}` (source docs kept
  alongside). **No split at generation time** — splitting happens later, possibly several
  random/grouped re-splits. Persona/vendor/template IDs are kept so splits can be grouped to
  avoid leakage through shared style. Dataset card documents generation and limitations.

---

## Context / session strategy
- One phase (or one sub-step for Phases 1–2) per session. End each with a `STATUS.md` update:
  what's done, files produced, gate result, next step, open issues.
- Never load full datasets into context — use scripts that print summaries/reports.
- Large reference docs (guidelines, codebook) are written section by section, each section
  appended and checkpointed.
- Batches of 50–100 cases for generation; validators run after every batch.
- Compact or restart between phases; the next session needs only PLAN.md + STATUS.md +
  the specific reference files that phase touches.

## Decisions
- Evidence: source docs (pretend PDFs) → noisy vendor-specific extracted JSON. (decided)
- Splits: not done at generation; re-split later as needed. (decided)
- Count: ~1000 cases. (decided)
- LLM: AWS Bedrock (Amazon Nova models) from scripts, tiered by task (decided, pending access):
  - Nova Pro: APS narratives, complex/grey-area golden narrative polish, baseline test.
  - Nova Lite: note style-variation pass, simple APS, vendor-format rendering.
  - Nova Micro: cheap paraphrase/noise passes, quick validation checks.
  - Structured data always by seeded Python; LLM output always fact-checked against spec.
  - Auth: the `AWS_BEARER_TOKEN_BEDROCK` in ~/projects/prompt_optimization/.env was rejected
    ("API Key is valid?") on 2026-11-09 — needs a fresh key or a profile/role.

## Risk-class taxonomy (decided 2026-11-09)
Principle: every class has explicit entry criteria AND explicit knockouts, so any case can be
explained as "in X because…, not in X+1 because…". Two independent axes + modifiers:

**Non-tobacco ladder**
| Class | Basis |
|---|---|
| Elite (Super Preferred) | All Pref Plus criteria at tightest thresholds, zero debits, no knockouts, age/amount limits |
| Preferred Plus | Criteria matrix (build, BP, lipids, FH, MVR, avocation, tobacco-free 5 yr) |
| Preferred | Looser matrix thresholds; tobacco-free 3 yr |
| Standard Plus | Misses Preferred on ≤1–2 named criteria; tobacco-free 2 yr |
| Standard | Net debits 0–+25 (or fails Std Plus) |
| Table 1–16 (A–P) | Net debits: +26–50 → T2 (+50%)… each table = +25% of std premium |
| Postpone | Time-based: recent event/surgery/pending workup/pregnancy; re-apply date stated |
| Decline | Net debits > +400 or listed decline impairments |

**Tobacco ladder** (any nicotine/tobacco within 12 mo, or positive cotinine)
Preferred Tobacco → Standard Tobacco → Table Tobacco 1–16 → Postpone/Decline.
Hard rule: admitted cigarettes within 12 mo or cotinine+ caps best class at Standard Tobacco
unless the cigar/vape exceptions apply as written in the guideline.

**Modifiers (stack on any class)**: flat extras ($/1000, temporary or permanent: aviation,
avocation, occupation, foreign travel, recent cancer), rider eligibility/denial, exclusion
endorsements where permitted.

"Substandard" is not a separate class: it is the umbrella term for Table 1–16 and/or flat
extras. "Table rated" = Std premium + 25% × table number.

## LLM cost plan (Bedrock, us-east-1 on-demand; $/1M tokens in/out — verify on AWS pricing page)
Nova Micro 0.035/0.14 · Nova Lite 0.06/0.24 · Nova 2 Lite 0.30/2.50 · Nova Pro 0.80/3.20
Guideline, dictionaries, schemas, generators are authored in Claude Code — $0 Bedrock.
Structured docs (app, MVR, Rx, MIB, labs) are rendered by code — $0.

| Task | Model | Volume | Est. |
|---|---|---|---|
| APS narratives, complex | Pro | ~200 docs × 2.5K in / 4K out | ~$3.00 |
| APS narratives, simple | Lite | ~400 docs × 2.5K / 2.5K | ~$0.35 |
| Golden narrative polish | Lite (Pro for ~150 grey-area) | 1000 × 3K / 1.2K | ~$1.40 |
| Noisy-notes style pass | Lite | 1000 × 2.5K / 1K | ~$0.40 |
| Fact-check LLM text vs spec | Micro | ~2000 × 4K / 0.3K | ~$0.40 |
| Adversarial baseline | Pro | 200 × 6K / 1K | ~$1.60 |
| **Subtotal** | | | **~$7** |
| ×2 for retries, pilots, re-runs | | | **~$15** |
| Worst case: everything on Pro, ×2 | | | ~$40 |

Guardrails (built in Phase 0, `src/llm.py`):
- Every call goes through one wrapper: logs tokens + $ to `qa/usage.jsonl`.
- `--dry-run` estimates cost of a batch before sending; a batch over its estimate ×1.5 aborts.
- Hard caps: per-batch $2, per-session $5, global $25 (env-overridable; stops, never warns-and-continues).
- Pilot first: 10 cases per LLM step to measure real token use and compare Lite vs Pro quality
  (APS especially) before running the full 1000. Re-estimate after the pilot.
- `python src/llm.py --spent` prints running total.
- Option later: Bedrock batch inference (~50% off) for the big APS/notes runs.
