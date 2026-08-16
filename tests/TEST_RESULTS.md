# Test Results

**Run date:** 2026-08-16 (post production-readiness review)  
**Command:** `python -m pytest tests/ -v`  
**Result:** **120 passed** in 528s (~8m 48s)  
**Environment:** Windows, Python 3.10.9, PySpark local[1]

## Summary by layer

| Layer | Tests | Status |
|-------|-------|--------|
| Data generation | 9 | PASS |
| Intentional defects (CSV validator) | 4 | PASS |
| Bronze config + Spark read | 15 | PASS |
| Silver integration | 8 | PASS |
| Silver completeness | 5 | PASS |
| Silver uniqueness | 6 | PASS |
| Silver referential integrity | 4 | PASS |
| Silver type validation | 5 | PASS |
| Silver business rules | 8 | PASS |
| Silver metrics | 3 | PASS |
| Gold aggregations | 6 | PASS |
| Gold reconciliation | 11 | PASS |
| Gold segmentation | 8 | PASS |
| Dashboard queries | 12 | PASS |
| Integration (end-to-end) | 5 | PASS |
| Common (config validation) | 8 | PASS |

## Business outcomes verified

### Positive cases
- Valid synthetic customers, products, and orders pass dimension checks
- Clean product rows (no intentional defects) are 100% valid
- Clean order subsets pass business-rule checks
- Gold KPIs reconcile to Silver valid-order counts
- Dashboard KPI totals match `gold.daily_weekly_trends` (DAILY grain)

### Negative cases
- 50 NULL emails flagged (`completeness:email_null`)
- 100 NULL `customer_id`, 200 NULL `product_id` on orders
- 50 invalid customer FKs, 30 invalid product FKs
- 20 duplicate customer rows (40 flagged), 40 duplicate order rows (80 flagged)
- 420 invalid orders excluded from Gold aggregations
- Invalid email format, bad segment, amount mismatch, payment-date violations detected in synthetic tests

### Gold / segmentation
- Segment counts (seed 42): High-Value 9,652 / Repeat 284 / One-Time 4
- Independent reconciliation: 11 checks + 10 entity traces PASS
- `classify_segment()` priority rules verified at boundaries

## Fixes applied during test harness build

1. **Python worker mismatch (Windows):** Set `PYSPARK_PYTHON` and `PYSPARK_DRIVER_PYTHON` to `sys.executable` in `tests/conftest.py`.
2. **Test ordering:** Silver layer runs before Gold/Dashboard/Integration to reduce Spark session strain.
3. **Avoid fragile `collect()`:** Dimension tests use `filter().count()` where possible.

## Re-run

```bash
python -m pytest tests/ -v
```

Fast subset:

```bash
python -m pytest tests/ -m unit -v
```
