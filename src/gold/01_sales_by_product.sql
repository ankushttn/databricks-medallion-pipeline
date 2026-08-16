-- Gold: sales aggregated by product.
-- Source: valid silver.orders INNER JOIN valid silver.products.
-- Excludes invalid Silver rows and avoids duplicate-PK double counting via _is_valid filter.

CREATE OR REPLACE TABLE {gold_sales_by_product}
USING DELTA
AS
WITH valid_orders AS (
    SELECT
        order_id,
        product_id,
        total_amount
    FROM {silver_orders}
    WHERE _is_valid = TRUE
),
valid_products AS (
    SELECT
        product_id,
        product_name,
        category
    FROM {silver_products}
    WHERE _is_valid = TRUE
)
SELECT
    p.product_id,
    p.product_name,
    p.category,
    COUNT(DISTINCT o.order_id) AS total_orders,
    CAST(SUM(o.total_amount) AS DECIMAL(14, 2)) AS total_revenue,
    CAST(
        CASE
            WHEN COUNT(DISTINCT o.order_id) > 0
            THEN SUM(o.total_amount) / COUNT(DISTINCT o.order_id)
            ELSE 0
        END AS DECIMAL(12, 2)
    ) AS avg_order_value,
    current_timestamp() AS _refreshed_at
FROM valid_orders AS o
INNER JOIN valid_products AS p
    ON o.product_id = p.product_id
GROUP BY
    p.product_id,
    p.product_name,
    p.category;
