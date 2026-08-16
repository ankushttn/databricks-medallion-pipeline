# Task Breakdown

**Related:** `spec.md`, `design-notes.md`, `requirements-analysis.md`

---

## Phase 0 — Foundation ✅

- [x] Repository structure
- [x] Initial documentation (requirements, design stubs, Cursor rules)
- [x] `.gitignore`
- [x] Cursor rules (`.cursor/rules/medallion-pipeline.mdc`)
- [x] Stub source files
- [x] AI prompt templates

## Phase 0.5 — Architecture & Data Model Design ✅

- [x] `requirements-analysis.md` — full requirements (v1.0)
- [x] `design-notes.md` — architecture, layers, Mermaid diagram, Delta/logging/error/DQ design (v2.0)
- [x] `data-model.md` — full schemas, relationships, PKs/FKs, partitioning (v2.0)
- [x] `data-quality-strategy.md` — formal DQ framework, 48 checks, metrics (v2.0)
- [x] `cursor-workflow/spec.md` — technical specification (v2.0)
- [x] `cursor-workflow/task-breakdown.md` — this file

---

## Phase 1 — Data Generation ✅

- [x] Implement `generate_sample_data.py` with fixed random seed
- [x] Generate CSVs with schema per `data-model.md`
- [x] Inject mandatory defects (50 NULL emails, 10 dup customer_id, order defects per spec)
- [x] Post-generation validation (fails loudly on mismatch)
- [x] CLI args: `--output-dir`, `--seed`
- [x] Update `DATA_GENERATION_NOTES.md`
- [x] Add `tests/test_data_generation.py`

## Phase 2 — Bronze Layer ✅

- [x] Shared config (`config.py`) — env vars + CLI, DBFS/local paths
- [x] Explicit schemas (`schemas.py`)
- [x] Core ingest utilities (`ingest_utils.py`)
- [x] Implement `01_ingest_customers.py` → `bronze.customers`
- [x] Implement `02_ingest_orders.py` → `bronze.orders` (partitioned by `order_date`)
- [x] Implement `03_ingest_products.py` → `bronze.products`
- [x] Implement `ingest_all.py` orchestrator
- [x] Metadata: `_ingested_at`, `_source_file`
- [x] Static validation (`validate_bronze_static.py`)
- [x] Databricks execution guide (`BRONZE_EXECUTION.md`)
- [x] `tests/test_bronze_ingest.py` (10 tests passing)
- [ ] Full Delta integration test on Databricks cluster (manual)

## Phase 3 — Silver Layer

**Design reference:** `design-notes.md` §4, `data-model.md` §5

- [x] Implement checks per `data-quality-strategy.md` (48 checks across 5 dimensions)
- [x] Implement `create_silver_tables.py` (order: customers → products → orders → DQ summary)
- [x] Add `_is_valid`, `_quality_issues`, `_validated_at` columns
- [x] Create `silver.data_quality_summary` reporting table
- [x] Partition `silver.orders` by `order_date`
- [x] Verify row-count parity with Bronze
- [x] Verify mandatory §6.4 defect counts (`data/SILVER_QUALITY_REPORT.md`, run `silver-validation-001`)
- [ ] Update `database/schema.sql` with Silver DDL
- [x] Add `tests/test_silver_quality.py`
- [x] Add `src/silver/validate_silver_local.py` for CSV-based validation without Delta

## Phase 4 — Gold Layer

**Design reference:** `design-notes.md` §5, `data-model.md` §6

- [x] Implement `01_sales_by_product.sql` → `gold.sales_by_product`
- [x] Implement `02_revenue_by_customer.sql` → `gold.revenue_by_customer`
- [x] Implement `03_daily_weekly_trends.sql` → `gold.daily_weekly_trends`
- [x] Implement `04_customer_segmentation.sql` → `gold.customer_segmentation`
- [x] Implement `create_gold_tables.py` orchestrator
- [x] Filter Silver inputs to `_is_valid = true`
- [x] Add `src/gold/validate_gold_local.py` and `tests/test_gold_aggregations.py`
- [x] Document assumptions in `src/gold/GOLD_ARCHITECTURE.md`
- [ ] Update `database/schema.sql` with Gold DDL
- [x] Add `tests/test_gold_aggregations.py`

## Phase 5 — Dashboard & Wrap-up

**Design reference:** `design-notes.md` §6

- [ ] Implement `dashboard_queries.sql` (Gold tables only)
- [ ] Complete `DASHBOARD_GUIDE.md` (Databricks SQL Dashboard setup)
- [ ] End-to-end validation on Databricks
- [ ] Complete `reflection.md`
- [ ] Complete `final-ai-usage-summary.md`
- [ ] Update all `ai-prompts/` layer files
- [ ] Final review against `requirements-analysis.md` and `spec.md`
- [ ] Complete `candidate-info.md`

---

## Dependency Graph

```text
Phase 0 → Phase 0.5 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
```

Within Phase 3:

```text
silver.customers ──┐
silver.products  ──┼──→ silver.orders ──→ silver.data_quality_summary
```

Within Phase 4:

```text
silver.orders + silver.products  → gold.sales_by_product
silver.orders + silver.customers → gold.revenue_by_customer
silver.orders                    → gold.daily_weekly_trends
silver.customers + silver.orders → gold.customer_segmentation
```

---

*Last updated: 2026-08-15*
