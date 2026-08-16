# Candidate Information

| Field | Value |
|-------|-------|
| **Name** | Ankush Dev |
| **Email** | _[Add your submission email]_ |
| **Submission Date** | 2026-08-16 |
| **Databricks Workspace** | _[Add workspace URL after running `scripts/DATABRICKS_E2E_VALIDATION.md`]_ |
| **Git Repository** | https://github.com/ankushttn/databricks-medallion-pipeline.git |

## Assignment Checklist

- [x] Bronze layer ingests all three source entities
- [x] Silver layer implements five quality dimensions
- [x] Gold layer delivers four business aggregations
- [x] Dashboard queries documented (`src/dashboard/dashboard_queries.sql`, `DASHBOARD_GUIDE.md`)
- [x] Tests or validation for major components (120 pytest tests; reports in `data/`)
- [x] AI usage documented in `ai-prompts/` and `final-ai-usage-summary.md`
- [x] Reflection completed in `reflection.md`

## Local verification summary

| Check | Result | Evidence |
|-------|--------|----------|
| Pytest suite | 122 tests (post-fix) | `tests/TEST_RESULTS.md` |
| Silver invalid rows | 700 (70 + 210 + 420) | `data/SILVER_QUALITY_REPORT.md` |
| Gold reconciliation | PASS | `data/GOLD_RECONCILIATION_REPORT.md` |
| Dashboard SQL (local) | 12/12 PASS | `data/DASHBOARD_VALIDATION_REPORT.md` |
| Databricks E2E | Pending workspace run | `scripts/DATABRICKS_E2E_VALIDATION.md` |
