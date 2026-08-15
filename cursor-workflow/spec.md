# Technical Specification

**Project:** E-Commerce Medallion Architecture Data Pipeline  
**Version:** 2.0  
**Status:** Design complete — implementation pending  
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

### 4.1 Data Generation

- [ ] `src/data_generation/generate_sample_data.py` — deterministic seed
- [ ] `data/customers.csv`, `data/orders.csv`, `data/products.csv` — populated per `data-model.md` §2
- [ ] Intentional defects per `requirements-analysis.md` §6.4 (~700 problematic rows)
- [ ] `src/data_generation/DATA_GENERATION_NOTES.md` — generation and defect documentation
- [ ] `tests/test_data_generation.py`

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

### 4.2 Bronze Layer

- [ ] `src/bronze/01_ingest_customers.py`
- [ ] `src/bronze/02_ingest_orders.py`
- [ ] `src/bronze/03_ingest_products.py`
- [ ] `src/bronze/ingest_all.py`
- [ ] Delta tables: `bronze.customers`, `bronze.orders`, `bronze.products`
- [ ] Metadata: `_ingested_at`, `_source_file`
- [ ] Partition `bronze.orders` by `order_date`
- [ ] `tests/test_bronze_ingest.py`

**Bronze acceptance:**

- Row count matches CSV per entity
- No quality filtering or deduplication
- All source columns preserved

### 4.3 Silver Layer

- [ ] `src/silver/01_quality_completeness.py`
- [ ] `src/silver/02_quality_uniqueness.py`
- [ ] `src/silver/03_quality_type_validation.py`
- [ ] `src/silver/04_quality_referential_integrity.py`
- [ ] `src/silver/05_quality_business_logic.py`
- [ ] `src/silver/create_silver_tables.py` — orchestrator (customers → products → orders → DQ summary)
- [ ] Quality metadata: `_is_valid`, `_quality_issues`, `_validated_at`
- [ ] Reporting table: `silver.data_quality_summary`
- [ ] Partition `silver.orders` by `order_date`
- [ ] `tests/test_silver_quality.py`

**Silver acceptance:**

- Five quality dimensions implemented
- Bronze row count = Silver row count per entity
- All §6.4 defects detected and flagged
- `SUM(invalid_records)` ≈ 700 across entities
- Quality metrics logged and persisted

### 4.4 Gold Layer

- [ ] `src/gold/01_sales_by_product.sql` → `gold.sales_by_product`
- [ ] `src/gold/02_revenue_by_customer.sql` → `gold.revenue_by_customer`
- [ ] `src/gold/03_daily_weekly_trends.sql` → `gold.daily_weekly_trends`
- [ ] `src/gold/04_customer_segmentation.sql` → `gold.customer_segmentation`
- [ ] `src/gold/create_gold_tables.py`
- [ ] Filter `silver.*` inputs to `_is_valid = true`
- [ ] `tests/test_gold_aggregations.py`

**Gold acceptance:**

- Four tables created with columns per `data-model.md` §6
- Aggregations exclude invalid Silver rows
- SQL is readable and formatted

### 4.5 Dashboard Layer

- [ ] `src/dashboard/dashboard_queries.sql` — queries against Gold tables only
- [ ] `src/dashboard/DASHBOARD_GUIDE.md` — Databricks SQL Dashboard setup
- [ ] Panels: sales by product, revenue by customer, daily/weekly trends, customer segmentation

### 4.6 Database & Schema

- [ ] `database/schema.sql` — CREATE SCHEMA statements aligned with `data-model.md`
- [ ] `database/setup-notes.md` — Databricks workspace configuration
- [ ] `database/seed-data-notes.md` — seed data documentation

### 4.7 Testing & Documentation

- [ ] Tests for all major components under `tests/`
- [ ] `reflection.md` completed at submission
- [ ] `final-ai-usage-summary.md` completed at submission
- [ ] All `ai-prompts/` layer files updated

---

## 5. Processing Sequence

```text
1. generate_sample_data.py
2. ingest_all.py                    (bronze.customers, bronze.products, bronze.orders)
3. create_silver_tables.py          (silver.customers → silver.products → silver.orders → DQ summary)
4. create_gold_tables.py          (four gold tables)
5. dashboard_queries.sql            (Databricks SQL Dashboard)
```

---

## 6. Cross-Cutting Requirements

### Error Handling

- Fail fast on infrastructure errors (missing files, Spark failures)
- Log context with `logging`; re-raise exceptions
- Data quality issues are flagged, not raised as exceptions

### Logging

- `logging` module only (no `print`)
- Log: run_id, layer, table, row counts, durations, quality summaries

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

| # | Criterion |
|---|-----------|
| AC-01 | Pipeline runs end-to-end: CSV → Bronze → Silver → Gold → Dashboard |
| AC-02 | Schema matches `data-model.md` |
| AC-03 | Five Silver quality dimensions operational |
| AC-04 | All mandatory defects (§6.4) detected and flagged |
| AC-05 | ~700 rows flagged invalid in Silver |
| AC-06 | No bad records deleted (Bronze count = Silver count) |
| AC-07 | Four Gold tables with correct business logic |
| AC-08 | Dashboard queries execute against Gold on Databricks SQL |
| AC-09 | Tests pass for major components |
| AC-10 | No secrets in source code |
| AC-11 | AI usage documented |
| AC-12 | Deterministic data generation (fixed seed) |
| AC-13 | Architecture unchanged: Source → Bronze → Silver → Gold → Dashboard |

---

## 8. Out of Scope

- Real-time / streaming ingestion
- CI/CD pipeline deployment
- SCD Type 2 dimension management
- Production job scheduling (document only)

---

*Last updated: 2026-08-15*
