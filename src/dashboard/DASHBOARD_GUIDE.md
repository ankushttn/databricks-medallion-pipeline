# Databricks SQL Dashboard Guide

## Status

| Artifact | Status |
|----------|--------|
| `src/dashboard/dashboard_queries.sql` | **Created in repository** — SQL validated locally |
| Databricks SQL Dashboard UI | **Not verified** — requires manual setup in your workspace |

This guide separates:

1. **Repository deliverables** — SQL queries and local validation you can run today.
2. **Manual Databricks steps** — dashboard creation in the Databricks SQL UI (not executed or verified from this repo).

---

## Prerequisites

Before building the dashboard in Databricks:

1. Bronze, Silver, and Gold pipelines have run successfully.
2. Gold tables exist and are readable:

   | Table | Grain |
   |-------|-------|
   | `gold.sales_by_product` | `product_id` |
   | `gold.revenue_by_customer` | `customer_id` |
   | `gold.daily_weekly_trends` | `date` + `trend_grain` |
   | `gold.customer_segmentation` | `segment_type` |

3. Your SQL warehouse has `SELECT` on the `gold` schema (or `{catalog}.gold` in Unity Catalog).

Build Gold tables:

```bash
python src/gold/create_gold_tables.py --catalog main
```

---

## Local validation (repository)

Validate that every query in `dashboard_queries.sql` executes against Gold temp views built from sample CSV data:

```bash
python src/dashboard/validate_dashboard_local.py --data-dir data --output-dir data
python -m pytest tests/test_dashboard_queries.py -v
```

Reports:

- `data/DASHBOARD_VALIDATION_REPORT.md`
- `data/DASHBOARD_VALIDATION_REPORT.json`

**What local validation confirms:** SQL syntax, Gold-only table references, expected row shapes, and KPI cross-checks against `gold.daily_weekly_trends`.

**What local validation does not confirm:** Databricks SQL Dashboard UI wiring, chart rendering, permissions, or warehouse performance.

---

## Manual Databricks setup (not verified from this repo)

Perform these steps in your Databricks workspace after Gold tables are deployed.

### Step 1 — Open SQL Editor

1. Go to **SQL** → **SQL Editor** in the Databricks workspace.
2. Attach a SQL warehouse with access to your Gold schema.

### Step 2 — Create saved queries

For each `-- QUERY:` block in `src/dashboard/dashboard_queries.sql`:

1. Copy the `SELECT` statement for that query.
2. If using Unity Catalog, qualify tables (e.g. `main.gold.sales_by_product`).
3. Run the query to confirm it returns results.
4. Click **Save** and name the query exactly as the block name (e.g. `kpi_total_revenue`).

### Step 3 — Create the dashboard

1. Go to **SQL** → **Dashboards** → **Create dashboard**.
2. Name it (e.g. `E-Commerce Gold KPIs`).
3. Add a visualization for each saved query (see catalog below).
4. Arrange KPI tiles in the top row; charts below.

### Step 4 — Configure refresh

1. Schedule the Gold pipeline job to run on your cadence (e.g. daily).
2. Set the dashboard auto-refresh interval **after** the Gold job completes.
3. Optionally add a text tile showing `MAX(_refreshed_at)` from any Gold table.

### Step 5 — Verify in Databricks (required before claiming success)

Manually confirm in the workspace:

- [ ] Each saved query runs without error
- [ ] KPI values match expectations from `gold.daily_weekly_trends` / `gold.revenue_by_customer`
- [ ] Charts render with correct axes and labels
- [ ] Dashboard refresh works on schedule

Only after these checks should the dashboard be considered production-ready.

---

## Query catalog

### KPI queries

#### `kpi_total_revenue`

| Field | Value |
|-------|-------|
| **Source table** | `gold.daily_weekly_trends` |
| **Visualization** | KPI / counter (single value) |
| **X-axis** | N/A |
| **Y-axis** | N/A |
| **Filters** | `trend_grain = 'DAILY'` (avoids double-counting weekly rows) |
| **Business purpose** | Headline total revenue from valid orders |
| **Expected interpretation** | Higher = stronger sales. Uses DAILY grain only so weekly aggregates are not summed twice. Compare period-over-period after adding date parameters. |

