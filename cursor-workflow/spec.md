# Technical Specification

**Project:** E-Commerce Medallion Architecture Data Pipeline  
**Version:** 3.0  
**Status:** Implementation complete locally — Databricks deployment pending verification  
**Related:** `design-notes.md`, `data-model.md`, `requirements-analysis.md`

---

## 1. Objective

Deliver a complete pipeline on Databricks:

```text
Source CSV → Bronze → Silver → Gold → Databricks SQL Dashboard
```

The pipeline ingests e-commerce customer, order, and product data, flags ~700 intentionally problematic rows in Silver, and produces four Gold analytics tables for dashboard consumption.

---

## 2. Architecture

See `design-notes.md` for the full Mermaid diagram. Layer responsibilities:

| Layer | Technology | Output |
|-------|------------|--------|
| Source | Python (`generate_sample_data.py`) | `data/*.csv` |
| Bronze | PySpark | `bronze.customers`, `bronze.orders`, `bronze.products` |
| Silver | PySpark | `silver.customers`, `silver.products`, `silver.orders`, `silver.data_quality_summary` |
| Gold | SQL + PySpark orchestrator | Four `gold.*` analytics tables |
| Dashboard | Databricks SQL | Visualizations from Gold tables |

---

## 3. Data Model Summary

Full schemas in `data-model.md`.

### Source Entities

**Customers:** `customer_id` INT, `customer_name` STRING, `email` STRING, `country` STRING, `signup_date` DATE, `customer_segment` STRING, `lifetime_value` DECIMAL

**Orders:** `order_id` INT, `customer_id` INT, `order_date` DATE, `product_id` INT, `quantity` INT, `unit_price` DECIMAL, `total_amount` DECIMAL, `order_status` STRING, `payment_date` DATE

**Products:** `product_id` INT, `product_name` STRING, `category` STRING, `price` DECIMAL, `cost` DECIMAL, `stock_quantity` INT, `reorder_level` INT

### Relationships

- `orders.customer_id` → `customers.customer_id` (many-to-one)
- `orders.product_id` → `products.product_id` (many-to-one)

---

## 4. Deliverables

### 4.1 Data Generation ✅

- [x] `src/data_generation/generate_sample_data.py` — deterministic seed
- [x] `data/customers.csv`, `data/orders.csv`, `data/products.csv` — populated per `data-model.md` §2
- [x] Intentional defects per `requirements-analysis.md` §6.4
- [x] `src/data_generation/DATA_GENERATION_NOTES.md`
- [x] `src/data_generation/validate_sample_data.py` — independent 34-check validator
- [x] `tests/data_generation/` — generation and defect tests

**Defect injection (mandatory):**

| Entity | Defect | Count |
|--------|--------|-------|
| Customers | NULL `email` | 50 |
| Customers | Duplicate `customer_id` | 10 |
| Orders | NULL `customer_id` | 100 |
| Orders | NULL `product_id` | 200 |
| Orders | Invalid `customer_id` | 50 |
| Orders | Invalid `product_id` | 30 |
| Orders | Duplicate `order_id` | 20 |

### 4.2 Bronze Layer ✅

- [x] `src/bronze/01_ingest_customers.py`
- [x] `src/bronze/02_ingest_orders.py`
- [x] `src/bronze/03_ingest_products.py`
- [x] `src/bronze/ingest_all.py`
- [x] Delta tables: `bronze.customers`, `bronze.orders`, `bronze.products` (documented; Delta write requires Databricks)
- [x] Metadata: `_ingested_at`, `_source_file`
- [x] Partition `bronze.orders` by `order_date`
- [x] `tests/bronze/` — config + Spark read tests
- [x] `src/bronze/BRONZE_EXECUTION.md`

**Bronze acceptance:**

- Row count matches CSV per entity — **verified locally**
- No quality filtering or deduplication — **verified**
- All source columns preserved — **verified**

### 4.3 Silver Layer ✅

- [x] `src/silver/01_quality_completeness.py`
- [x] `src/silver/02_quality_uniqueness.py`
- [x] `src/silver/03_quality_type_validation.py`
- [x] `src/silver/04_quality_referential_integrity.py`
- [x] `src/silver/05_quality_business_logic.py`
- [x] `src/silver/create_silver_tables.py`
- [x] Quality metadata: `_is_valid`, `_quality_issues`, `_validated_at`
- [x] Reporting table: `silver.data_quality_summary`
- [x] Partition `silver.orders` by `order_date`
- [x] `tests/silver/` — per-dimension + integration tests
- [x] `src/silver/validate_silver_local.py`
- [x] `data/SILVER_QUALITY_REPORT.md`

**Silver acceptance:**

- Five quality dimensions implemented — **verified**
- Bronze row count = Silver row count per entity — **verified**
- All §6.4 defects detected and flagged — **verified** (`silver-validation-001`)
- ~420 invalid orders flagged — **verified**
- Quality metrics logged and persisted — **verified**

### 4.4 Gold Layer ✅

- [x] `src/gold/01_sales_by_product.sql` → `gold.sales_by_product`
- [x] `src/gold/02_revenue_by_customer.sql` → `gold.revenue_by_customer`
- [x] `src/gold/03_daily_weekly_trends.sql` → `gold.daily_weekly_trends`
- [x] `src/gold/04_customer_segmentation.sql` → `gold.customer_segmentation`
- [x] `src/gold/create_gold_tables.py`
- [x] Filter `silver.*` inputs to `_is_valid = true`
- [x] `tests/gold/` — aggregations, reconciliation, segmentation
- [x] `src/gold/reconciliation.py` + `reconcile_gold_local.py`
- [x] `data/GOLD_RECONCILIATION_REPORT.md` — all checks PASS

