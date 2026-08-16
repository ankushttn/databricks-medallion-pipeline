# Dashboard Query Validation Report

**Run ID:** `dashboard-validation-001`  
**Validated at:** 2026-08-16T06:21:04.947547+00:00  
**Status:** PASS

Local validation executes each query in `dashboard_queries.sql` against
Gold temp views built from sample CSV data. This does **not** verify
Databricks SQL Dashboard UI configuration.

## KPI Snapshot

| metric | value |
|--------|-------|
| total_revenue | 74519828.18 |
| total_orders | 99600 |
| avg_order_value | 748.19 |
| total_customers | 9940 |

## Query Results

| query_name | result | row_count | detail |
|------------|--------|-----------|--------|
| chart_customer_revenue_distribution | PASS | 6 | executed_ok rows=6 |
| chart_customer_segmentation | PASS | 3 | executed_ok rows=3 |
| chart_daily_revenue_trend | PASS | 912 | executed_ok rows=912 |
| chart_top_10_products_by_revenue | PASS | 10 | executed_ok rows=10 |
| chart_weekly_revenue_trend | PASS | 132 | executed_ok rows=132 |
| kpi_average_order_value | PASS | 1 | executed_ok rows=1 |
| kpi_total_customers | PASS | 1 | executed_ok rows=1 |
| kpi_total_orders | PASS | 1 | executed_ok rows=1 |
| kpi_total_revenue | PASS | 1 | executed_ok rows=1 |
| table_segment_performance | PASS | 3 | executed_ok rows=3 |
| table_top_10_customers_by_revenue | PASS | 10 | executed_ok rows=10 |
| kpi_cross_check_trends | PASS | 1 | KPI totals match gold.daily_weekly_trends DAILY grain |
