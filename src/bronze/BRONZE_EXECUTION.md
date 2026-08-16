# Bronze Layer — Databricks Execution Guide

**Scripts:** `src/bronze/01_ingest_*.py`, `src/bronze/ingest_all.py`  
**Static validation:** `src/bronze/validate_bronze_static.py`

---

## Prerequisites

1. Sample CSVs generated and validated (`data/customers.csv`, `products.csv`, `orders.csv`)
2. Databricks workspace with Delta Lake enabled
3. Unity Catalog (recommended) or Hive metastore
4. Cluster or serverless SQL/compute with PySpark

---

## Configuration

All paths and catalog settings are externalized — **no hardcoded environment paths in code**.

| Variable | Description | Example |
|----------|-------------|---------|
| `MEDALLION_CATALOG` | Unity Catalog name (optional) | `main` |
| `MEDALLION_BRONZE_SCHEMA` | Bronze schema | `bronze` |
| `MEDALLION_SOURCE_BASE_PATH` | CSV directory | `dbfs:/FileStore/medallion/data` |
| `MEDALLION_BRONZE_WRITE_MODE` | Delta write mode | `overwrite` |

CLI flags override environment variables: `--source-base-path`, `--catalog`, `--bronze-schema`, `--write-mode`.

---

## Step 1 — Upload Source CSVs (if not using repo `data/`)

```bash
databricks fs cp data/customers.csv dbfs:/FileStore/medallion/data/customers.csv
databricks fs cp data/products.csv  dbfs:/FileStore/medallion/data/products.csv
databricks fs cp data/orders.csv    dbfs:/FileStore/medallion/data/orders.csv
```

Or mount a Unity Catalog volume and place files there.

---

## Step 2 — Static Validation (optional, no Spark)

Run locally or on Databricks driver before ingestion:

```bash
python src/bronze/validate_bronze_static.py --source-base-path data
```

On Databricks:

```bash
python src/bronze/validate_bronze_static.py \
  --source-base-path dbfs:/FileStore/medallion/data
```

---

## Step 3 — Run Bronze Ingestion

### Option A — All entities (recommended)

```python
# Databricks notebook cell
%python
import sys
sys.path.insert(0, "/Workspace/Repos/<user>/databricks-medallion-pipeline/src")

import os
os.environ["MEDALLION_CATALOG"] = "main"
os.environ["MEDALLION_SOURCE_BASE_PATH"] = "dbfs:/FileStore/medallion/data"

from bronze.ingest_utils import configure_src_path, run_ingest_all
configure_src_path()
exit_code = run_ingest_all()
if exit_code != 0:
    raise RuntimeError("Bronze ingest_all failed")
```

Or as a shell job task:

```bash
python /Workspace/Repos/<user>/databricks-medallion-pipeline/src/bronze/ingest_all.py \
  --catalog main \
  --source-base-path dbfs:/FileStore/medallion/data \
  --write-mode overwrite
```

### Option B — Individual entities

```bash
python src/bronze/01_ingest_customers.py --catalog main --source-base-path dbfs:/FileStore/medallion/data
python src/bronze/03_ingest_products.py  --catalog main --source-base-path dbfs:/FileStore/medallion/data
python src/bronze/02_ingest_orders.py    --catalog main --source-base-path dbfs:/FileStore/medallion/data
```

Order for `ingest_all`: customers → products → orders (dependency-neutral at Bronze; matches orchestrator).

---

## Step 4 — Verify in Databricks SQL

```sql
SELECT COUNT(*) FROM main.bronze.customers;   -- expected: 10010
SELECT COUNT(*) FROM main.bronze.products;    -- expected: 500
SELECT COUNT(*) FROM main.bronze.orders;      -- expected: 100020

SELECT _source_file, _ingested_at, COUNT(*)
FROM main.bronze.customers
GROUP BY _source_file, _ingested_at;

-- Spot-check null FK preserved from source
SELECT COUNT(*) FROM main.bronze.orders WHERE customer_id IS NULL;  -- expected: 100
```

---

## Local Development Notes

- **Static tests** run without Spark: `pytest tests/test_bronze_ingest.py -v`
- **Full Delta write** requires `delta-spark` locally or a Databricks cluster
- Default local path: `--source-base-path data` (project-relative)

---

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| `BronzeSourceFileError` | CSV missing | Upload file; check `--source-base-path` |
| `BronzeIngestionError` (header) | Column mismatch | Regenerate CSVs from data generation |
| `BronzeIngestionError` (FAILFAST) | Malformed value | Fix source CSV; do not cleanse in Bronze |
| `BronzeIngestionError` (write) | Delta/catalog permissions | Check schema exists and UC grants |

---

*Last updated: 2026-08-16*
