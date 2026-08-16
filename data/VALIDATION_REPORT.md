# Sample Data Validation Report

**Data directory:** `data`
**Validation seed (generation):** `42`
**Overall status:** ✅ PASSED
**Checks run:** 34
**Checks passed:** 34
**Checks failed:** 0

---

## Summary by Category

- ✅ **column_names**: 3/3 passed
- ✅ **date_ranges**: 1/1 passed
- ✅ **duplicate_pks**: 7/7 passed
- ✅ **financial**: 2/2 passed
- ✅ **intentional_issues**: 4/4 passed
- ✅ **invalid_values**: 1/1 passed
- ✅ **null_counts**: 5/5 passed
- ✅ **orphan_fks**: 5/5 passed
- ✅ **row_counts**: 6/6 passed

---

## Detailed Results

| Check ID | Category | Description | Status | Expected | Actual |
|----------|----------|-------------|--------|----------|--------|
| RC-CUST | row_counts | customers row count | PASS | 10010 | 10010 |
| RC-PROD | row_counts | products row count | PASS | 500 | 500 |
| RC-ORDE | row_counts | orders row count | PASS | 100020 | 100020 |
| CN-CUST | column_names | customers column names match schema | PASS | ['customer_id', 'customer_name', 'email', 'country', 'signup_date', 'customer_segment', 'lifetime_value'] | ['customer_id', 'customer_name', 'email', 'country', 'signup_date', 'customer_segment', 'lifetime_value'] |
| CN-PROD | column_names | products column names match schema | PASS | ['product_id', 'product_name', 'category', 'price', 'cost', 'stock_quantity', 'reorder_level'] | ['product_id', 'product_name', 'category', 'price', 'cost', 'stock_quantity', 'reorder_level'] |
| CN-ORDE | column_names | orders column names match schema | PASS | ['order_id', 'customer_id', 'order_date', 'product_id', 'quantity', 'unit_price', 'total_amount', 'order_status', 'payment_date'] | ['order_id', 'customer_id', 'order_date', 'product_id', 'quantity', 'unit_price', 'total_amount', 'order_status', 'payment_date'] |
| NC-EMAIL | null_counts | NULL email count (intentional) | PASS | 50 | 50 |
| NC-OCID | null_counts | NULL order.customer_id (intentional) | PASS | 100 | 100 |
| NC-OPID | null_counts | NULL order.product_id (intentional) | PASS | 200 | 200 |
| NC-PAY | null_counts | NULL payment_date (allowed by schema) | PASS | > 0 (nullable column) | 24941 |
| NC-UNEXP | null_counts | No unexpected NULLs in required columns | PASS | 0 | 0 |
| DP-CUST | duplicate_pks | Customer duplicate PK extra rows (intentional) | PASS | 10 | 10 |
| DP-CKEY | duplicate_pks | Customer_id values appearing >1 (intentional) | PASS | 10 | 10 |
| DP-PROD | duplicate_pks | Product duplicate PKs (must be zero) | PASS | 0 | 0 |
| DP-ORD | duplicate_pks | Order duplicate PK extra rows (intentional) | PASS | 20 | 20 |
| DP-OKEY | duplicate_pks | Order_id values appearing >1 (intentional) | PASS | 20 | 20 |
| DP-MAXC | duplicate_pks | No customer_id appears more than twice | PASS | <= 2 | 2 |
| DP-MAXO | duplicate_pks | No order_id appears more than twice | PASS | <= 2 | 2 |
| FK-OCUST | orphan_fks | Orphan customer_id count (intentional invalid FK) | PASS | 50 | 50 |
| FK-OPROD | orphan_fks | Orphan product_id count (intentional invalid FK) | PASS | 30 | 30 |
| FK-UNEXC | orphan_fks | No unexpected orphan customer_id values | PASS | 0 | 0 |
| FK-UNEXP | orphan_fks | No unexpected orphan product_id values | PASS | 0 | 0 |
| FK-VFC | orphan_fks | Valid-range customer_id values exist in customers.csv | PASS | 0 | 0 |
| IV-ALL | invalid_values | No invalid domain values in clean rows | PASS | 0 errors | 0 |
| DR-ALL | date_ranges | All dates within expected ranges and logically consistent | PASS | 0 errors | 0 |
| FC-ORD | financial | order total_amount = quantity × unit_price | PASS | 0 mismatches | 0 |
| FC-PROD | financial | product cost <= price (except intentional supplementary defects) | PASS | 210 | 210 |
| II-EMAIL | intentional_issues | Intentional defect: null_email | PASS | 50 | 50 |
| II-OCID | intentional_issues | Intentional defect: null_customer_id | PASS | 100 | 100 |
| II-OPID | intentional_issues | Intentional defect: null_product_id | PASS | 200 | 200 |
| II-SUM | intentional_issues | All 7 intentional defect types specified in assignment | PASS | 7 types | see FK + null + dup checks |
| CV-CIDS | row_counts | All customer_id 1..10000 present at least once | PASS | 0 missing | 0 |
| CV-PIDS | row_counts | All product_id 1..500 present | PASS | 0 missing | 0 |
| CV-OIDS | row_counts | All order_id 1..100000 present at least once | PASS | 0 missing | 0 |

---

## Intentional Defect Summary

| Defect | Expected |
|--------|----------|
| null_email | 50 |
| duplicate_customer_id_extra_rows | 10 |
| null_customer_id | 100 |
| null_product_id | 200 |
| orphan_customer_id | 50 |
| orphan_product_id | 30 |
| duplicate_order_id_extra_rows | 20 |
