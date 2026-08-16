# Gold Layer Validation Report

**Run ID:** `gold-validation-001`  
**Validated at:** 2026-08-16T02:46:18.104614  
**Overall status:** PASS

## Assumptions

- Only Silver rows with `_is_valid = TRUE` are used in Gold aggregations.
- Invalid rows (NULL FKs, duplicate PKs, referential failures, etc.) are excluded.
- `COUNT(DISTINCT order_id)` prevents duplicate-key double counting if any invalid rows slipped through.
- High-Value segment threshold: `$2,500.00` lifetime actual revenue.
- Segmentation is mutually exclusive with priority: Inactive → High-Value → Repeat → One-Time.
- **Note:** `Inactive` may have zero customers when every valid customer has at least one valid order.

## Silver Input Summary

| entity | valid_rows | invalid_rows_excluded |
|--------|------------|------------------------|
| silver.customers | 9,940 | excluded from Gold |
| silver.products | 500 | excluded from Gold |
| silver.orders | 99,600 | excluded from Gold |

**Invalid orders excluded from Gold:** 420

## Gold Table Row Counts

| table_name | row_count |
|------------|-----------|
| gold_sales_by_product | 500 |
| gold_revenue_by_customer | 9,940 |
| gold_daily_weekly_trends | 1,044 |
| gold_customer_segmentation | 3 |

## Gold Metrics Summary

| check_name | table_name | total_rows | passed_rows | failed_rows | pass_percentage | failure_percentage | detail |
|------------|------------|------------|-------------|-------------|-----------------|---------------------|--------|
| sales_by_product_summary | gold.sales_by_product | 500 | 500 | 0 | 100.00% | 0.00% | orders=99600, revenue=74519828.18 |
| revenue_by_customer_summary | gold.revenue_by_customer | 9,940 | 9,940 | 0 | 100.00% | 0.00% | orders=99003, revenue=74068955.73 |
| daily_weekly_trends_daily_summary | gold.daily_weekly_trends | 912 | 912 | 0 | 100.00% | 0.00% | grain=DAILY, orders=99600, revenue=74519828.18 |
| daily_weekly_trends_weekly_summary | gold.daily_weekly_trends | 132 | 132 | 0 | 100.00% | 0.00% | grain=WEEKLY, orders=99600, revenue=74519828.18 |
| segment_high_value | gold.customer_segmentation | 9,652 | 9,652 | 0 | 100.00% | 0.00% | avg_revenue=7619.84, total_revenue=73546742.87 |
| segment_repeat | gold.customer_segmentation | 284 | 284 | 0 | 100.00% | 0.00% | avg_revenue=1828.36, total_revenue=519253.12 |
| segment_one_time | gold.customer_segmentation | 4 | 4 | 0 | 100.00% | 0.00% | avg_revenue=739.94, total_revenue=2959.74 |

## Validation Queries

| table | validation | result | detail |
|-------|------------|--------|--------|
| gold.sales_by_product | no_null_product_keys | PASS | 0 |
| gold.sales_by_product | non_negative_metrics | PASS | 0 |
| gold.sales_by_product | avg_order_value_consistency | PASS | 0 |
| gold.sales_by_product | no_duplicate_products | PASS | rows=500 distinct_products=500 |
| gold.revenue_by_customer | no_null_customer_keys | PASS | 0 |
| gold.revenue_by_customer | lifetime_value_matches_revenue | PASS | 0 |
| gold.revenue_by_customer | avg_order_value_consistency | PASS | 0 |
| gold.revenue_by_customer | no_duplicate_customers | PASS | rows=9940 distinct_customers=9940 |
| gold.daily_weekly_trends | no_null_dates | PASS | 0 |
| gold.daily_weekly_trends | avg_order_value_consistency | PASS | 0 |
| gold.daily_weekly_trends | daily_and_weekly_grains_present | PASS | grains=[WEEKLY, DAILY] |
| gold.customer_segmentation | segment_count_within_bounds | PASS | segments=[High-Value, Repeat, One-Time] count=3 |
| gold.customer_segmentation | customer_count_positive | PASS | 0 |
| gold.customer_segmentation | avg_revenue_consistency | PASS | 0 |
| gold.customer_segmentation | segment_types_allowed | PASS | [] |
