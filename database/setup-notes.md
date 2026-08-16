# Database Setup Notes

## Databricks Configuration

1. Create catalogs/schemas: `bronze`, `silver`, `gold` (or use a single catalog with three schemas).
2. Grant appropriate permissions to the pipeline service principal or user.
3. Configure a DBFS or Unity Catalog volume path for raw CSV staging if needed.

## Local Development

- CSV files live in `data/` and are read by Bronze ingestion scripts.
- Delta tables are created at runtime on Databricks — no local metastore required.
- **Static Bronze validation (no Spark):** `python src/bronze/validate_bronze_static.py --source-base-path data`
- **Unit tests:** `pytest tests/test_bronze_ingest.py -v`
- See `src/bronze/BRONZE_EXECUTION.md` for full Databricks runbook.

## Status

_Bronze layer implemented — run on Databricks for Delta table creation._