**Gold acceptance:**

- Four tables with columns per `data-model.md` §6 — **verified locally**
- Aggregations exclude invalid Silver rows — **verified**
- Independent reconciliation PASS — **verified**
- SQL readable and formatted — **verified**

### 4.5 Dashboard Layer ✅ (SQL only)

- [x] `src/dashboard/dashboard_queries.sql` — 12 queries against Gold tables only
- [x] `src/dashboard/DASHBOARD_GUIDE.md` — setup guide with honest verification status
- [x] `src/dashboard/validate_dashboard_local.py`
- [x] `tests/dashboard/test_dashboard_queries.py` — 12 tests PASS
- [ ] Databricks SQL Dashboard UI — **not verified** (manual steps documented)

### 4.6 Database & Schema

- [ ] `database/schema.sql` — Silver/Gold DDL incomplete
- [x] `database/setup-notes.md` — Databricks workspace configuration
- [x] `database/seed-data-notes.md` — seed data documentation

### 4.7 Testing & Documentation ✅

- [x] Tests for all major components under `tests/` — **120/120 PASS**
- [x] `tests/README.md`, `tests/TEST_RESULTS.md`
- [x] `ERROR_HANDLING.md` — production-readiness strategy
- [x] `README.md` — 22-section professional guide
- [x] All `ai-prompts/` layer files updated with evidence
- [ ] `reflection.md` — pending
- [ ] `final-ai-usage-summary.md` — pending

---

## 5. Processing Sequence

```text
1. generate_sample_data.py
2. ingest_all.py                    (bronze.customers, bronze.products, bronze.orders)
3. create_silver_tables.py          (silver.customers → silver.products → silver.orders → DQ summary)
4. create_gold_tables.py            (four gold tables)
5. dashboard_queries.sql            (Databricks SQL Dashboard)
```

**Local validation sequence (verified):**

```bash
python src/data_generation/generate_sample_data.py --seed 42 --output-dir data
python src/silver/validate_silver_local.py --data-dir data --output-dir data
python src/gold/validate_gold_local.py --data-dir data --output-dir data
python src/gold/reconcile_gold_local.py --data-dir data --output-dir data
python src/dashboard/validate_dashboard_local.py --data-dir data --output-dir data
python -m pytest tests/ -v
```

---

## 6. Cross-Cutting Requirements

### Error Handling

- Fail fast on infrastructure errors (missing files, Spark failures)
- Log context with `logging`; re-raise exceptions
- Data quality issues are flagged, not raised as exceptions
- See `ERROR_HANDLING.md` and `src/common/pipeline_utils.py`

### Logging

- `logging` module only (no `print`)
- Log: run_id, layer, table, row counts, durations, quality summaries
- Pipeline start/end timing via `pipeline_timer` context manager

### Delta Lake

- All tables stored as Delta format
- Write mode: `overwrite` for batch refresh
- Orders tables partitioned by `order_date` (Bronze and Silver)
- Gold `daily_weekly_trends` partitioned by `period_type`

### Security

- No hardcoded secrets
- Credentials via Databricks secrets or environment variables

---

## 7. Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| AC-01 | Pipeline runs end-to-end: CSV → Bronze → Silver → Gold → Dashboard | Local ✅ / Databricks ⏳ |
| AC-02 | Schema matches `data-model.md` | ✅ Verified locally |
| AC-03 | Five Silver quality dimensions operational | ✅ Verified |
| AC-04 | All mandatory defects (§6.4) detected and flagged | ✅ Verified |
| AC-05 | ~700 rows flagged invalid in Silver | ✅ ~420 invalid orders + customer/product flags |
| AC-06 | No bad records deleted (Bronze count = Silver count) | ✅ Verified |
| AC-07 | Four Gold tables with correct business logic | ✅ Reconciliation PASS |
| AC-08 | Dashboard queries execute against Gold on Databricks SQL | SQL ✅ / UI ⏳ |
| AC-09 | Tests pass for major components | ✅ 120/120 |
| AC-10 | No secrets in source code | ✅ Verified |
| AC-11 | AI usage documented | ✅ `ai-prompts/` complete |
| AC-12 | Deterministic data generation (fixed seed) | ✅ Seed 42 |
| AC-13 | Architecture unchanged: Source → Bronze → Silver → Gold → Dashboard | ✅ Verified |

---

## 8. Verification Boundaries

| Capability | Verified in repo | Notes |
|------------|------------------|-------|
| Sample data generation | Yes | 34-check validator + pytest |
| Bronze CSV read + schema | Yes | Static + Spark tests |
| Silver quality framework | Yes | Local validation report |
| Gold aggregations | Yes | Reconciliation PASS |
| Dashboard SQL | Yes | Local validator |
| Databricks Delta writes | No | Documented in layer execution guides |
| Databricks SQL Dashboard UI | No | Manual steps in `DASHBOARD_GUIDE.md` |

---

## 9. Out of Scope

- Real-time / streaming ingestion
- CI/CD pipeline deployment
- SCD Type 2 dimension management
- Production job scheduling (document only)

---

*Last updated: 2026-08-16*