#### `kpi_total_orders`

| Field | Value |
|-------|-------|
| **Source table** | `gold.daily_weekly_trends` |
| **Visualization** | KPI / counter |
| **X-axis** | N/A |
| **Y-axis** | N/A |
| **Filters** | `trend_grain = 'DAILY'` |
| **Business purpose** | Total valid order count |
| **Expected interpretation** | Volume indicator independent of basket size. Should equal sum of daily `total_orders` in Gold trends. |

#### `kpi_average_order_value`

| Field | Value |
|-------|-------|
| **Source table** | `gold.daily_weekly_trends` |
| **Visualization** | KPI / counter |
| **X-axis** | N/A |
| **Y-axis** | N/A |
| **Filters** | `trend_grain = 'DAILY'` |
| **Business purpose** | Average revenue per order |
| **Expected interpretation** | `total_revenue / total_orders`. Rising AOV with flat order count suggests larger baskets or premium mix. |

#### `kpi_total_customers`

| Field | Value |
|-------|-------|
| **Source table** | `gold.revenue_by_customer` |
| **Visualization** | KPI / counter |
| **X-axis** | N/A |
| **Y-axis** | N/A |
| **Filters** | None |
| **Business purpose** | Count of valid customers in the dimension |
| **Expected interpretation** | One row per valid Silver customer, including zero-order customers. Does not include invalid (flagged) customers. |

---

### Required chart queries

#### `chart_top_10_products_by_revenue`

| Field | Value |
|-------|-------|
| **Source table** | `gold.sales_by_product` |
| **Visualization** | **Bar chart** (vertical or horizontal) |
| **X-axis** | `product_name` |
| **Y-axis** | `total_revenue` |
| **Filters** | `ORDER BY total_revenue DESC LIMIT 10` |
| **Business purpose** | Identify top-performing products for assortment and inventory focus |
| **Expected interpretation** | Longest bars = highest revenue. Revenue from valid orders joined to valid products only. No join in dashboard query — duplicate-safe. |

**Databricks chart settings:** Bar chart → X = `product_name`, Y = `total_revenue`, sort descending.

#### `chart_customer_revenue_distribution`

| Field | Value |
|-------|-------|
| **Source table** | `gold.revenue_by_customer` |
| **Visualization** | **Histogram** (bar chart with revenue buckets) |
| **X-axis** | `revenue_bucket` (lifetime spend band) |
| **Y-axis** | `customer_count` |
| **Filters** | None |
| **Business purpose** | Understand how customer lifetime value is distributed |
| **Expected interpretation** | Each bar = number of customers in a spend band. Sample data skews toward `2,500+` because High-Value threshold is $2,500. Sort by `revenue_bucket_sort` for correct bucket order. |

**Databricks chart settings:** Bar chart → X = `revenue_bucket`, Y = `customer_count`, sort by `revenue_bucket_sort`.

#### `chart_customer_segmentation`

| Field | Value |
|-------|-------|
| **Source table** | `gold.customer_segmentation` |
| **Visualization** | **Pie chart** or **donut chart** |
| **Slice dimension** | `segment_type` |
| **Slice size** | `customer_count` (alternative: `total_revenue`) |
| **Filters** | None |
| **Business purpose** | Behavioral customer mix (Inactive, High-Value, Repeat, One-Time) |
| **Expected interpretation** | Mutually exclusive segments. `customer_pct` shows share of valid customers. Empty segments (e.g. Inactive when all customers have orders) do not appear. |

**Databricks chart settings:** Pie/donut → Group by `segment_type`, aggregate `customer_count` (SUM).

---

### Supplementary queries (recommended)

#### `chart_daily_revenue_trend`

| Field | Value |
|-------|-------|
| **Source table** | `gold.daily_weekly_trends` |
| **Visualization** | Line chart |
| **X-axis** | `date` |
| **Y-axis** | `total_revenue` |
| **Filters** | `trend_grain = 'DAILY'` |
| **Business purpose** | Daily revenue trend for seasonality and growth |
| **Expected interpretation** | Upward slope = growth; spikes may indicate promotions or bulk orders. |

