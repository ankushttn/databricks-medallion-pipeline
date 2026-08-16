# Silver Quality Validation Report

**Run ID:** `20260816T064521Z`  
**Validated at:** 2026-08-16T06:45:21.021251  
**Mandatory checks:** PASS

## Entity Summary

| table_name | total_rows | passed_rows | failed_rows | pass_percentage | failure_percentage |
|------------|------------|-------------|-------------|-----------------|---------------------|
| silver.customers | 10,010 | 9,940 | 70 | 99.30% | 0.70% |
| silver.products | 500 | 290 | 210 | 58.00% | 42.00% |
| silver.orders | 100,020 | 99,600 | 420 | 99.58% | 0.42% |

## Per-Check Results

| check_name | table_name | total_rows | passed_rows | failed_rows | pass_percentage | failure_percentage | issue_code |
|------------|------------|------------|-------------|-------------|-----------------|---------------------|------------|
| lifetime value non-negative | silver.customers | 10,010 | 10,010 | 0 | 100.00% | 0.00% | `business:negative_lifetime_value` |
| email completeness | silver.customers | 10,010 | 9,960 | 50 | 99.50% | 0.50% | `completeness:email_null` |
| customer_id integer validation | silver.customers | 10,010 | 10,010 | 0 | 100.00% | 0.00% | `type:customer_id_invalid` |
| customer_segment allowed values | silver.customers | 10,010 | 10,010 | 0 | 100.00% | 0.00% | `type:customer_segment_invalid` |
| email format validation | silver.customers | 10,010 | 10,010 | 0 | 100.00% | 0.00% | `type:email_format_invalid` |
| lifetime_value decimal validation | silver.customers | 10,010 | 10,010 | 0 | 100.00% | 0.00% | `type:lifetime_value_invalid` |
| signup_date date validation | silver.customers | 10,010 | 10,010 | 0 | 100.00% | 0.00% | `type:signup_date_invalid` |
| customers primary key uniqueness | silver.customers | 10,010 | 9,990 | 20 | 99.80% | 0.20% | `uniqueness:duplicate_customer_id` |
| completed orders require payment date | silver.orders | 100,020 | 100,020 | 0 | 100.00% | 0.00% | `business:missing_payment_date` |
| order status allowed values | silver.orders | 100,020 | 100,020 | 0 | 100.00% | 0.00% | `business:invalid_order_status` |
| payment date not before order date | silver.orders | 100,020 | 100,020 | 0 | 100.00% | 0.00% | `business:payment_before_order` |
| quantity positive | silver.orders | 100,020 | 100,020 | 0 | 100.00% | 0.00% | `business:non_positive_quantity` |
| total amount consistency | silver.orders | 100,020 | 100,020 | 0 | 100.00% | 0.00% | `business:total_amount_mismatch` |
| unit price non-negative | silver.orders | 100,020 | 100,020 | 0 | 100.00% | 0.00% | `business:negative_unit_price` |
| customer_id completeness | silver.orders | 100,020 | 99,920 | 100 | 99.90% | 0.10% | `completeness:customer_id_null` |
| product_id completeness | silver.orders | 100,020 | 99,820 | 200 | 99.80% | 0.20% | `completeness:product_id_null` |
| customer_id referential integrity | silver.orders | 100,020 | 99,970 | 50 | 99.95% | 0.05% | `referential:invalid_customer_id` |
| product_id referential integrity | silver.orders | 100,020 | 99,990 | 30 | 99.97% | 0.03% | `referential:invalid_product_id` |
| order_date date validation | silver.orders | 100,020 | 100,020 | 0 | 100.00% | 0.00% | `type:order_date_invalid` |
| order_id integer validation | silver.orders | 100,020 | 100,020 | 0 | 100.00% | 0.00% | `type:order_id_invalid` |
| order_status string validation | silver.orders | 100,020 | 100,020 | 0 | 100.00% | 0.00% | `type:order_status_invalid` |
| quantity integer validation | silver.orders | 100,020 | 100,020 | 0 | 100.00% | 0.00% | `type:quantity_invalid` |
| total_amount decimal validation | silver.orders | 100,020 | 100,020 | 0 | 100.00% | 0.00% | `type:total_amount_invalid` |
| unit_price decimal validation | silver.orders | 100,020 | 100,020 | 0 | 100.00% | 0.00% | `type:unit_price_invalid` |
| orders primary key uniqueness | silver.orders | 100,020 | 99,980 | 40 | 99.96% | 0.04% | `uniqueness:duplicate_order_id` |
| cost non-negative | silver.products | 500 | 500 | 0 | 100.00% | 0.00% | `business:negative_cost` |
| price not below cost | silver.products | 500 | 290 | 210 | 58.00% | 42.00% | `business:price_below_cost` |
| price positive | silver.products | 500 | 500 | 0 | 100.00% | 0.00% | `business:non_positive_price` |
| reorder level non-negative | silver.products | 500 | 500 | 0 | 100.00% | 0.00% | `business:negative_reorder_level` |
| stock quantity non-negative | silver.products | 500 | 500 | 0 | 100.00% | 0.00% | `business:negative_stock_quantity` |
| category allowed values | silver.products | 500 | 500 | 0 | 100.00% | 0.00% | `type:category_invalid` |
| cost decimal validation | silver.products | 500 | 500 | 0 | 100.00% | 0.00% | `type:cost_invalid` |
| price decimal validation | silver.products | 500 | 500 | 0 | 100.00% | 0.00% | `type:price_invalid` |
| product_id integer validation | silver.products | 500 | 500 | 0 | 100.00% | 0.00% | `type:product_id_invalid` |
| reorder_level integer validation | silver.products | 500 | 500 | 0 | 100.00% | 0.00% | `type:reorder_level_invalid` |
| stock_quantity integer validation | silver.products | 500 | 500 | 0 | 100.00% | 0.00% | `type:stock_quantity_invalid` |
| products primary key uniqueness | silver.products | 500 | 500 | 0 | 100.00% | 0.00% | `uniqueness:duplicate_product_id` |

