-- =============================================================================
-- Medallion Pipeline — Databricks SQL Dashboard Queries
-- =============================================================================
--
-- Scope: Read-only analytics against pre-aggregated Gold tables only.
-- Do NOT join Bronze or Silver tables from dashboard queries.
--
-- Duplicate-join safety:
--   Each query reads from a single Gold table (or a subquery on one table).
--   Gold tables are already aggregated at their business grain, so no
--   COUNT(DISTINCT ...) is required here and multi-table joins are avoided.
--
-- Unity Catalog:
--   Replace the `gold` schema prefix with your catalog-qualified name when
--   needed, e.g. `main.gold.sales_by_product`.
--
-- Databricks SQL Dashboard:
--   Create one saved query per `-- QUERY:` block below, then bind each query
--   to a visualization. See src/dashboard/DASHBOARD_GUIDE.md for setup steps.
-- =============================================================================


-- =============================================================================
-- QUERY: kpi_total_revenue
-- Visualization: KPI (single value / counter)
-- Source: gold.daily_weekly_trends (DAILY grain only)
-- =============================================================================
-- Business purpose: Headline revenue from all valid orders.
-- Interpretation: Sum of daily revenue; excludes invalid Silver rows. Uses
-- DAILY grain only so weekly rows are not double-counted.
SELECT
    CAST(SUM(total_revenue) AS DECIMAL(14, 2)) AS total_revenue
FROM gold.daily_weekly_trends
WHERE trend_grain = 'DAILY';


-- =============================================================================
-- QUERY: kpi_total_orders
-- Visualization: KPI (single value / counter)
-- Source: gold.daily_weekly_trends (DAILY grain only)
-- =============================================================================
-- Business purpose: Total count of valid orders across the reporting period.
-- Interpretation: Sum of daily order counts; each order counted once per day.
SELECT
    SUM(total_orders) AS total_orders
FROM gold.daily_weekly_trends
WHERE trend_grain = 'DAILY';


-- =============================================================================
-- QUERY: kpi_average_order_value
-- Visualization: KPI (single value / counter)
-- Source: gold.daily_weekly_trends (DAILY grain only)
-- =============================================================================
-- Business purpose: Average revenue per valid order.
-- Interpretation: total_revenue / total_orders across all daily buckets.
SELECT
    CAST(
        CASE
            WHEN SUM(total_orders) > 0
            THEN SUM(total_revenue) / SUM(total_orders)
            ELSE 0
        END AS DECIMAL(12, 2)
    ) AS avg_order_value
FROM gold.daily_weekly_trends
WHERE trend_grain = 'DAILY';


-- =============================================================================
-- QUERY: kpi_total_customers
-- Visualization: KPI (single value / counter)
-- Source: gold.revenue_by_customer
-- =============================================================================
-- Business purpose: Count of valid customers in the customer dimension.
-- Interpretation: One row per valid Silver customer; includes customers with
-- zero orders (lifetime_value_actual = 0).
SELECT
    COUNT(*) AS total_customers
FROM gold.revenue_by_customer;


-- =============================================================================
-- QUERY: chart_top_10_products_by_revenue
-- Visualization: Bar chart
-- Source: gold.sales_by_product
-- =============================================================================
-- X-axis: product_name (or product_id)
-- Y-axis: total_revenue
-- Filters: LIMIT 10 (top performers by revenue)
-- Business purpose: Identify highest-revenue products for assortment and
-- merchandising decisions.
-- Interpretation: Bars ranked descending; revenue from valid orders joined to
-- valid products only.
SELECT
    product_id,
    product_name,
    category,
    total_orders,
    total_revenue,
    avg_order_value
FROM gold.sales_by_product
ORDER BY total_revenue DESC
LIMIT 10;


-- =============================================================================
-- QUERY: chart_customer_revenue_distribution
-- Visualization: Histogram (bar chart with revenue buckets on x-axis)
-- Source: gold.revenue_by_customer
-- =============================================================================
-- X-axis: revenue_bucket (lifetime spend band)
-- Y-axis: customer_count
-- Filters: none (all valid customers)
-- Business purpose: Understand how customer lifetime value is distributed.
-- Interpretation: Taller bars = more customers in that spend band. Most
-- customers in this sample skew High-Value (>= $2,500) per segmentation rules.
SELECT
    revenue_bucket,
    revenue_bucket_sort,
    COUNT(*) AS customer_count
