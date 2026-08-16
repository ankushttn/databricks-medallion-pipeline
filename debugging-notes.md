# Debugging Notes

Log issues encountered during development and their resolutions.

## Template

### [YYYY-MM-DD] — Short title

**Layer:** Bronze | Silver | Gold | Dashboard | Infrastructure  
**Symptom:** _What went wrong?_  
**Root cause:** _Why did it happen?_  
**Fix:** _What changed?_  
**Files affected:** _List paths_  
**Prevention:** _How to avoid recurrence_

---

## Issues

### [2026-08-16] — Silver local validation: duplicate key row counts vs injection counts

**Layer:** Silver  
**Symptom:** Uniqueness checks report 20 flagged `customer_id` rows and 40 flagged `order_id` rows, while data generation injects 10 and 20 duplicate *rows* respectively.  
**Root cause:** By design, uniqueness flags **every row sharing a duplicated primary key**, not only the appended copy. Ten injected duplicate customer rows create 10 keys with count=2 → 20 flagged rows. Twenty injected duplicate order rows → 40 flagged rows.  
**Fix:** No code change required. Validation script documents `>= expected` for uniqueness checks.  
**Files affected:** `src/silver/validate_silver_local.py`, `data/SILVER_QUALITY_REPORT.md`  
**Prevention:** When interpreting uniqueness metrics, distinguish *injected duplicate rows* from *flagged row count* (always ≥ injection count).

### [2026-08-16] — Silver validation completed; all mandatory defects detected

**Layer:** Silver  
**Symptom:** N/A — validation run requested.  
**Root cause:** N/A  
**Fix:** Executed `validate_silver_local.py` against `data/*.csv`. All seven mandatory defect categories matched expected counts. Type and business-rule checks passed with zero failures on clean generated data (products) and no spurious order/customer failures.  
**Files affected:** `data/SILVER_QUALITY_REPORT.md`, `data/SILVER_QUALITY_REPORT.json`, `src/silver/validate_silver_local.py`  
**Prevention:** Re-run `python src/silver/validate_silver_local.py` after any change to checks or sample data.

### [2026-08-16] — Gold segmentation: Inactive segment empty on sample data

**Layer:** Gold  
**Symptom:** `gold.customer_segmentation` has 3 rows (High-Value, Repeat, One-Time) — no Inactive.  
**Root cause:** All 9,940 valid customers have at least one valid order. Invalid customers (70) are excluded from Gold.  
**Fix:** No code change. Validation updated from "must have 4 segments" to "at most 4 allowed segment types."  
**Files affected:** `src/gold/validations.py`, `src/gold/GOLD_ARCHITECTURE.md`  
**Prevention:** Empty behavioral segments are valid; do not require zero-count segment rows.

### [2026-08-16] — Gold revenue_by_customer order count vs trends

**Layer:** Gold  
**Symptom:** `SUM(total_orders)` in `revenue_by_customer` (99,003) < valid orders (99,600).  
**Root cause:** 597 valid orders reference customers that failed Silver validation (duplicate PK, etc.). These orders appear in product/trend Gold tables but not customer attribution.  
**Fix:** By design — customer Gold requires valid customer dimension. Documented in `GOLD_ARCHITECTURE.md`.  
**Files affected:** `src/gold/GOLD_ARCHITECTURE.md`, `data/GOLD_VALIDATION_REPORT.md`  
**Prevention:** Expected when invalid customers have valid-looking order rows.

### [2026-08-16] — Gold reconciliation: trends compare false failures (Decimal join)

**Layer:** Gold  
**Symptom:** Initial reconciliation reported 1,824 daily-trend metric mismatches despite Gold SQL appearing correct.  
**Root cause:** Reconciliation compared Gold vs independent aggregates using Python dict keys with mixed `Decimal`/`float` types and non-deterministic row ordering — not a Gold logic bug.  
**Fix:** Rewrote comparison to use Spark joins with explicit `DecimalType(18,2)` casting and key-based anti-joins for missing rows.  
**Files affected:** `src/gold/reconciliation.py`, `tests/test_gold_reconciliation.py`  
**Prevention:** Always reconcile monetary metrics in Spark with aligned decimal types; avoid `collect()` + Python float equality for revenue.

### [2026-08-16] — Gold reconciliation JSON export: Decimal not JSON serializable

**Layer:** Gold  
**Symptom:** `reconcile_gold_local.py` wrote markdown report but crashed on `GOLD_RECONCILIATION_REPORT.json` with `TypeError: Decimal is not JSON serializable`.  
**Root cause:** `EntityTrace` and reconciliation summary rows contain `Decimal` values from Spark aggregates; `json.dumps` has no default handler.  
**Fix:** Added `default=str` to `json.dumps` in `reconcile_gold_local.py`.  
**Files affected:** `src/gold/reconcile_gold_local.py`  
**Prevention:** Use `default=str` or explicit float conversion for any Spark-derived JSON export.

### [2026-08-16] — Gold senior reconciliation completed; all checks PASS

**Layer:** Gold  
**Symptom:** N/A — senior-level validation requested.  
**Root cause:** N/A  
**Fix:** Implemented independent reconciliation (`src/gold/reconciliation.py`, `reconcile_gold_local.py`, `tests/test_gold_reconciliation.py`). Alternate methods: deduplicated order facts, semi-joins, Python `classify_segment()`. All 11 reconciliation checks PASS. Five product traces (83, 121, 197, 236, 469) and five customer traces (1, 10, 866, 1966, 264) PASS Bronze → Silver → Gold. Pytest: 17/17 passed (`test_gold_reconciliation.py` + `test_gold_aggregations.py`).  
**Files affected:** `data/GOLD_RECONCILIATION_REPORT.md`, `data/GOLD_RECONCILIATION_REPORT.json`, `src/gold/reconciliation.py`, `src/gold/reconcile_gold_local.py`, `tests/test_gold_reconciliation.py`  
**Prevention:** Re-run `python src/gold/reconcile_gold_local.py` after any Gold SQL or Silver validity rule change.

### [2026-08-16] — Production-readiness: logging, exceptions, config validation

**Layer:** Infrastructure (Bronze, Silver, Gold, common)  
**Symptom:** N/A — production-readiness review requested.  
**Root cause:** Gaps in config fail-fast validation, inconsistent pipeline start/end logging, broad `except Exception` handlers, silent CSV header skip when file missing.  
**Fix:** Added `src/common/pipeline_utils.py` (logging, timing, config validation), `ERROR_HANDLING.md`. Narrowed exception handlers in Bronze ingest, data generation, dashboard validation. Added empty-dataset warnings, elapsed-time logging, Gold validation SQL error logging with `exc_info`. Config loaders now validate write_mode and schema names; Bronze validates local source directory.  
**Files affected:** `src/common/pipeline_utils.py`, `src/bronze/config.py`, `src/bronze/ingest_utils.py`, `src/silver/config.py`, `src/silver/quality_engine.py`, `src/silver/create_silver_tables.py`, `src/gold/config.py`, `src/gold/gold_engine.py`, `src/gold/create_gold_tables.py`, `src/data_generation/generate_sample_data.py`, `src/data_generation/validate_sample_data.py`, `src/dashboard/validate_dashboard_local.py`, `tests/common/test_pipeline_utils.py`, `tests/bronze/test_bronze_config.py`, `ERROR_HANDLING.md`  
**Prevention:** Follow `ERROR_HANDLING.md`; run `python -m pytest tests/ -v` after pipeline changes (120 tests).