## Mandatory Defect Verification

| entity | check | expected | actual | result |
|--------|-------|----------|--------|--------|
| customers | NULL emails (`completeness:email_null`) | == 50 | 50 | PASS |
| customers | duplicate customer_id rows (`uniqueness:duplicate_customer_id`) | >= 10 | 20 | PASS |
| products | price below cost (supplementary defects) (`business:price_below_cost`) | == 210 | 210 | PASS |
| orders | NULL customer_id (`completeness:customer_id_null`) | == 100 | 100 | PASS |
| orders | NULL product_id (`completeness:product_id_null`) | == 200 | 200 | PASS |
| orders | invalid customer_id (`referential:invalid_customer_id`) | == 50 | 50 | PASS |
| orders | invalid product_id (`referential:invalid_product_id`) | == 30 | 30 | PASS |
| orders | duplicate order_id rows (`uniqueness:duplicate_order_id`) | >= 20 | 40 | PASS |

## Unexpected Failures (non-assignment)

_No unexpected check failures detected._

## All Failing Checks (full transparency)

| check_name | table_name | failed_rows | failure_percentage | issue_code |
|------------|------------|-------------|---------------------|------------|
| price not below cost | silver.products | 210 | 42.00% | `business:price_below_cost` |
| product_id completeness | silver.orders | 200 | 0.20% | `completeness:product_id_null` |
| customer_id completeness | silver.orders | 100 | 0.10% | `completeness:customer_id_null` |
| email completeness | silver.customers | 50 | 0.50% | `completeness:email_null` |
| customer_id referential integrity | silver.orders | 50 | 0.05% | `referential:invalid_customer_id` |
| orders primary key uniqueness | silver.orders | 40 | 0.04% | `uniqueness:duplicate_order_id` |
| product_id referential integrity | silver.orders | 30 | 0.03% | `referential:invalid_product_id` |
| customers primary key uniqueness | silver.customers | 20 | 0.20% | `uniqueness:duplicate_customer_id` |