FROM (
    SELECT
        customer_id,
        lifetime_value_actual,
        CASE
            WHEN lifetime_value_actual = 0 THEN '0 — No revenue'
            WHEN lifetime_value_actual < 500 THEN '1–499'
            WHEN lifetime_value_actual < 1000 THEN '500–999'
            WHEN lifetime_value_actual < 1500 THEN '1,000–1,499'
            WHEN lifetime_value_actual < 2000 THEN '1,500–1,999'
            WHEN lifetime_value_actual < 2500 THEN '2,000–2,499'
            ELSE '2,500+'
        END AS revenue_bucket,
        CASE
            WHEN lifetime_value_actual = 0 THEN 0
            WHEN lifetime_value_actual < 500 THEN 1
            WHEN lifetime_value_actual < 1000 THEN 2
            WHEN lifetime_value_actual < 1500 THEN 3
            WHEN lifetime_value_actual < 2000 THEN 4
            WHEN lifetime_value_actual < 2500 THEN 5
            ELSE 6
        END AS revenue_bucket_sort
    FROM gold.revenue_by_customer
) AS bucketed
GROUP BY
    revenue_bucket,
    revenue_bucket_sort
ORDER BY
    revenue_bucket_sort;


-- =============================================================================
-- QUERY: chart_customer_segmentation
-- Visualization: Pie chart or donut chart
-- Source: gold.customer_segmentation
-- =============================================================================
-- Slice dimension: segment_type
-- Slice size: customer_count (alternative: total_revenue)
-- Filters: none
-- Business purpose: Show behavioral customer mix (Inactive, High-Value,
-- Repeat, One-Time).
-- Interpretation: Mutually exclusive segments; slice size = number of customers
-- in each segment. Empty segments do not appear as rows.
SELECT
    segment_type,
    customer_count,
    avg_revenue,
    total_revenue,
    ROUND(
        100.0 * customer_count / SUM(customer_count) OVER (),
        2
    ) AS customer_pct
FROM gold.customer_segmentation
ORDER BY
    customer_count DESC;


-- =============================================================================
-- QUERY: chart_daily_revenue_trend
-- Visualization: Line chart
-- Source: gold.daily_weekly_trends (DAILY grain only)
-- =============================================================================
-- X-axis: date
-- Y-axis: total_revenue
-- Filters: trend_grain = 'DAILY'
-- Business purpose: Track revenue over time for seasonality and growth.
-- Interpretation: One point per calendar day; upward slope indicates growth.
SELECT
    date,
    total_orders,
    total_revenue,
    avg_order_value
FROM gold.daily_weekly_trends
WHERE trend_grain = 'DAILY'
ORDER BY
    date;


-- =============================================================================
-- QUERY: chart_weekly_revenue_trend
-- Visualization: Line chart or bar chart
-- Source: gold.daily_weekly_trends (WEEKLY grain only)
-- =============================================================================
-- X-axis: week (week start date)
-- Y-axis: total_revenue
-- Filters: trend_grain = 'WEEKLY'
-- Business purpose: Smoothed weekly view for executive reporting.
SELECT
    week,
    total_orders,
    total_revenue,
    avg_order_value
FROM gold.daily_weekly_trends
WHERE trend_grain = 'WEEKLY'
ORDER BY
    week;


-- =============================================================================
-- QUERY: table_top_10_customers_by_revenue
-- Visualization: Table (or horizontal bar chart)
-- Source: gold.revenue_by_customer
-- =============================================================================
-- Business purpose: Identify top customers by lifetime spend.
-- Interpretation: Ranked by lifetime_value_actual (sum of valid orders).
SELECT
    customer_id,
    customer_name,
    customer_segment,
    total_orders,
    lifetime_value_actual,
    avg_order_value
FROM gold.revenue_by_customer
ORDER BY
    lifetime_value_actual DESC
LIMIT 10;


-- =============================================================================
-- QUERY: table_segment_performance
-- Visualization: Table
-- Source: gold.customer_segmentation
-- =============================================================================
-- Business purpose: Detailed segment KPIs for planning and marketing.
SELECT
    segment_type,
    customer_count,
    avg_revenue,
    total_revenue,
    _refreshed_at
FROM gold.customer_segmentation
ORDER BY
    total_revenue DESC;
