# AI Prompts — Debugging

Evidence log for debugging sessions, validation failures, and AI suggestion rejections. Cross-references `debugging-notes.md`.

---

## Interaction 1 — Silver uniqueness flagged-row semantics (2026-08-16)

### 1. Prompt sent

_(Implicit — discovered during Silver validation session)_

> Execute complete Silver-layer validation and investigate any unexpected failures.

### 2. Purpose

Confirm mandatory defect counts; understand uniqueness metrics.

### 3. Cursor response summary

Cursor reported uniqueness checks showing 20 flagged `customer_id` rows and 40 flagged `order_id` rows vs 10 and 20 injected duplicate rows respectively.

### 4. What was accepted

- No code change — behavior is correct by design
- `>= expected` comparison for uniqueness in validation script
- Documentation in `debugging-notes.md` and `SILVER_QUALITY_REPORT.md`

### 5. What was rejected

- Changing uniqueness logic to flag only the "copy" row
- Treating 20/40 flagged rows as a validation failure

### 6. What was modified manually

Validation script documentation only.

### 7. Why the decision was made

Uniqueness flags **every row sharing a duplicated PK**. Ten injected duplicate customer rows → 10 keys × 2 rows = 20 flagged.

### 8. Validation performed

`python src/silver/validate_silver_local.py --data-dir data --output-dir data`

### 9. Result

Silver validation PASS. Interpretation documented.

---

## Interaction 2 — Gold Inactive segment empty (2026-08-16)

### 1. Prompt sent

_(Implicit — discovered during Gold validation)_

### 2. Purpose

Explain why `customer_segmentation` has 3 rows, not 4.

### 3. Cursor response summary

All 9,940 valid customers have ≥1 valid order. Invalid customers (70) excluded from Gold. Inactive segment legitimately empty.

### 4. What was accepted

- No Gold SQL change
- Validation rule: "at most 4 allowed segment types" (not "must have 4 rows")

### 5. What was rejected

- Forcing an Inactive segment row with zero customers
- Treating missing Inactive as a Gold bug

### 6. What was modified manually

`src/gold/validations.py`, `GOLD_ARCHITECTURE.md`

### 7. Why the decision was made

Segmentation logic is correct; sample data simply has no valid customers with zero orders.

### 8. Validation performed

`python src/gold/validate_gold_local.py --data-dir data --output-dir data`

### 9. Result

Gold validation PASS with 3 segments documented.

---

## Interaction 3 — Gold reconciliation false failures (2026-08-16)

### 1. Prompt sent

> Perform senior-level Gold validation with independent alternate-path calculations.

### 2. Purpose

Verify Gold aggregations are correct.

### 3. Cursor response summary

Initial reconciliation reported 1,824 daily-trend metric mismatches. Cursor investigated and concluded Gold SQL was correct; reconciliation `compare_dataframes()` had Decimal/float type mismatch from `collect()` + Python dict comparison.

### 4. What was accepted

- Rewrote comparison to Spark joins with explicit decimal casting
- Kept Gold SQL unchanged

### 5. What was rejected

- Modifying Gold SQL to match broken reconciler output
- Accepting reconciliation PASS without fixing comparison logic

### 6. What was modified manually

`src/gold/reconciliation.py` — multiple comparison rewrites.

### 7. Why the decision was made

Reconciliation tooling must be as rigorous as production code. Type-aligned Spark joins are the correct comparison method for monetary metrics.

### 8. Validation performed

```bash
python -m pytest tests/test_gold_reconciliation.py -v
python src/gold/reconcile_gold_local.py --data-dir data --output-dir data
```

### 9. Result

All reconciliation checks PASS. Documented in `debugging-notes.md`.

---

## Interaction 4 — JSON Decimal serialization (2026-08-16)

### 1. Prompt sent

_(Discovered during reconciliation report generation)_

### 2. Purpose

Export reconciliation results to JSON.

### 3. Cursor response summary

`reconcile_gold_local.py` wrote markdown but crashed on JSON with `TypeError: Decimal is not JSON serializable`.

### 4. What was accepted

`default=str` in `json.dumps`

### 5. What was rejected

Dropping Decimal precision fields from export

### 6. What was modified manually

`src/gold/reconcile_gold_local.py`

### 7. Why the decision was made

Simple, safe serialization for audit reports without custom encoders.

### 8. Validation performed

Re-ran `reconcile_gold_local.py` — both `.md` and `.json` written.

### 9. Result

JSON export fixed.

---

## Interaction 5 — Dashboard validator signature mismatch (2026-08-16)

### 1. Prompt sent

_(Discovered during dashboard local validation)_

### 2. Purpose

Run dashboard queries against local Gold temp views.

### 3. Cursor response summary

First `validate_dashboard_local.py` run failed — `build_silver_tables()` called without required `validated_at` argument.

### 4. What was accepted

