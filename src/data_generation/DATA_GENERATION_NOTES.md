# Data Generation Notes

**Script:** `src/data_generation/generate_sample_data.py`  
**Validator:** `src/data_generation/validate_sample_data.py`  
**Status:** Implemented and independently validated  
**Related:** `data-model.md` §2, `requirements-analysis.md` §6.4, `data-quality-strategy.md`, `data/VALIDATION_REPORT.md`

---

## Generation Approach

### Pipeline

```text
1. generate_customers()     → 10,000 clean rows (customer_id 1..10000)
2. inject_customer_defects() → NULL emails + 10 appended duplicate rows
3. generate_products()      → 500 clean rows (product_id 1..500)
4. generate_orders()        → 100,000 clean rows (order_id 1..100000)
5. inject_order_defects()   → NULL FKs, invalid FKs, 20 appended duplicate rows
6. validate_generated_data() → fail loudly if counts or quality rules violated
7. write_csv()              → data/customers.csv, products.csv, orders.csv
```

### Design Principles

| Principle | Implementation |
|-------------|----------------|
| Deterministic | `random.Random(seed)` for all stochastic choices |
| Realistic | Weighted statuses, valid date ranges, proper email patterns |
| Controlled defects only | Disjoint index sets for order defects; no overlap |
| NULL as empty string | CSV blank fields (`""`) for Silver completeness checks |
| Invalid FK ranges | `800001–800050` (customers), `700001–700030` (products) |
| Financial integrity | `total_amount = quantity × unit_price` on every row |
| No manual CSV edits | All changes via generator only |

### Module Structure

| Function | Responsibility |
|----------|----------------|
| `generate_customers()` | Base customer dimension |
| `inject_customer_defects()` | 50 NULL emails, 10 duplicate rows |
| `generate_products()` | Clean product dimension |
| `generate_orders()` | Base fact rows with valid FKs |
| `inject_order_defects()` | Order-level defects (disjoint pools) |
| `validate_generated_data()` | Generator-internal validation |
| `validate_sample_data.py` | **Independent** file-based validation (senior DE review) |

---

## Seed

| Parameter | Value |
|-----------|-------|
| **Default seed** | `42` |
| **CLI override** | `--seed <int>` |

```bash
python src/data_generation/generate_sample_data.py --output-dir data --seed 42
```

Re-running with the same seed produces **byte-identical** CSV output.

---

## Expected Row Counts

| File | Base Rows | Injected Extra Rows | **Total** |
|------|-----------|---------------------|-----------|
| `customers.csv` | 10,000 | +10 duplicate | **10,010** |
| `products.csv` | 500 | — | **500** |
| `orders.csv` | 100,000 | +20 duplicate | **100,020** |

### ID Coverage

| Entity | ID Range | Coverage |
|--------|----------|----------|
| Customers | 1–10,000 | All IDs present at least once |
| Products | 1–500 | All IDs present exactly once |
| Orders | 1–100,000 | All IDs present at least once |

---

## Schema

### customers.csv (7 columns)

`customer_id`, `customer_name`, `email`, `country`, `signup_date`, `customer_segment`, `lifetime_value`

### products.csv (7 columns)

`product_id`, `product_name`, `category`, `price`, `cost`, `stock_quantity`, `reorder_level`

### orders.csv (9 columns)

`order_id`, `customer_id`, `order_date`, `product_id`, `quantity`, `unit_price`, `total_amount`, `order_status`, `payment_date`

---

## Intentional Quality Issues

Defects are injected into **disjoint row sets** — no uncontrolled compound defects.

### Customers

| Defect | Count | Representation | Silver Issue Code |
|--------|-------|----------------|-------------------|
| NULL `email` | **50** | Empty string `""` | `completeness:email_null` |
| Duplicate `customer_id` | **10** extra rows | 10 appended copies → 10 keys appear twice (20 rows flagged) | `uniqueness:duplicate_customer_id` |

### Orders

| Defect | Count | Representation | Silver Issue Code |
|--------|-------|----------------|-------------------|
| NULL `customer_id` | **100** | Empty string `""` | `completeness:customer_id_null` |
| NULL `product_id` | **200** | Empty string `""` | `completeness:product_id_null` |
| Invalid `customer_id` | **50** | IDs `800001`–`800050` | `referential:invalid_customer_id` |
| Invalid `product_id` | **30** | IDs `700001`–`700030` | `referential:invalid_product_id` |
| Duplicate `order_id` | **20** extra rows | 20 appended copies → 20 keys appear twice (40 rows flagged) | `uniqueness:duplicate_order_id` |

