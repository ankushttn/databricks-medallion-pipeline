-- Medallion pipeline schema reference (Databricks / Unity Catalog).
-- Tables are created by ingestion and orchestration scripts; this file documents
-- the expected catalog structure. Adjust catalog name as needed.

-- CREATE SCHEMA IF NOT EXISTS main.bronze;
-- CREATE SCHEMA IF NOT EXISTS main.silver;
-- CREATE SCHEMA IF NOT EXISTS main.gold;

-- ---------------------------------------------------------------------------
-- Bronze (raw landing — values as read from CSV plus ingestion metadata)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS bronze.customers (
    customer_id INT,
    customer_name STRING,
    email STRING,
    country STRING,
    signup_date DATE,
    customer_segment STRING,
    lifetime_value DECIMAL(12, 2),
    _ingested_at TIMESTAMP,
    _source_file STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS bronze.products (
    product_id INT,
    product_name STRING,
    category STRING,
    price DECIMAL(10, 2),
    cost DECIMAL(10, 2),
    stock_quantity INT,
    reorder_level INT,
    _ingested_at TIMESTAMP,
    _source_file STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS bronze.orders (
    order_id INT,
    customer_id INT,
    order_date DATE,
    product_id INT,
    quantity INT,
    unit_price DECIMAL(10, 2),
    total_amount DECIMAL(12, 2),
    order_status STRING,
    payment_date DATE,
    _ingested_at TIMESTAMP,
    _source_file STRING
) USING DELTA
PARTITIONED BY (order_date);

-- ---------------------------------------------------------------------------
-- Silver (typed entities + quality metadata; row counts match Bronze)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS silver.customers (
    customer_id INT,
    customer_name STRING,
    email STRING,
    country STRING,
    signup_date DATE,
    customer_segment STRING,
    lifetime_value DECIMAL(12, 2),
    _is_valid BOOLEAN,
    _quality_issues ARRAY<STRING>,
    _validated_at TIMESTAMP,
    _ingested_at TIMESTAMP,
    _source_file STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS silver.products (
    product_id INT,
    product_name STRING,
    category STRING,
    price DECIMAL(10, 2),
    cost DECIMAL(10, 2),
    stock_quantity INT,
    reorder_level INT,
    _is_valid BOOLEAN,
    _quality_issues ARRAY<STRING>,
    _validated_at TIMESTAMP,
    _ingested_at TIMESTAMP,
    _source_file STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS silver.orders (
    order_id INT,
    customer_id INT,
    order_date DATE,
    product_id INT,
    quantity INT,
    unit_price DECIMAL(10, 2),
    total_amount DECIMAL(12, 2),
    order_status STRING,
    payment_date DATE,
    _is_valid BOOLEAN,
    _quality_issues ARRAY<STRING>,
    _validated_at TIMESTAMP,
    _ingested_at TIMESTAMP,
    _source_file STRING
) USING DELTA
PARTITIONED BY (order_date);

CREATE TABLE IF NOT EXISTS silver.data_quality_metrics (
    run_id STRING,
    entity STRING,
    total_records INT,
    valid_records INT,
    invalid_records INT,
    pass_rate_pct DECIMAL(5, 2),
    reported_at TIMESTAMP
) USING DELTA;

CREATE TABLE IF NOT EXISTS silver.data_quality_summary (
    run_id STRING,
    entity STRING,
    check_id STRING,
    check_dimension STRING,
    issue_code STRING,
    severity STRING,
    issue_count INT,
    issue_rate_pct DECIMAL(5, 2),
    check_pass_rate_pct DECIMAL(5, 2),
    total_records INT,
    valid_records INT,
    invalid_records INT,
    reported_at TIMESTAMP
) USING DELTA;

-- ---------------------------------------------------------------------------
-- Gold (business metrics — valid Silver rows only unless noted)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gold.sales_by_product (
    product_id INT,
    product_name STRING,
    category STRING,
    total_orders BIGINT,
    total_revenue DECIMAL(14, 2),
    avg_order_value DECIMAL(12, 2),
    _refreshed_at TIMESTAMP
) USING DELTA;

CREATE TABLE IF NOT EXISTS gold.revenue_by_customer (
    customer_id INT,
    customer_name STRING,
    customer_segment STRING,
    total_orders BIGINT,
    total_revenue DECIMAL(14, 2),
    lifetime_value_actual DECIMAL(14, 2),
    avg_order_value DECIMAL(12, 2),
    _refreshed_at TIMESTAMP
) USING DELTA;

CREATE TABLE IF NOT EXISTS gold.daily_weekly_trends (
    trend_grain STRING,
    date DATE,
    week DATE,
    total_orders BIGINT,
    total_revenue DECIMAL(14, 2),
    avg_order_value DECIMAL(12, 2),
    _refreshed_at TIMESTAMP
) USING DELTA;

CREATE TABLE IF NOT EXISTS gold.customer_segmentation (
    segment_type STRING,
    customer_count BIGINT,
    avg_revenue DECIMAL(12, 2),
    total_revenue DECIMAL(14, 2),
    _refreshed_at TIMESTAMP
) USING DELTA;

-- Verification (seed 42 sample data after Silver run):
-- SELECT SUM(invalid_records) FROM (
--   SELECT COUNT(*) FILTER (WHERE NOT _is_valid) AS invalid_records FROM silver.customers
--   UNION ALL SELECT COUNT(*) FILTER (WHERE NOT _is_valid) FROM silver.products
--   UNION ALL SELECT COUNT(*) FILTER (WHERE NOT _is_valid) FROM silver.orders
-- );
