# AI Prompts — Data Generation

Evidence log for Cursor interactions on sample data generation. Each entry documents a real session from the project transcript.

---

## Interaction 1 — Implement sample data generation (2026-08-15)

### 1. Prompt sent

> Now implement the sample data generation component.
>
> Before coding: inspect the existing project; read requirements-analysis.md, data-model.md, data-quality-strategy.md; follow Cursor rules.
>
> Create `src/data_generation/generate_sample_data.py` and update `DATA_GENERATION_NOTES.md`.
>
> Generate customers.csv, orders.csv, products.csv with ~10,000 customers, ~500 products, ~100,000 orders.
>
> Inject mandatory defects: 50 NULL emails, 10 duplicate customer_id, 100 NULL customer_id, 200 NULL product_id, 50 invalid customer_id, 30 invalid product_id, 20 duplicate order_id.
>
> Use fixed random seed; validate defect counts after generation; fail loudly on mismatch.

### 2. Purpose

Produce deterministic source CSVs with exact intentional quality defects for Silver testing.

### 3. Cursor response summary

Cursor read design docs and implemented `generate_sample_data.py` with modular generators, `DEFECT_COUNTS` dataclass, post-generation `validate_defect_counts()`, and CLI (`--output-dir`, `--seed`). Regenerated CSVs with seed 42. Added `tests/test_data_generation.py` (4 tests). Updated `DATA_GENERATION_NOTES.md` and marked Phase 1 complete in `task-breakdown.md`.

### 4. What was accepted

- Fixed seed 42 for reproducibility
- Modular generator functions per entity
- Post-generation validation that raises `DataGenerationValidationError` on mismatch
- Exact defect injection counts from requirements §6.4
- CLI arguments for output directory and seed

### 5. What was rejected

- Manual CSV editing to fix defects (generator must be the source of truth)
- Skipping post-generation validation
- Uncontrolled random defects beyond the specified counts

### 6. What was modified manually

No manual CSV edits. Generator was re-run after a file-write fix during the session (transcript shows a re-run after a file fix, not manual data changes).

### 7. Why the decision was made

Deterministic seed + programmatic defect injection ensures Silver tests can assert exact counts. Validation at generation time catches regressions before Bronze ingestion.

### 8. Validation performed

```bash
python src/data_generation/generate_sample_data.py --output-dir data --seed 42
python -m pytest tests/test_data_generation.py -v
```

**Result:** customers 10,010 / products 500 / orders 100,020 rows; all mandatory defect counts matched.

### 9. Result

Phase 1 complete. CSVs committed under `data/`.

---

## Interaction 2 — Senior review of generated sample data (2026-08-15)

### 1. Prompt sent

> Review the generated sample data as a senior data engineer. Do not blindly assume the generator is correct.
>
> Run automated validation for: row counts, column names, null counts, duplicate PKs, orphan FKs, invalid values, date ranges, financial calculations, expected intentional issue counts.
>
> Create a validation report. If unexpected quality issues exist, fix the generator rather than manually editing CSVs. Then regenerate. Update DATA_GENERATION_NOTES.md. Do not proceed if validation fails.

### 2. Purpose

Independent verification that committed CSVs match assignment requirements before pipeline implementation proceeds.

### 3. Cursor response summary

Cursor created `src/data_generation/validate_sample_data.py` — an independent CSV validator that reads files from disk without trusting the generator's internal checks. Implemented 34 automated checks across row counts, schema, nulls, duplicates, orphan FKs, date ranges, financial calculations, and intentional defect counts. Ran validation, produced report, updated `DATA_GENERATION_NOTES.md`.

### 4. What was accepted

- Independent validator separate from generator
- Fix generator (not CSVs) if validation fails
- Comprehensive check categories (9 areas from prompt)
- Validation report as deliverable

### 5. What was rejected

- Trusting only the generator's built-in `validate_defect_counts()` as sufficient senior review
- Proceeding with unvalidated data
- Manual CSV patching

### 6. What was modified manually

None to CSV data. Validator script was added; `DATA_GENERATION_NOTES.md` updated with validation results and known limitations.

### 7. Why the decision was made

Senior review requires an alternate verification path — reading raw CSVs independently mirrors how a reviewer would audit production data.

### 8. Validation performed

```bash
python src/data_generation/validate_sample_data.py --data-dir data --output-dir data
```

**Result:** All 34 checks PASS on seed-42 CSVs. No generator fixes required.

### 9. Result

Sample data approved for Bronze/Silver implementation. Validator later integrated into pytest (`tests/data_generation/test_intentional_defects.py`).