### Products

**No intentional defects.** All 500 rows are fully valid.

### Estimated Problematic Rows (post-Silver)

| Entity | Rows with ≥1 intentional issue |
|--------|----------------------------------|
| Customers | ~70 (50 NULL email + 20 duplicate-PK rows) |
| Orders | ~420 (380 modified + 40 duplicate-PK rows, disjoint sets) |
| **Total** | **~490** |

> The assignment's ~700 problematic-row target will be approached when Silver business-logic checks run (e.g., `payment_before_order` edge cases are not injected at source). Source data contains **only** the 7 specified defect types.

---

## Validation

### Two-Layer Validation

| Layer | Script | When |
|-------|--------|------|
| Generator-internal | `validate_generated_data()` in `generate_sample_data.py` | Before CSV write; aborts on failure |
| Independent review | `validate_sample_data.py` | After generation; reads files from disk |

### Independent Validation Command

```bash
python src/data_generation/validate_sample_data.py \
  --data-dir data \
  --seed 42 \
  --report data/VALIDATION_REPORT.md
```

### Validation Categories (34 checks)

| # | Category | Checks | Result (2026-08-15) |
|---|----------|--------|---------------------|
| 1 | Row counts | 6 | **PASS** |
| 2 | Column names | 3 | **PASS** |
| 3 | Null counts | 5 | **PASS** |
| 4 | Duplicate PKs | 7 | **PASS** |
| 5 | Orphan FKs | 5 | **PASS** |
| 6 | Invalid values | 1 | **PASS** |
| 7 | Date ranges | 1 | **PASS** |
| 8 | Financial calculations | 2 | **PASS** |
| 9 | Intentional issue counts | 4 | **PASS** |

**Overall: 34/34 PASSED** — see `data/VALIDATION_REPORT.md` for full report.

### Key Validation Results (seed=42)

| Metric | Expected | Actual |
|--------|----------|--------|
| Customer rows | 10,010 | 10,010 |
| Product rows | 500 | 500 |
| Order rows | 100,020 | 100,020 |
| NULL emails | 50 | 50 |
| Duplicate customer_id extra rows | 10 | 10 |
| NULL customer_id | 100 | 100 |
| NULL product_id | 200 | 200 |
| Orphan customer_id | 50 | 50 |
| Orphan product_id | 30 | 30 |
| Duplicate order_id extra rows | 20 | 20 |
| Unexpected NULLs | 0 | 0 |
| Financial mismatches | 0 | 0 |
| Invalid domain values | 0 | 0 |

### Unit Tests

```bash
pytest tests/test_data_generation.py -v
```

---

## Data Realism Reference

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
| Order status | Completed 55%, Pending 15%, Shipped 15%, Cancelled 10%, Returned 5% |
| Payment date | Set for Completed/Shipped/Returned; empty for Pending/Cancelled |
| total_amount | Always `quantity × unit_price` (exact to 2 dp) |

---

## Known Limitations

| Limitation | Notes |
|------------|-------|
| **~700 problematic rows** | Source data yields ~490 intentionally problematic rows; remaining gap expected from Silver business-logic flags, not additional source defects |
| **No product defects** | Products are intentionally clean per assignment spec |
| **NULL representation** | Empty CSV strings; Bronze must preserve as-is for Silver to detect |
| **Duplicate rows** | Appended copies (not in-place overwrites); row count exceeds base by 10/20 |
| **Invalid FK ranges** | Hardcoded `800xxx` / `700xxx` — must not overlap valid ID ranges |
| **Single seed tested in CI** | Tests use seeds 42, 99, 7; production default is 42 |
| **No incremental generation** | Full overwrite on each run |
| **Windows console** | Validator report uses UTF-8; console may substitute `?` for emoji on cp1252 |

---

## Regeneration Procedure

```bash
# 1. Generate
python src/data_generation/generate_sample_data.py --output-dir data --seed 42

# 2. Independent validation (must pass before Bronze)
python src/data_generation/validate_sample_data.py --data-dir data --seed 42 --report data/VALIDATION_REPORT.md

# 3. Unit tests
pytest tests/test_data_generation.py -v
```

**Do not proceed to Bronze if any validation step fails.**

---

*Last updated: 2026-08-15 — independent validation passed (34/34)*
