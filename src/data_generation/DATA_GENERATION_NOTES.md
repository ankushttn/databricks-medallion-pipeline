# Data Generation Notes

## Purpose

Produce reproducible CSV files for `data/customers.csv`, `data/orders.csv`, and `data/products.csv`.

## Requirements

- Use a fixed random seed (e.g., `random.seed(42)`).
- Generate realistic but synthetic e-commerce records.
- Intentionally inject a small percentage of bad records for Silver quality testing.

## Planned Bad Record Types

| Entity | Issue | Purpose |
|--------|-------|---------|
| Customers | Null email, duplicate customer_id | Completeness, uniqueness |
| Orders | Invalid customer_id, negative quantity | Referential integrity, business logic |
| Products | Invalid unit_price (negative or zero) | Business logic |

## Output

| File | Approx. rows |
|------|--------------|
| `data/customers.csv` | 100 |
| `data/products.csv` | 50 |
| `data/orders.csv` | 500 |

## Status

_Not implemented — foundation phase only._