Fix call signature to match `validate_gold_local.py` pattern

### 5. What was rejected

Stubbing out Silver build step

### 6. What was modified manually

`src/dashboard/validate_dashboard_local.py`

### 7. Why the decision was made

Dashboard validation must use the same Silver→Gold path as other validators.

### 8. Validation performed

`python src/dashboard/validate_dashboard_local.py --data-dir data --output-dir data`

### 9. Result

12/12 queries PASS.

---

## Interaction 6 — PySpark worker crash on Windows (2026-08-16)

### 1. Prompt sent

> Create meaningful automated testing strategy. Run tests. Fix failures caused by implementation defects.

### 2. Purpose

Full pytest suite across all layers.

### 3. Cursor response summary

Initial full run: 22 failures. Root cause: Python worker version mismatch (driver 3.10 vs worker 3.13) causing `PySparkRuntimeError: Python worker failed to connect back`. Secondary issue: Spark session exhaustion from test ordering.

### 4. What was accepted

- `PYSPARK_PYTHON` and `PYSPARK_DRIVER_PYTHON` pinned to `sys.executable` in `conftest.py`
- Test collection reordering (Silver before Gold/Dashboard/Integration)
- Replace fragile `collect()` with `filter().count()` in dimension tests

### 5. What was rejected

- Marking tests as xfail/skipped on Windows
- Blaming Silver/Gold implementation for worker crashes

### 6. What was modified manually

`tests/conftest.py`, multiple Silver test files, `pytest_collection_modifyitems` hook.

### 7. Why the decision was made

Failures were infrastructure/test-harness issues, not pipeline logic bugs. Pinning Python executable is standard Windows PySpark fix.

### 8. Validation performed

```bash
python -m pytest tests/ -v
```

**Result:** 109/109 PASS (later 120/120 after production-readiness tests added).

### 9. Result

Reliable local test execution on Windows documented in `tests/TEST_RESULTS.md`.

---

## Interaction 7 — Production-readiness review (2026-08-16)

### 1. Prompt sent

> Perform a production-readiness review. Focus on logging, exception handling, configuration, input validation. Do NOT hide exceptions with broad empty except blocks. Document error-handling strategy. Run tests after changes.

### 2. Purpose

Harden pipeline for production patterns without changing business logic.

### 3. Cursor response summary

Created `src/common/pipeline_utils.py`, `ERROR_HANDLING.md`. Narrowed Bronze exception handlers. Added config validation, pipeline start/end logging, empty-dataset warnings. Fixed Gold `pipeline_timer` marking SUCCESS on validation failure (now raises `GoldBuildError`). Fixed `setup_logging` recursion in Bronze (aliased `configure_pipeline_logging`).

### 4. What was accepted

- Shared logging/timing utilities
- Fail-fast config validation
- Specific exception types in Bronze ingest
- `ERROR_HANDLING.md` strategy document

### 5. What was rejected

- Broad `except Exception: pass` patterns
- Silent CSV header skip on missing files
- Logging success when Gold validation failed

### 6. What was modified manually

Multiple files across Bronze/Silver/Gold/common — see `debugging-notes.md` production-readiness entry.

### 7. Why the decision was made

Production pipelines need observable failures and consistent logging. Business logic unchanged; operational quality improved.

### 8. Validation performed

```bash
python -m pytest tests/ -v
```

**Result:** 120/120 PASS in ~8m 48s.

### 9. Result

Production-readiness improvements merged. `tests/common/test_pipeline_utils.py` added (8 tests).

---

## Interaction 8 — AI/Cursor evidence documentation (2026-08-16)

### 1. Prompt sent

> Create complete AI/Cursor evidence documentation. Update all ai-prompts/*.md and cursor-workflow/*.md files. Document prompt, purpose, response, accepted/rejected, manual changes, rationale, validation, result. Do NOT fabricate. Only document interactions that actually occurred.

### 2. Purpose

Demonstrate persistent project context, iterative development, validation, debugging, rejection of incorrect AI suggestions, and refinement of AI-generated code.

### 3. Cursor response summary

_(This document and sibling `ai-prompts/*.md` files — sourced from agent transcript `50551ecf-026a-4549-8321-588606fc1847.jsonl`.)_

### 4. What was accepted

- Structured 9-field interaction records per major session
- Honest verification boundaries (local vs Databricks)
- Cross-references to `debugging-notes.md` and test results

### 5. What was rejected

- Fabricated Cursor responses or interactions
- Claiming Databricks end-to-end execution was verified

### 6. What was modified manually

All `ai-prompts/*.md` and `cursor-workflow/*.md` files updated in this session.

### 7. Why the decision was made

Assignment requires auditable AI usage evidence with real prompts and outcomes.

### 8. Validation performed

Cross-checked against agent transcript and existing validation reports.

### 9. Result

Complete evidence documentation package.
