# Data Generation Notes

**Script:** `src/data_generation/generate_sample_data.py`  
**Status:** Implemented  
**Related:** `data-model.md` §2, `requirements-analysis.md` §6.4, `data-quality-strategy.md`

---

## Purpose

Produce deterministic, realistic CSV files for the medallion pipeline with **exactly** the assignment-mandated quality defects and no uncontrolled issues.

## Usage

```bash
python src/data_generation/generate_sample_data.py --output-dir data --seed 42
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--output-dir` | `data` | Directory for output CSV files |
| `--seed` | `42` | Random seed for reproducibility |

The script **exits with code 1** if post-generation validation fails.

---

## Output Files

| File | Base Rows | Extra Rows | Total Rows | Notes |
|------|-----------|------------|------------|-------|
| `customers.csv` | 10,000 | +10 duplicates | **10,010** | |
| `products.csv` | 500 | — | **500** | No intentional defects |
| `orders.csv` | 100,000 | +20 duplicates | **100,020** | |

---

## Schema

### customers.csv

`customer_id`, `customer_name`, `email`, `country`, `signup_date`, `customer_segment`, `lifetime_value`

### products.csv

`product_id`, `product_name`, `category`, `price`, `cost`, `stock_quantity`, `reorder_level`

### orders.csv

`order_id`, `customer_id`, `order_date`, `product_id`, `quantity`, `unit_price`, `total_amount`, `order_status`, `payment_date`

---

## Data Realism

| Field | Generation Logic |
|-------|------------------|
| Names | Random first + last from fixed pools |
| Email | `{first}.{last}{id}@{domain}` |
| Countries | US, UK, DE, FR, CA, AU, IN, JP, BR, MX |
| Segments | Premium, Standard, Basic |
| Signup dates | 2018-01-01 to 2025-06-30 |
| Lifetime value | Uniform $100 – $49,999.99 |
| Product categories | Electronics, Clothing, Home, Sports, Books, Beauty, Toys, Garden |
| Price / cost | Price $5–$500; cost = 35–75% of price |
| Order dates | 2023-01-01 to 2025-06-30 |
| Order status | Weighted: Completed 55%, Pending 15%, Shipped 15%, Cancelled 10%, Returned 5% |
| Payment date | Set for Completed/Shipped/Returned; empty for Pending/Cancelled |
| total_amount | Always `quantity × unit_price` (exact to 2 dp) |

---

## Intentional Quality Defects

Defects are injected into **disjoint row sets** to avoid uncontrolled compound issues.

### Customers

| Defect | Count | CSV Representation | Silver Check |
|--------|-------|-------------------|--------------|
| NULL `email` | **50** | Empty string `""` | `completeness:email_null` |
| Duplicate `customer_id` | **10** | 10 appended rows copying existing customers | `uniqueness:duplicate_customer_id` |

### Orders

| Defect | Count | CSV Representation | Silver Check |
|--------|-------|-------------------|--------------|
| NULL `customer_id` | **100** | Empty string `""` | `completeness:customer_id_null` |
| NULL `product_id` | **200** | Empty string `""` | `completeness:product_id_null` |
| Invalid `customer_id` | **50** | IDs `800001`–`800050` (not in customers) | `referential:invalid_customer_id` |
| Invalid `product_id` | **30** | IDs `700001`–`700030` (not in products) | `referential:invalid_product_id` |
| Duplicate `order_id` | **20** | 20 appended rows copying existing orders | `uniqueness:duplicate_order_id` |

### Products

No intentional defects. All 500 product rows are fully valid.

---

## Post-Generation Validation

The script validates before writing CSVs:

1. **Row counts** — expected totals including duplicate append rows
2. **Schema columns** — match `data-model.md`
3. **Defect counts** — exact match to assignment specification (fails loudly on mismatch)
4. **Uncontrolled issues** — no unexpected nulls, bad formats, duplicate product IDs, amount mismatches, etc.

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| NULL as empty CSV string | Bronze reads as-is; Silver treats blank as null |
| Invalid FK ranges outside 1..N | `800xxx` / `700xxx` cannot collide with valid IDs |
| Duplicate rows appended | Preserves base row count; adds extra rows with same PK |
| Disjoint defect indices | Prevents accidental extra quality issues |
| `Random(seed)` not `numpy` | Stdlib only — no extra dependencies |

---

## Tests

```bash
pytest tests/test_data_generation.py -v
```

---

*Last updated: 2026-08-15*
