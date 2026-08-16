# Databricks End-to-End Validation Runbook

Use this checklist to verify **AC-01**, **AC-07**, and **AC-08** on a live Databricks workspace.
Local pytest and validation scripts do not substitute for this run.

## Prerequisites

- Databricks workspace with Unity Catalog (or Hive metastore)
- Permissions to create schemas `bronze`, `silver`, `gold`
- Repo cloned or files uploaded to workspace
- Sample CSVs in `data/` (or regenerate with seed 42)

## 1. Configure workspace paths

Set environment variables or widget parameters:

```text
CATALOG=main          # or your catalog
DATA_PATH=/Workspace/Users/<you>/databricks-medallion-pipeline/data
```

## 2. Bronze — Delta ingest (AC-01, BR-07)

```python
# Databricks notebook cell
%run ./src/bronze/ingest_all.py
```

Verify:

```sql
SELECT 'customers' AS entity, COUNT(*) AS rows FROM bronze.customers
UNION ALL SELECT 'products', COUNT(*) FROM bronze.products
UNION ALL SELECT 'orders', COUNT(*) FROM bronze.orders;
-- Expected: 10010, 500, 100020

SELECT COUNT(*) AS null_customer_id
FROM bronze.orders WHERE customer_id IS NULL;
-- Expected: 100
```

Record ingest logs: row counts and `_source_file` populated on all tables.

## 3. Silver — quality framework (AC-04)

```python
%run ./src/silver/create_silver_tables.py
```

Verify:

```sql
SELECT entity, total_records, valid_records, invalid_records
FROM silver.data_quality_metrics
ORDER BY entity;
-- Expected invalid totals: customers=70, products=210, orders=420 (sum=700)

SELECT issue_code, issue_count
FROM silver.data_quality_summary
WHERE issue_count > 0
ORDER BY issue_code;
```

## 4. Gold — aggregations (AC-06)

```python
%run ./src/gold/create_gold_tables.py
```

Verify:

```sql
SELECT COUNT(*) FROM gold.sales_by_product;      -- valid products with orders
SELECT COUNT(*) FROM gold.revenue_by_customer;   -- 9940
SELECT COUNT(*) FROM gold.daily_weekly_trends WHERE trend_grain = 'DAILY';
SELECT * FROM gold.customer_segmentation ORDER BY segment_type;
```

## 5. Dashboard SQL (AC-07, DB-05)

1. Open **SQL** → **SQL Editor**
2. Paste queries from `src/dashboard/dashboard_queries.sql` one at a time
3. Confirm each returns rows without error
4. Create a **Lakeview / SQL Dashboard** per `src/dashboard/DASHBOARD_GUIDE.md`
5. Save dashboard URL and screenshot for submission evidence

## 6. Sign-off template

| Step | Pass/Fail | Evidence |
|------|-----------|----------|
| Bronze row counts | | Query output / notebook log |
| Silver invalid sum ≈ 700 | | `data_quality_metrics` |
| Gold four tables | | `SHOW TABLES IN gold` |
| Dashboard queries | | Screenshot or dashboard URL |
| End-to-end job (optional) | | Job run ID |

**Validated by:** _______________  
**Date:** _______________  
**Workspace URL:** _______________
