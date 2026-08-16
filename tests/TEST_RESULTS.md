# Test Results

**Run date:** 2026-08-16 (acceptance-report fixes)  
**Command:** `python -m pytest tests/ -q`  
**Result:** **123 passed** in 566s (~9m 26s)  
**Environment:** Windows, Python 3.10.9, PySpark local[1]

## Summary by layer

| Layer | Tests | Status |
|-------|-------|--------|
| Data generation | 9 | PASS |
| Intentional defects (CSV validator) | 4 | PASS |
| Bronze config + Spark read + Delta write | 17 | PASS |
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
| Integration (end-to-end) | 6 | PASS |
| Common (config validation) | 8 | PASS |

## Business outcomes verified

- Sample data: 10,010 customers, 500 products, 100,020 orders (seed 42)
- Mandatory §6.4 defects detected in Silver
- **700 invalid Silver rows** (70 customers + 210 products + 420 orders)
- 210 supplementary `business:price_below_cost` product defects
- Gold reconciliation 11/11 PASS
- Dashboard SQL validation 12/12 PASS (local)

## Changes from prior run

- Added 210 supplementary product `price_below_cost` defects to meet ~700-row target
- Added Bronze Delta format unit tests (`test_bronze_delta_write.py`)
- Added integration test `test_silver_total_invalid_rows_near_assignment_target`
- Fixed Gold reconciliation comparator for invalid-product exclusion
