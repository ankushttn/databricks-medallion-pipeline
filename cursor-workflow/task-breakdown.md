# Task Breakdown

**Related:** `spec.md`, `design-notes.md`, `requirements-analysis.md`  
**Last updated:** 2026-08-16

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
- [x] `cursor-workflow/spec.md` — technical specification (v3.0)
- [x] `cursor-workflow/task-breakdown.md` — this file

---

## Phase 1 — Data Generation ✅

- [x] Implement `generate_sample_data.py` with fixed random seed
- [x] Generate CSVs with schema per `data-model.md`
- [x] Inject mandatory defects (50 NULL emails, 10 dup customer_id, order defects per spec)
- [x] Post-generation validation (fails loudly on mismatch)
- [x] CLI args: `--output-dir`, `--seed`
- [x] Update `DATA_GENERATION_NOTES.md`
- [x] Independent senior validator: `validate_sample_data.py` (34 checks)
- [x] Tests: `tests/data_generation/`

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
- [x] Tests: `tests/bronze/` (15 tests)
- [x] Production-readiness: narrowed exceptions, config validation
- [ ] Full Delta integration test on Databricks cluster (manual)

## Phase 3 — Silver Layer ✅

**Design reference:** `design-notes.md` §4, `data-model.md` §5

- [x] Implement checks per `data-quality-strategy.md` (48 checks across 5 dimensions)
- [x] Implement `create_silver_tables.py` (order: customers → products → orders → DQ summary)
- [x] Add `_is_valid`, `_quality_issues`, `_validated_at` columns
- [x] Create `silver.data_quality_summary` reporting table
- [x] Partition `silver.orders` by `order_date`
- [x] Verify row-count parity with Bronze
- [x] Verify mandatory §6.4 defect counts (`data/SILVER_QUALITY_REPORT.md`, run `silver-validation-001`)
- [x] Tests: `tests/silver/` (39 tests across dimensions + integration + metrics)
- [x] `src/silver/validate_silver_local.py` for CSV-based validation without Delta
- [x] `SILVER_ARCHITECTURE.md`
- [ ] Update `database/schema.sql` with Silver DDL

## Phase 4 — Gold Layer ✅

**Design reference:** `design-notes.md` §5, `data-model.md` §6

- [x] Implement `01_sales_by_product.sql` → `gold.sales_by_product`
- [x] Implement `02_revenue_by_customer.sql` → `gold.revenue_by_customer`
- [x] Implement `03_daily_weekly_trends.sql` → `gold.daily_weekly_trends`
- [x] Implement `04_customer_segmentation.sql` → `gold.customer_segmentation`
- [x] Implement `create_gold_tables.py` orchestrator
- [x] Filter Silver inputs to `_is_valid = true`
- [x] `src/gold/validate_gold_local.py` and `tests/gold/test_gold_aggregations.py`
- [x] Document assumptions in `src/gold/GOLD_ARCHITECTURE.md`
- [x] Senior reconciliation: `reconciliation.py`, `reconcile_gold_local.py`, `tests/gold/test_gold_reconciliation.py` (all PASS)
- [x] Segmentation tests: `tests/gold/test_gold_segmentation.py`
- [ ] Update `database/schema.sql` with Gold DDL

## Phase 5 — Dashboard, Testing & Wrap-up

**Design reference:** `design-notes.md` §6

- [x] Implement `dashboard_queries.sql` (Gold tables only — 12 queries)
- [x] Complete `DASHBOARD_GUIDE.md` (Databricks SQL Dashboard setup)
- [x] `validate_dashboard_local.py` + `tests/dashboard/test_dashboard_queries.py`
- [x] Automated test suite: `tests/` — **120 tests PASS** (`tests/README.md`, `tests/TEST_RESULTS.md`)
- [x] Production-readiness review (`ERROR_HANDLING.md`, `pipeline_utils.py`)
- [x] Professional `README.md` (22 sections + Mermaid)
- [x] Update all `ai-prompts/` layer files with evidence documentation
- [x] Update `cursor-workflow/project-context.md`, `spec.md`, `cursor-rules-or-instructions.md`
- [ ] End-to-end validation on Databricks
- [ ] Databricks SQL Dashboard UI verification
- [ ] Complete `reflection.md`
- [ ] Complete `final-ai-usage-summary.md`
- [ ] Complete `candidate-info.md`
- [ ] Final review against `requirements-analysis.md` and `spec.md`
- [ ] `database/schema.sql` Silver/Gold DDL

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

## Validation Summary (local, 2026-08-16)

| Check | Command | Result |
|-------|---------|--------|
| Sample data | `validate_sample_data.py` | 34/34 PASS |
| Bronze static | `validate_bronze_static.py` | PASS |
| Silver quality | `validate_silver_local.py` | All mandatory defects detected |
| Gold validation | `validate_gold_local.py` | 15/15 queries PASS |
| Gold reconciliation | `reconcile_gold_local.py` | 11/11 checks PASS |
| Dashboard SQL | `validate_dashboard_local.py` | 12/12 queries PASS |
| Full pytest | `python -m pytest tests/ -v` | **120/120 PASS** (~8m 48s) |

---

## AI Evidence Documentation

All major Cursor interactions documented in:

| File | Sessions covered |
|------|------------------|
| `ai-prompts/documentation.md` | Foundation, requirements, architecture, DQ strategy, README, this evidence pass |
| `ai-prompts/data-generation.md` | Generation + senior CSV review |
| `ai-prompts/bronze-layer.md` | Bronze ingestion |
| `ai-prompts/silver-layer.md` | Framework + validation |
| `ai-prompts/gold-layer.md` | Implementation + senior reconciliation |
| `ai-prompts/dashboard.md` | Dashboard SQL + guide |
| `ai-prompts/debugging.md` | All debugging sessions and AI rejections |

Source transcript: `50551ecf-026a-4549-8321-588606fc1847.jsonl`
