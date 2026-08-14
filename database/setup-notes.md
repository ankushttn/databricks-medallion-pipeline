# Database Setup Notes

## Databricks Configuration

1. Create catalogs/schemas: `bronze`, `silver`, `gold` (or use a single catalog with three schemas).
2. Grant appropriate permissions to the pipeline service principal or user.
3. Configure a DBFS or Unity Catalog volume path for raw CSV staging if needed.

## Local Development

- CSV files live in `data/` and are read by Bronze ingestion scripts.
- Delta tables are created at runtime on Databricks — no local metastore required.

## Schema Application

Run `database/schema.sql` on the Databricks SQL warehouse after customizing for your catalog naming.

## Status

_Foundation phase — setup scripts not yet implemented._