#### `chart_weekly_revenue_trend`

| Field | Value |
|-------|-------|
| **Source table** | `gold.daily_weekly_trends` |
| **Visualization** | Line or bar chart |
| **X-axis** | `week` |
| **Y-axis** | `total_revenue` |
| **Filters** | `trend_grain = 'WEEKLY'` |
| **Business purpose** | Smoothed weekly view for executive reporting |
| **Expected interpretation** | Less noisy than daily; good for week-over-week reviews. |

#### `table_top_10_customers_by_revenue`

| Field | Value |
|-------|-------|
| **Source table** | `gold.revenue_by_customer` |
| **Visualization** | Table (or horizontal bar chart) |
| **Business purpose** | Top customers by `lifetime_value_actual` |
| **Expected interpretation** | Ranked lifetime spend from valid orders only. |

#### `table_segment_performance`

| Field | Value |
|-------|-------|
| **Source table** | `gold.customer_segmentation` |
| **Visualization** | Table |
| **Business purpose** | Segment-level KPIs (`customer_count`, `avg_revenue`, `total_revenue`) |
| **Expected interpretation** | Compare segment economics; High-Value drives most revenue in sample data. |

---

## Duplicate-join safety

Dashboard queries follow these rules:

| Rule | Rationale |
|------|-----------|
| **Gold tables only** | No Bronze/Silver joins that could reintroduce invalid or duplicate rows |
| **Single-table reads** | Each query selects from one Gold table (subqueries on the same table are OK) |
| **DAILY grain for global KPIs** | `daily_weekly_trends` has both DAILY and WEEKLY rows; KPIs filter `trend_grain = 'DAILY'` to prevent double counting |
| **Pre-aggregated metrics** | Use `total_revenue`, `total_orders`, `customer_count` from Gold — do not re-aggregate raw orders in the dashboard |

---

## Suggested dashboard layout

```text
┌─────────────────────────────────────────────────────────────────┐
│  Total Revenue  │  Total Orders  │  Avg Order Value │ Customers │
├─────────────────────────────────────────────────────────────────┤
│  Top 10 Products (bar)          │  Customer Segmentation (pie)  │
├─────────────────────────────────┴───────────────────────────────┤
│  Customer Revenue Distribution (histogram)                      │
├─────────────────────────────────────────────────────────────────┤
│  Daily Revenue Trend (line)                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `Table or view not found: gold.*` | Gold pipeline not run or wrong catalog | Run `create_gold_tables.py`; qualify `main.gold.*` |
| KPI revenue 2× expected | Summing both DAILY and WEEKLY trends | Add `WHERE trend_grain = 'DAILY'` |
| Segmentation missing Inactive | All valid customers have orders | Expected on sample data; see `GOLD_ARCHITECTURE.md` |
| Customer KPI ≠ sum of segment counts | Stale Gold tables | Re-run Gold pipeline and refresh dashboard |
| Histogram buckets out of order | Chart sorted alphabetically | Sort by `revenue_bucket_sort` in visualization settings |

---

## Databricks SQL Dashboard UI verification (AC-07)

Local validation (`validate_dashboard_local.py`) confirms SQL correctness only. Complete these steps in your workspace:

1. Run Gold pipeline so `gold.*` tables exist.
2. Create a new **SQL Dashboard** (Lakeview) in Databricks SQL.
3. Add each visualization from the mapping table in this guide using queries from `dashboard_queries.sql`.
4. Confirm KPI cross-check: `kpi_total_revenue` matches sum of `gold.daily_weekly_trends` where `trend_grain = 'DAILY'`.
5. Save dashboard URL and screenshot for submission evidence.

See also: `scripts/DATABRICKS_E2E_VALIDATION.md` §5.

---

## Related documentation

- `src/gold/GOLD_ARCHITECTURE.md` — Gold table definitions and segmentation rules
- `src/dashboard/dashboard_queries.sql` — All query SQL
- `data/DASHBOARD_VALIDATION_REPORT.md` — Local validation output (after running validator)
- `data/GOLD_RECONCILIATION_REPORT.md` — Gold layer reconciliation results
