# Requirements Analysis

## Project Goal

Build an end-to-end e-commerce **Medallion Architecture** pipeline that ingests customer, order, and product data, validates it in Silver, and produces business-ready Gold analytics.

## Functional Requirements

### Source Data

| Entity | Source | Key Fields (expected) |
|--------|--------|----------------------|
| Customers | `data/customers.csv` | customer_id, name, email, segment, created_at |
| Orders | `data/orders.csv` | order_id, customer_id, product_id, quantity, order_date, total_amount |
| Products | `data/products.csv` | product_id, name, category, unit_price |

### Bronze Layer

- Ingest all three CSV sources into Delta tables.
- Preserve raw data exactly as received (no transformations beyond type-safe load).
- Support orchestrated run via `ingest_all.py`.

### Silver Layer

Apply five data quality dimensions:

1. **Completeness** — required fields present
2. **Uniqueness** — no duplicate primary keys
3. **Type validation** — correct data types and formats
4. **Referential integrity** — foreign keys resolve (orders → customers, orders → products)
5. **Business logic** — domain rules (e.g., positive quantities, valid amounts)

Rules:

- Flag invalid records; do **not** delete intentionally bad source rows.
- Quality issues must be measurable (counts, flags, summary tables).

### Gold Layer

Deliver four business aggregations:

1. Sales by product
2. Revenue by customer
3. Daily / weekly trends
4. Customer segmentation

### Dashboard

- SQL queries in `src/dashboard/` consuming Gold tables.
- Setup guide in `DASHBOARD_GUIDE.md`.

## Non-Functional Requirements

- Deterministic sample data generation (fixed seed).
- Production-oriented code: logging, type hints, docstrings.
- No hardcoded secrets.
- Tests or validation for every major component.
- Full AI interaction documentation.

## Out of Scope (Foundation Phase)

- Actual pipeline implementation (pending).
- Databricks job scheduling and CI/CD (future).
