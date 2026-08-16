-- Gold: behavioral customer segmentation.
-- Source: valid silver.customers LEFT JOIN valid silver.orders.
--
-- Business rules (mutually exclusive, evaluated in priority order):
--   1. Inactive    — zero valid orders
--   2. High-Value  — total_revenue >= {high_value_revenue_threshold}
--   3. Repeat      — two or more valid orders (and not High-Value)
--   4. One-Time    — exactly one valid order (and not High-Value)

CREATE OR REPLACE TABLE {gold_customer_segmentation}
USING DELTA
AS
WITH valid_orders AS (
    SELECT
        order_id,
        customer_id,
        total_amount
    FROM {silver_orders}
    WHERE _is_valid = TRUE
),
valid_customers AS (
    SELECT customer_id
    FROM {silver_customers}
    WHERE _is_valid = TRUE
),
customer_activity AS (
    SELECT
        c.customer_id,
        COUNT(DISTINCT o.order_id) AS total_orders,
        CAST(COALESCE(SUM(o.total_amount), 0) AS DECIMAL(14, 2)) AS total_revenue
    FROM valid_customers AS c
    LEFT JOIN valid_orders AS o
        ON c.customer_id = o.customer_id
    GROUP BY c.customer_id
),
classified AS (
    SELECT
        customer_id,
        total_orders,
        total_revenue,
        CASE
            WHEN total_orders = 0 THEN 'Inactive'
            WHEN total_revenue >= CAST({high_value_revenue_threshold} AS DECIMAL(14, 2)) THEN 'High-Value'
            WHEN total_orders >= 2 THEN 'Repeat'
            ELSE 'One-Time'
        END AS segment_type
    FROM customer_activity
)
SELECT
    segment_type,
    COUNT(*) AS customer_count,
    CAST(AVG(total_revenue) AS DECIMAL(12, 2)) AS avg_revenue,
    CAST(SUM(total_revenue) AS DECIMAL(14, 2)) AS total_revenue,
    current_timestamp() AS _refreshed_at
FROM classified
GROUP BY segment_type;
