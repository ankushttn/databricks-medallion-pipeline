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
