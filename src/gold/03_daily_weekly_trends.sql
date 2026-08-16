-- Gold: daily and weekly order/revenue trends.
-- Source: valid silver.orders only.
-- Uses COUNT(DISTINCT order_id) to prevent duplicate-key double counting.

CREATE OR REPLACE TABLE {gold_daily_weekly_trends}
USING DELTA
AS
WITH valid_orders AS (
    SELECT
        order_id,
        order_date,
        total_amount
    FROM {silver_orders}
    WHERE _is_valid = TRUE
),
daily AS (
    SELECT
        'DAILY' AS trend_grain,
        order_date AS date,
        date_trunc('week', order_date) AS week,
        COUNT(DISTINCT order_id) AS total_orders,
        CAST(SUM(total_amount) AS DECIMAL(14, 2)) AS total_revenue
    FROM valid_orders
    GROUP BY
        order_date,
        date_trunc('week', order_date)
),
weekly AS (
    SELECT
        'WEEKLY' AS trend_grain,
        date_trunc('week', order_date) AS date,
        date_trunc('week', order_date) AS week,
        COUNT(DISTINCT order_id) AS total_orders,
        CAST(SUM(total_amount) AS DECIMAL(14, 2)) AS total_revenue
    FROM valid_orders
    GROUP BY date_trunc('week', order_date)
)
SELECT
    trend_grain,
    date,
    week,
    total_orders,
    total_revenue,
    CAST(
        CASE
            WHEN total_orders > 0 THEN total_revenue / total_orders
            ELSE 0
        END AS DECIMAL(12, 2)
    ) AS avg_order_value,
    current_timestamp() AS _refreshed_at
FROM daily
UNION ALL
SELECT
    trend_grain,
    date,
    week,
    total_orders,
    total_revenue,
    CAST(
        CASE
            WHEN total_orders > 0 THEN total_revenue / total_orders
            ELSE 0
        END AS DECIMAL(12, 2)
    ) AS avg_order_value,
    current_timestamp() AS _refreshed_at
FROM weekly;
