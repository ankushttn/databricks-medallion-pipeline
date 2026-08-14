# Data Generation Notes

## Purpose

Produce reproducible CSV files for `data/customers.csv`, `data/orders.csv`, and `data/products.csv`.

## Requirements

- Use a fixed random seed (e.g., `random.seed(42)`).
- Generate realistic but synthetic e-commerce records.
- Intentionally inject a small percentage of bad records for Silver quality testing.

## Planned Bad Record Types

> **Authoritative specification:** See `requirements-analysis.md` §6.4.

| Entity | Issue | Count | Purpose |
|--------|-------|-------|---------|
| Customers | NULL `email` | 50 | Completeness |
| Customers | Duplicate `customer_id` | 10 | Uniqueness |
| Orders | NULL `customer_id` | 100 | Completeness |
| Orders | NULL `product_id` | 200 | Completeness |
| Orders | Invalid `customer_id` | 50 | Referential integrity |
| Orders | Invalid `product_id` | 30 | Referential integrity |
| Orders | Duplicate `order_id` | 20 | Uniqueness |

**Target:** approximately **700 problematic rows** across the dataset (see requirements-analysis.md §6.4).

## Output

| File | Approx. rows |
|------|--------------|
| `data/customers.csv` | 100 |
| `data/products.csv` | 50 |
| `data/orders.csv` | 500 |

## Status

_Not implemented — foundation phase only._
