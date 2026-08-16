# AI Prompts — Silver Layer

Evidence log for Cursor interactions on Silver data quality. Each entry documents a real session from the project transcript.

---

## Interaction 1 — Silver quality framework implementation (2026-08-16)

### 1. Prompt sent

> Implement the Silver data quality framework.
>
> Before coding inspect all existing documentation and Bronze implementation.
>
> Create dimension modules `01_quality_completeness.py` through `05_quality_business_logic.py` and `create_silver_tables.py`.
>
> Design a reusable quality-check framework where practical.
>
> Each quality check should produce: source row identifier, check name, check status, quality result, failure reason, validation timestamp.
>
> Do not delete bad records.
>
> Implement completeness (email, customer_id, product_id), uniqueness (customer_id, order_id), type validation, referential integrity, and business logic checks.

### 2. Purpose

Flag ~700 intentionally problematic rows across five quality dimensions without deleting any Bronze records.

### 3. Cursor response summary

Cursor built a reusable framework:

- `quality_framework.py` — `QualityCheck`, `QualityContext`, `apply_checks_to_dataframe`, `finalize_silver_entity`
- `check_helpers.py` — shared check builders
- `quality_engine.py` — orchestrates all five dimensions
- `metrics.py` — entity metrics and `data_quality_summary` reporting
- `01`–`05` dimension modules + `create_silver_tables.py`
- `SILVER_ARCHITECTURE.md` documentation
- `tests/test_silver_quality.py` (8 tests) validating defect counts and row parity

### 4. What was accepted

- Reusable framework with per-dimension `prepare()` + `get_checks()` pattern
- `_is_valid`, `_quality_issues`, `_validated_at`, `_run_id` metadata columns
- `silver.data_quality_summary` reporting table
- Row-count parity with Bronze (no deletes)
- Orders partitioned by `order_date`
- Referential checks skip NULL FKs (completeness handles nulls separately)

### 5. What was rejected

- Deleting or filtering invalid rows from Silver output
- Single monolithic check script without dimension separation
- Silent quality failures (all issues stored in `_quality_issues` array)

### 6. What was modified manually

During implementation, Cursor fixed quality engine issues (transcript: "Fixing the quality engine and implementing dimension modules") before tests passed. No user manual edits documented.

### 7. Why the decision was made

Framework reuse keeps 48 checks consistent. Flagging (not deleting) preserves audit trail required by assignment and `data-quality-strategy.md` P-01.

### 8. Validation performed

```bash
python -m pytest tests/test_silver_quality.py tests/test_silver_metrics.py -v
```

**Result:** 8/8 Silver integration tests PASSED at time of implementation.

### 9. Result

Silver framework implemented. Local validation script added in next session.

---

## Interaction 2 — Complete Silver-layer validation (2026-08-16)

### 1. Prompt sent

> Now execute a complete Silver-layer validation.
>
> Use the generated CSVs and/or Bronze data.
>
> Verify Silver catches: 50 NULL emails, 10 duplicate customer_id, 100 NULL customer_id, 200 NULL product_id, 50 invalid customer_id, 30 invalid product_id, 20 duplicate order_id. Also verify type and business-rule checks.
>
> Produce a quality report with check_name, table_name, total_rows, passed_rows, failed_rows, pass_percentage, failure_percentage.
>
> Investigate unexpected failures. Do NOT hide failures. Fix incorrect checks, rerun, document in debugging-notes.md. Only mark Silver complete after all required intentional issues are correctly detected.

### 2. Purpose

Confirm all mandatory §6.4 defects are detected before Gold implementation.

### 3. Cursor response summary

Cursor ran `validate_silver_local.py` against `data/*.csv`, produced `data/SILVER_QUALITY_REPORT.md` and `.json`. All seven mandatory defect categories matched expected counts. Documented uniqueness flagged-row vs injected-row semantics in `debugging-notes.md` (20 flagged customer rows from 10 injected duplicates; 40 flagged order rows from 20 injected duplicates).

### 4. What was accepted

- `>= expected` comparison for uniqueness (flags all participants in a duplicate key group)
- No code change for uniqueness semantics (by design)
- Quality report as auditable artifact
- Type and business-rule checks with zero spurious failures on clean generated data

### 5. What was rejected

- Treating uniqueness flagged-row count as equal to injected duplicate-row count
- Marking Silver complete with any mandatory defect mismatch
- Hiding or downplaying validation failures

### 6. What was modified manually

None. Uniqueness interpretation documented; no check logic changed.

### 7. Why the decision was made

Uniqueness flags every row sharing a duplicated PK — correct behavior per `data-quality-strategy.md`. Validation uses `>=` for uniqueness and `==` for other dimensions.

### 8. Validation performed

```bash
python src/silver/validate_silver_local.py --data-dir data --output-dir data
```

**Result:** Run `silver-validation-001` — all mandatory defects detected. Report: `data/SILVER_QUALITY_REPORT.md`.

### 9. Result

Silver layer marked complete for quality detection. ~420 invalid orders flagged; row parity preserved (Bronze count = Silver count per entity).

---

## Iterative refinement note (automated testing, 2026-08-16)

Silver tests were expanded into per-dimension files under `tests/silver/` with positive/negative synthetic cases. Full suite: 39 Silver-related tests (integration + 5 dimension modules + metrics) — all PASS in final 120-test run.
