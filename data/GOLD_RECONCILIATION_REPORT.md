# Gold Reconciliation Report

**Run ID:** `gold-reconciliation-001`  
**Status:** PASS

Independent reconciliation recomputes Gold metrics using alternate aggregation paths
(deduplicated order facts, semi-joins, Python segment classification) and compares
row-level results to Gold SQL output.

## Reconciliation Checks

| check_name | table | result | gold | expected | detail |
|------------|-------|--------|------|----------|--------|
| sales_by_product_metrics | gold.sales_by_product | PASS | keys=500 | keys=500 | missing_keys=0 metric_mismatches=0 |
| revenue_by_customer_metrics | gold.revenue_by_customer | PASS | keys=9940 | keys=9940 | missing_keys=0 metric_mismatches=0 |
| daily_trends_metrics | gold.daily_weekly_trends | PASS | keys=912 | keys=912 | missing_keys=0 metric_mismatches=0 |
| weekly_trends_metrics | gold.daily_weekly_trends | PASS | keys=132 | keys=132 | missing_keys=0 metric_mismatches=0 |
| daily_trends_order_total | gold.daily_weekly_trends | PASS | 99600 | 99600 | Sum of daily total_orders vs distinct valid order_id |
| customer_segmentation_metrics | gold.customer_segmentation | PASS | keys=3 | keys=3 | missing_keys=0 metric_mismatches=0 |
| segmentation_python_loop | gold.customer_segmentation | PASS | {'High-Value': 9652, 'Repeat': 284, 'One-Time': 4} | {'High-Value': 9652, 'Repeat': 284, 'One-Time': 4, 'Inactive': 0} | Independent Python classification vs Gold SQL |
| invalid_duplicates_excluded | gold.sales_by_product | PASS | 74519828.18 | all_orders=74821244.25 | duplicate_invalid_orders=40 |
| null_fk_orders_excluded | gold.sales_by_product | PASS | 74519828.18 | 74519828.18 | null_customer_id_invalid_orders=100 |
| gold_revenue_matches_valid_inner_join | gold.sales_by_product | PASS | 74519828.18 | 74519828.18 | Gold product revenue sum vs valid order revenue (inner join may differ if orphan products) |
| gold_sales_revenue_equals_valid_product_join | gold.sales_by_product | PASS | 74519828.18 | 74519828.18 | Gold total revenue vs valid orders with valid product |
| orphan_valid_orders_identified | gold.revenue_by_customer | PASS | 597 | >0 | Valid orders with invalid customers excluded from customer Gold |

## Product Traces (Bronze → Silver → Gold)

| product_id | bronze_rows | silver_valid | silver_invalid | gold_orders | expected_orders | gold_revenue | expected_revenue | result | notes |
|------------|-------------|--------------|----------------|-------------|-----------------|--------------|------------------|--------|-------|
| 83 | 186 | 186 | 0 | 186 | 186 | 218688.9 | 218688.90 | PASS |  |
| 121 | 204 | 203 | 1 | 203 | 203 | 74970.27 | 74970.27 | PASS |  |
| 197 | 229 | 227 | 2 | 227 | 227 | 147654.18 | 147654.18 | PASS |  |
| 236 | 186 | 186 | 0 | 186 | 186 | 3522.36 | 3522.36 | PASS |  |
| 469 | 251 | 251 | 0 | 251 | 251 | 377486.72 | 377486.72 | PASS |  |

## Customer Traces (Bronze → Silver → Gold)

| customer_id | bronze_rows | silver_valid | silver_invalid | gold_orders | expected_orders | gold_revenue | expected_revenue | result | notes |
|------------|-------------|--------------|----------------|-------------|-----------------|--------------|------------------|--------|-------|
| 1 | 7 | 7 | 0 | 7 | 7 | 7050.21 | 7050.21 | PASS | segment=High-Value |
| 10 | 3 | 3 | 0 | 3 | 3 | 2306.37 | 2306.37 | PASS | segment=Repeat |
| 866 | 1 | 1 | 0 | 1 | 1 | 796.25 | 796.25 | PASS | segment=One-Time |
| 1966 | 9 | 9 | 0 | None | 9 | None | 9707.69 | PASS | Customer invalid in Silver — excluded from Gold customer table |
| 264 | 4 | 4 | 0 | None | 4 | None | 2574.96 | PASS | Customer invalid in Silver — excluded from Gold customer table |
