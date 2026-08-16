-- Medallion pipeline schema definitions.
-- See data-model.md for full entity design.

-- Unity Catalog example (adjust catalog name):
-- CREATE SCHEMA IF NOT EXISTS main.bronze;
-- CREATE SCHEMA IF NOT EXISTS main.silver;
-- CREATE SCHEMA IF NOT EXISTS main.gold;

-- Bronze tables are created by ingestion scripts (Delta saveAsTable).
-- Expected tables:
--   bronze.customers  (10,010 rows + _ingested_at, _source_file)
--   bronze.products   (500 rows)
--   bronze.orders     (100,020 rows, partitioned by order_date)

-- Example verification:
-- SELECT COUNT(*) FROM bronze.customers;
-- SELECT COUNT(*) FROM bronze.orders WHERE customer_id IS NULL;
