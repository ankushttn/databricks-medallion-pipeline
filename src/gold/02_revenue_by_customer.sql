-- Gold: revenue aggregated by customer.
-- Source: valid silver.customers LEFT JOIN valid silver.orders.
-- lifetime_value_actual is computed from valid orders (not the source lifetime_value attribute).

CREATE OR REPLACE TABLE {gold_revenue_by_customer}
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
    SELECT
        customer_id,
        customer_name,
        customer_segment
    FROM {silver_customers}
    WHERE _is_valid = TRUE
),
customer_metrics AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.customer_segment,
        COUNT(DISTINCT o.order_id) AS total_orders,
        CAST(COALESCE(SUM(o.total_amount), 0) AS DECIMAL(14, 2)) AS total_revenue
    FROM valid_customers AS c
    LEFT JOIN valid_orders AS o
        ON c.customer_id = o.customer_id
    GROUP BY
        c.customer_id,
        c.customer_name,
        c.customer_segment
)
SELECT
    customer_id,
    customer_name,
    customer_segment,
    total_orders,
    total_revenue,
    CAST(
        CASE
            WHEN total_orders > 0 THEN total_revenue / total_orders
            ELSE 0
        END AS DECIMAL(12, 2)
    ) AS avg_order_value,
    total_revenue AS lifetime_value_actual,
    current_timestamp() AS _refreshed_at
FROM customer_metrics;
