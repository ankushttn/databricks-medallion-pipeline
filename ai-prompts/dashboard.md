# AI Prompts — Dashboard

Evidence log for Cursor interactions on the Databricks SQL dashboard layer. Each entry documents a real session from the project transcript.

---

## Interaction 1 — Dashboard queries and guide (2026-08-16)

### 1. Prompt sent

> Implement the Databricks SQL dashboard layer.
>
> Create/update:
> - `src/dashboard/dashboard_queries.sql`
> - `src/dashboard/DASHBOARD_GUIDE.md`
>
> Create visualizations:
> 1. Top 10 products by revenue — bar chart
> 2. Customer revenue distribution — histogram
> 3. Customer segmentation — pie/donut chart
>
> Also create KPI queries: total revenue, total orders, average order value, total customers.
>
> Queries must use Gold tables. Every query must be readable, commented, validated, safe against duplicate joins.
>
> DASHBOARD_GUIDE.md must explain query name, source table, visualization type, axes, filters, business purpose, expected interpretation.
>
> Do not claim the dashboard was created successfully unless verified in Databricks.
>
> Clearly distinguish SQL queries created by the repository vs dashboard configuration steps performed manually in Databricks.

### 2. Purpose

Provide analytics-facing SQL and setup documentation for Gold KPIs without falsely claiming Databricks UI verification.

### 3. Cursor response summary

Cursor implemented:

| File | Purpose |
|------|---------|
| `dashboard_queries.sql` | 12 named queries (4 KPIs + 3 required charts + 5 supplementary) |
| `DASHBOARD_GUIDE.md` | Query catalog, chart settings, duplicate-join rules, manual Databricks steps |
| `query_loader.py` | Parses `-- QUERY:` blocks for validation |
| `validate_dashboard_local.py` | Runs queries against local Gold temp views |
| `tests/dashboard/test_dashboard_queries.py` | 12 automated tests |

Initial `validate_dashboard_local.py` failed due to incorrect `build_silver_tables()` call signature — fixed to pass `validated_at` and register views correctly.

### 4. What was accepted

- Gold-only, single-table reads (no Silver/Bronze joins in dashboard SQL)
- `trend_grain = 'DAILY'` filter on KPI queries to avoid double-counting weekly rows
- Pre-aggregated Gold columns used as-is (no re-aggregation of raw orders)
- Honest status table: repo SQL validated locally; Databricks UI not verified
- Revenue histogram with `revenue_bucket_sort` for correct bucket ordering

### 5. What was rejected

- Claiming Databricks SQL Dashboard was built or verified in workspace
- Multi-table joins in dashboard queries (duplicate-join risk)
- Summing DAILY + WEEKLY trend rows for global KPIs

### 6. What was modified manually

`validate_dashboard_local.py` — fixed `build_silver_tables()` / `register_silver_views()` call after first validation run failed.

### 7. Why the decision was made

Dashboard layer is SQL + documentation in repo; actual Databricks UI wiring requires workspace access not available in local development. Local validation proves SQL correctness against Gold temp views.

### 8. Validation performed

```bash
python src/dashboard/validate_dashboard_local.py --data-dir data --output-dir data
python -m pytest tests/dashboard/test_dashboard_queries.py -v
```

**Result:** 12/12 queries PASS. KPI snapshot: revenue $74,519,828.18 / orders 99,600 / AOV $748.19 / customers 9,940. Report: `data/DASHBOARD_VALIDATION_REPORT.md`.

### 9. Result

Dashboard SQL layer complete locally. Manual Databricks steps documented in `DASHBOARD_GUIDE.md` § "Manual Databricks setup (not verified from this repo)".

---

## Duplicate-join safety rules (accepted design)

| Rule | Rationale |
|------|-----------|
| Gold tables only | No invalid/duplicate rows reintroduced from Silver |
| Single-table reads | Each query selects from one Gold table |
| DAILY grain for global KPIs | Prevents summing weekly + daily trend rows |
| Pre-aggregated metrics | Use `total_revenue`, `customer_count` from Gold directly |
