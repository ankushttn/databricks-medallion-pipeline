# Specification

## Objective

Deliver a complete Bronze → Silver → Gold pipeline for e-commerce data with dashboard-ready Gold outputs.

## Deliverables

### 1. Data Generation

- [ ] `generate_sample_data.py` with fixed seed
- [ ] Populated `data/*.csv` with intentional bad records

### 2. Bronze Layer

- [ ] `01_ingest_customers.py`
- [ ] `02_ingest_orders.py`
- [ ] `03_ingest_products.py`
- [ ] `ingest_all.py` orchestrator
- [ ] Delta tables: `bronze.customers`, `bronze.orders`, `bronze.products`

### 3. Silver Layer

- [ ] Completeness checks
- [ ] Uniqueness checks
- [ ] Type validation
- [ ] Referential integrity
- [ ] Business logic validation
- [ ] `create_silver_tables.py`
- [ ] Quality metrics logging

### 4. Gold Layer

- [ ] `01_sales_by_product.sql`
- [ ] `02_revenue_by_customer.sql`
- [ ] `03_daily_weekly_trends.sql`
- [ ] `04_customer_segmentation.sql`
- [ ] `create_gold_tables.py`

### 5. Dashboard

- [ ] `dashboard_queries.sql`
- [ ] `DASHBOARD_GUIDE.md`

### 6. Testing & Documentation

- [ ] Tests for major components
- [ ] `reflection.md` completed
- [ ] `final-ai-usage-summary.md` completed
- [ ] All `ai-prompts/` files updated

## Acceptance Criteria

- Pipeline runs end-to-end on Databricks
- Quality issues are flagged and measurable
- Gold tables power four analytics use cases
- No secrets in source code
- Architecture unchanged without approval
