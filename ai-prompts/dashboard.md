# AI Prompts — Dashboard

## Session Log

### [2026-08-16] Dashboard queries and guide

**Goal:** SQL queries and BI setup guide for Gold KPIs.

**Prompt:** Implement Databricks SQL dashboard layer with KPI queries, required visualizations (top products bar, customer revenue histogram, segmentation pie), local validation, and setup guide distinguishing repo SQL from manual Databricks UI steps.

**Outcome:**

- 12 named queries in `dashboard_queries.sql` (4 KPIs + 3 required charts + 5 supplementary)
- `DASHBOARD_GUIDE.md` with query catalog, visualization settings, duplicate-join safety rules
- `validate_dashboard_local.py` + `tests/test_dashboard_queries.py` for local SQL validation
- Databricks SQL Dashboard UI **not** verified (manual steps documented only)

**Files touched:**

- `src/dashboard/dashboard_queries.sql`
- `src/dashboard/DASHBOARD_GUIDE.md`
- `src/dashboard/query_loader.py`
- `src/dashboard/validate_dashboard_local.py`
- `tests/test_dashboard_queries.py`
- `cursor-workflow/task-breakdown.md`

**Validation:**

```bash
python src/dashboard/validate_dashboard_local.py --data-dir data --output-dir data
python -m pytest tests/test_dashboard_queries.py -v
```
