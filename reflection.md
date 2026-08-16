# Reflection

## What Went Well

- Clear medallion separation: Bronze preserves raw CSV values, Silver flags without deleting, Gold aggregates only valid rows.
- Reusable Silver quality framework (`quality_framework.py`, `check_helpers.py`) kept five dimensions consistent and testable.
- Independent validation scripts (`validate_silver_local.py`, `reconcile_gold_local.py`, `validate_dashboard_local.py`) provided evidence beyond unit tests.
- Deterministic data generation (seed 42) made defect counts reproducible and auditable.
- Honest documentation of what was verified locally vs what requires a Databricks workspace.

## Challenges

- Reconciling the assignment’s **~700 problematic-row** target with the **460 mandatory defect instances** required supplementary product business-logic defects (210 `price_below_cost` rows) without breaking mandatory counts.
- Gold reconciliation initially compared product revenue to all valid-order revenue; invalid products exposed the need to compare against valid-order ∩ valid-product joins only.
- PySpark on Windows required `PYSPARK_PYTHON` alignment and long test runtimes (~9 minutes for the full suite).
- Databricks Delta writes and SQL Dashboard UI could not be CI-verified without a live workspace.

## What I Would Do Differently

- Run Databricks E2E validation earlier to catch catalog/permission issues before final documentation.
- Add a pinned `requirements.txt` (pytest, pyspark) for reproducible local setup.
- Consider Databricks Asset Bundles for job orchestration instead of manual `%run` steps.

## Key Learnings

- Medallion layering and separation of concerns make quality issues measurable without losing auditability.
- Data quality as a first-class concern: flag, count, and report — do not silently drop bad rows in Silver.
- Duplicate primary keys must be flagged on **all** duplicate rows, not just extras, to prevent Gold double-counting.
- Dashboard KPIs must respect grain (DAILY vs WEEKLY) to avoid double-counting trend metrics.

## Time Spent (approximate)

| Phase | Hours |
|-------|-------|
| Planning & foundation | 4 |
| Data generation | 6 |
| Bronze | 5 |
| Silver | 10 |
| Gold & dashboard | 8 |
| Testing & documentation | 8 |
