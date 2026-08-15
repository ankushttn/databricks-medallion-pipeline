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

## Phase 1 — Data Generation

**Design reference:** `data-model.md` §2, `requirements-analysis.md` §6.4

- [ ] Implement `generate_sample_data.py` with fixed random seed
- [ ] Generate CSVs with schema:
  - Customers: `customer_id`, `customer_name`, `email`, `country`, `signup_date`, `customer_segment`, `lifetime_value`
  - Orders: `order_id`, `customer_id`, `order_date`, `product_id`, `quantity`, `unit_price`, `total_amount`, `order_status`, `payment_date`
  - Products: `product_id`, `product_name`, `category`, `price`, `cost`, `stock_quantity`, `reorder_level`
- [ ] Inject mandatory defects (50 NULL emails, 10 dup customer_id, order defects per spec)
- [ ] Reach ~700 problematic rows (document approach in `DATA_GENERATION_NOTES.md`)
- [ ] Update `data/*.csv` headers to match `data-model.md`
- [ ] Update `database/seed-data-notes.md`
- [ ] Add `tests/test_data_generation.py`

## Phase 2 — Bronze Layer

**Design reference:** `design-notes.md` §3, `data-model.md` §4

- [ ] Implement `01_ingest_customers.py` → `bronze.customers`
- [ ] Implement `02_ingest_orders.py` → `bronze.orders` (partitioned by `order_date`)
- [ ] Implement `03_ingest_products.py` → `bronze.products`
- [ ] Implement `ingest_all.py` orchestrator
- [ ] Add `_ingested_at`, `_source_file` metadata columns
- [ ] Implement error handling and logging per `design-notes.md` §9–10
- [ ] Update `database/schema.sql` with Bronze DDL
- [ ] Add `tests/test_bronze_ingest.py`

## Phase 3 — Silver Layer

**Design reference:** `design-notes.md` §4, `data-model.md` §5

- [ ] Implement checks per `data-quality-strategy.md` (48 checks across 5 dimensions)
- [ ] Implement `create_silver_tables.py` (order: customers → products → orders → DQ summary)
- [ ] Add `_is_valid`, `_quality_issues`, `_validated_at` columns
- [ ] Create `silver.data_quality_summary` reporting table
- [ ] Partition `silver.orders` by `order_date`
- [ ] Verify row-count parity with Bronze
- [ ] Verify ~700 invalid rows and all §6.4 defect counts
- [ ] Update `database/schema.sql` with Silver DDL
- [ ] Add `tests/test_silver_quality.py`

## Phase 4 — Gold Layer

**Design reference:** `design-notes.md` §5, `data-model.md` §6

- [ ] Implement `01_sales_by_product.sql` → `gold.sales_by_product`
- [ ] Implement `02_revenue_by_customer.sql` → `gold.revenue_by_customer`
- [ ] Implement `03_daily_weekly_trends.sql` → `gold.daily_weekly_trends`
- [ ] Implement `04_customer_segmentation.sql` → `gold.customer_segmentation`
- [ ] Implement `create_gold_tables.py` orchestrator
- [ ] Filter Silver inputs to `_is_valid = true`
- [ ] Update `database/schema.sql` with Gold DDL
- [ ] Add `tests/test_gold_aggregations.py`

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
