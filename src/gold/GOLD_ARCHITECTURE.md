# Gold Layer Architecture

## Purpose

Gold provides business-ready analytics built exclusively from **valid Silver data**
(`_is_valid = TRUE`). Quality flags and invalid records are excluded by default.

## Tables

| Table | Script | Grain | Key Metrics |
|-------|--------|-------|-------------|
| `gold.sales_by_product` | `01_sales_by_product.sql` | `product_id` | total_orders, total_revenue, avg_order_value |
| `gold.revenue_by_customer` | `02_revenue_by_customer.sql` | `customer_id` | total_orders, total_revenue, avg_order_value, lifetime_value_actual |
| `gold.daily_weekly_trends` | `03_daily_weekly_trends.sql` | `date` + `trend_grain` | total_orders, total_revenue, avg_order_value |
| `gold.customer_segmentation` | `04_customer_segmentation.sql` | `segment_type` | customer_count, avg_revenue, total_revenue |

## Input Dependencies

```text
gold.sales_by_product        ← silver.orders (valid) JOIN silver.products (valid)
gold.revenue_by_customer     ← silver.customers (valid) LEFT JOIN silver.orders (valid)
gold.daily_weekly_trends     ← silver.orders (valid)
gold.customer_segmentation   ← silver.customers (valid) LEFT JOIN silver.orders (valid)
```

## Rules

1. **Valid Silver only** — `WHERE _is_valid = TRUE` on every Silver input.
2. **No duplicate counting** — `COUNT(DISTINCT order_id)` for order metrics.
3. **Inner joins for product sales** — orders must join a valid product dimension.
4. **Left joins for customer metrics** — valid customers with zero orders appear with zero revenue.
5. **SQL-first** — business logic lives in readable `.sql` files.
6. **Full rebuild** — `CREATE OR REPLACE TABLE` (overwrite) per pipeline run.
7. **No quality columns in Gold** — only business-facing fields plus `_refreshed_at`.

## Customer Segmentation Business Rules

Segments are **mutually exclusive**. Each valid customer is assigned exactly one
`segment_type` using this priority order:

| Priority | Segment | Rule |
|----------|---------|------|
| 1 | **Inactive** | `total_orders = 0` (no valid orders) |
| 2 | **High-Value** | `total_revenue >= $2,500` (sum of valid order amounts) |
| 3 | **Repeat** | `total_orders >= 2` (and not High-Value) |
| 4 | **One-Time** | `total_orders = 1` (and not High-Value) |

**Definitions:**

- `total_orders` — `COUNT(DISTINCT order_id)` from valid Silver orders.
- `total_revenue` — `SUM(total_amount)` from valid Silver orders.
- Threshold constant: `HIGH_VALUE_REVENUE_THRESHOLD` in `src/gold/constants.py`.

**Not used for segmentation:** source `customer_segment` (Premium/Standard/Basic) —
that attribute remains on `gold.revenue_by_customer` only.

**Empty segments:** A segment type with zero matching customers does not appear as a row
in `gold.customer_segmentation` (e.g. `Inactive` when all valid customers have orders).

## Field Notes

| Field | Meaning |
|-------|---------|
| `lifetime_value_actual` | Computed `SUM(total_amount)` from valid orders — not the source `lifetime_value` column |
| `avg_order_value` | `total_revenue / total_orders` (0 when no orders) |
| `trend_grain` | `DAILY` (per calendar day) or `WEEKLY` (per week start) |
| `week` | Week start date (`date_trunc('week', order_date)`) |

## Assumptions

- Each Silver order row is one line item; `order_id` is the deduplication key.
- All valid order statuses contribute to revenue (no status filter).
- Cancelled/returned orders that pass Silver validation are included.
- Invalid Silver rows are **intentionally excluded** — they failed critical validation
  (duplicate PK, NULL FK, referential errors, etc.) and would distort analytics.
- Products with no valid orders do not appear in `gold.sales_by_product` (inner join).
- **Orphan valid orders:** Valid orders whose `customer_id` maps to an invalid customer
  (e.g. duplicate-PK customer rows) are included in `sales_by_product` and
  `daily_weekly_trends` but excluded from `revenue_by_customer` (requires valid customer join).

## Validation

Built-in validation queries live in `src/gold/validations.py` and run automatically
after `create_gold_tables.py` unless `--skip-validation` is passed.

Local validation (no Delta):

```bash
python src/gold/validate_gold_local.py --data-dir data --output-dir data
```

Databricks:

```bash
python src/gold/create_gold_tables.py --catalog main
```

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `MEDALLION_CATALOG` | _(none)_ | Unity Catalog |
| `MEDALLION_SILVER_SCHEMA` | `silver` | Silver schema |
| `MEDALLION_GOLD_SCHEMA` | `gold` | Gold schema |
| `MEDALLION_GOLD_WRITE_MODE` | `overwrite` | Delta write mode |
