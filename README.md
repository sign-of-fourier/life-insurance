# agentic_uw — synthetic life-underwriting corpus

Generates ~1000 synthetic life-insurance cases: application + evidence (source docs and noisy
OCR-style extracted JSON) → noisy human underwriter notes, paired with a golden, fully-traced
decision. Start with `PROJECT_OVERVIEW.md`; see also `PLAN.md` (design), `STATUS.md` (progress), `EXPERIMENTS.md`, `CHECKPOINT.md`.

## Layout
- `src/schemas.py`  data contracts for every layer (Truth → Evidence → Extracted → Golden → Notes)
- `src/validate.py` cross-layer integrity checks
- `src/llm.py`      the only path to Bedrock; logs cost to `qa/usage.jsonl`, hard caps
- `src/selftest.py` Phase 0 gate: `python src/selftest.py`
- `reference/` guideline + dictionaries · `rules/` machine-readable guideline tables
- `data/` generated cases · `qa/` reports, usage log

## Cost controls
`python src/llm.py --spent` · `--estimate MODEL IN OUT N` · caps via `UW_CAP_BATCH` (2),
`UW_CAP_SESSION` (5), `UW_CAP_GLOBAL` (25). Calls are refused before sending if the
worst-case cost would cross any cap. Key: `AWS_BEARER_TOKEN_BEDROCK` in `.env` (gitignored).
