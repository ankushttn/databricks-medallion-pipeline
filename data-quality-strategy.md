# Data Quality Strategy

**Project:** E-Commerce Medallion Architecture Data Pipeline  
**Version:** 2.0  
**Status:** Framework design complete — implementation pending  
**Related:** `data-model.md`, `design-notes.md`, `requirements-analysis.md` §6.4 & §11

---

## 1. Purpose

This document defines the **formal data quality framework** for the Silver layer. It specifies every validation check, how failures are flagged, how metrics are calculated, and how results remain auditable.

**Core mandate:** Bad records are **never deleted**. Every row from Bronze appears in Silver with explicit quality status and traceable failure reasons.

---

## 2. Framework Principles

| # | Principle | Implementation |
|---|-----------|----------------|
| P-01 | **Detect, don't delete** | `COUNT(bronze.*) = COUNT(silver.*)` per entity — always |
| P-02 | **Flag and measure** | Row-level `_quality_issues` + aggregate `silver.data_quality_summary` |
| P-03 | **Explain failures** | Every invalid row carries one or more machine-readable issue codes |
| P-04 | **Layer separation** | Quality logic runs only in Silver; Gold reads valid rows by default |
| P-05 | **Auditability** | Every run produces a `run_id`, timestamps, and persisted metrics |
| P-06 | **Deterministic checks** | Same input data produces identical flags and metrics |
| P-07 | **No silent drops** | Pipeline code errors fail the job; data errors are flagged and counted |

---

## 3. Quality Architecture

```text
bronze.<entity>
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│  Silver Validation Pipeline (create_silver_tables.py)    │
│                                                          │
│  1. Type casting (with type-failure flags)               │
│  2. 01_quality_completeness.py                           │
│  3. 02_quality_uniqueness.py                             │
│  4. 03_quality_type_validation.py                        │
│  5. 04_quality_referential_integrity.py  (orders only)   │
│  6. 05_quality_business_logic.py                         │
│  7. Consolidate flags → _is_valid, _quality_issues     │
│  8. Write silver.<entity> + silver.data_quality_summary  │
└──────────────────────────────────────────────────────────┘
       │
       ▼
silver.<entity>  (all rows retained, quality metadata attached)
```

### Processing Order

| Step | Entity | Rationale |
|------|--------|-----------|
| 1 | `silver.customers` | Parent dimension for order FK checks |
| 2 | `silver.products` | Parent dimension for order FK checks |
| 3 | `silver.orders` | Requires validated parent key sets |
| 4 | `silver.data_quality_summary` | Aggregated from all entity results |

---

## 4. Row-Level Quality Model

Every Silver entity row carries quality result columns in addition to business columns.

### 4.1 Quality Columns

| Column | Type | Description |
|--------|------|-------------|
| `_is_valid` | `BOOLEAN` | `true` when `_quality_issues` is empty; `false` otherwise |
| `_quality_issues` | `ARRAY<STRING>` | Ordered list of failed check issue codes (empty array = pass) |
| `_quality_status` | `STRING` | Derived: `VALID` if `_is_valid = true`, else `INVALID` |
| `_validated_at` | `TIMESTAMP` | UTC timestamp of the validation run |
| `_run_id` | `STRING` | Pipeline run identifier for audit linkage |

### 4.2 Issue Code Convention

```text
<dimension>:<specific_failure>

Examples:
  completeness:email_null
  uniqueness:duplicate_order_id
  type:signup_date_invalid
  referential:invalid_customer_id
  business:total_amount_mismatch
```

| Dimension Prefix | Script |
|------------------|--------|
| `completeness` | `01_quality_completeness.py` |
| `uniqueness` | `02_quality_uniqueness.py` |
| `type` | `03_quality_type_validation.py` |
| `referential` | `04_quality_referential_integrity.py` |
| `business` | `05_quality_business_logic.py` |

### 4.3 Multiple Failures on the Same Row

A single row **may fail multiple checks**. All failures are represented as follows:

| Representation | Rule |
|----------------|------|
| `_quality_issues` | **Append** every failed check's issue code; no deduplication unless the same code would repeat (it should not) |
| `_is_valid` | `false` if **any** check fails (logical AND of all checks) |
| `_quality_status` | `INVALID` if any issue present |
| Metric counting | Each issue code increments its own `issue_count` in `silver.data_quality_summary` — a row with 3 failures contributes 1 to each of 3 issue counts |
| Problematic row counting | A row counts **once** toward `invalid_records` regardless of how many issues it has |

**Example — order with compound failures:**

```text
order_id = 9001
customer_id = NULL
product_id = NULL
_quality_issues = [
  "completeness:customer_id_null",
  "completeness:product_id_null"
]
_is_valid = false
_quality_status = INVALID
```

**Example — customer with compound failures:**

```text
customer_id = 1042  (duplicate)
email = NULL
_quality_issues = [
  "completeness:email_null",
  "uniqueness:duplicate_customer_id"
]
_is_valid = false
```

### 4.4 Check Application Rules

| Rule | Description |
|------|-------------|
| **Referential checks on NULL FKs** | Skip referential check when FK is NULL; completeness check already flags the NULL |
| **Business logic on untyped rows** | Skip business rules on columns that failed type validation (avoid cascading false positives) |
| **Uniqueness on NULL PKs** | NULL PK is a completeness failure; uniqueness check applies only to non-null PK values |
| **All duplicate PK rows flagged** | Every row sharing a duplicated key is marked invalid — none are kept as "winner" |

---

## 5. Severity Model

| Severity | Code | Meaning | Pipeline Impact |
|----------|------|---------|-----------------|
| **Critical** | `CRITICAL` | Row cannot be trusted for analytics (PK null, duplicate PK, invalid FK) | Row excluded from Gold |
| **High** | `HIGH` | Required field missing or type invalid | Row excluded from Gold |
| **Medium** | `MEDIUM` | Business rule violation | Row excluded from Gold |
| **Low** | `LOW` | Warning-level (not used in assignment) | Row excluded from Gold if `_is_valid = false` |

> For this assignment, **any failed check** sets `_is_valid = false` regardless of severity. Severity is recorded in `silver.data_quality_summary` for audit prioritization.

---

## 6. Metrics Framework

### 6.1 Row-Level Metrics (per entity, per run)

| Metric | Formula | Description |
|--------|---------|-------------|
| `total_records` | `COUNT(*)` | All rows in Silver entity table |
| `valid_records` | `COUNT(*) WHERE _is_valid = true` | Rows passing all checks |
| `invalid_records` | `COUNT(*) WHERE _is_valid = false` | Rows with ≥1 issue |
| `pass_rate_pct` | `(valid_records / total_records) × 100` | Percentage of rows that passed |
| `fail_rate_pct` | `(invalid_records / total_records) × 100` | Percentage of rows that failed |
| `multi_issue_rows` | `COUNT(*) WHERE size(_quality_issues) > 1` | Rows with compound failures |

### 6.2 Check-Level Metrics (per issue code, per run)

| Metric | Formula | Description |
|--------|---------|-------------|
| `issue_count` | `COUNT(*) WHERE issue_code IN _quality_issues` | Rows failing this specific check |
| `issue_rate_pct` | `(issue_count / total_records) × 100` | Percentage of rows failing this check |
| `check_pass_rate_pct` | `100 - issue_rate_pct` | Percentage passing this specific check |

### 6.3 Pipeline-Level Metrics (all entities, per run)

| Metric | Formula | Assignment Target |
|--------|---------|-------------------|
| `total_invalid_rows` | `SUM(invalid_records)` across customers, orders, products | **≈ 700** |
| `overall_pass_rate_pct` | `(SUM(valid_records) / SUM(total_records)) × 100` | Document actual % |
| `total_issue_instances` | `SUM(issue_count)` across all issue codes | ≥ 460 (specified injections) |

### 6.4 Audit Table: `silver.data_quality_summary`

Persisted after every Silver run for auditability.

| Column | Type | Description |
|--------|------|-------------|
| `run_id` | `STRING` | Pipeline run identifier |
| `entity` | `STRING` | `customers`, `orders`, `products` |
| `check_id` | `STRING` | Formal check ID (e.g., `CMP-CUST-004`) |
| `check_dimension` | `STRING` | completeness, uniqueness, type, referential, business |
| `issue_code` | `STRING` | Machine-readable failure code |
| `severity` | `STRING` | CRITICAL, HIGH, MEDIUM |
| `issue_count` | `INT` | Rows with this issue |
| `issue_rate_pct` | `DECIMAL(5,2)` | `(issue_count / total_records) × 100` |
| `check_pass_rate_pct` | `DECIMAL(5,2)` | `100 - issue_rate_pct` |
| `total_records` | `INT` | Entity row count |
| `valid_records` | `INT` | Entity valid row count |
| `invalid_records` | `INT` | Entity invalid row count |
| `pass_rate_pct` | `DECIMAL(5,2)` | Entity-level pass rate |
| `reported_at` | `TIMESTAMP` | When metrics were written |

### 6.5 Logging Requirements

Every Silver run logs (via `logging` module):

```text
INFO  [run_id=20260815-001] silver.customers: total=5000 valid=4940 invalid=60 pass_rate=98.80%
INFO  [run_id=20260815-001] silver.customers issue completeness:email_null count=50 rate=1.00%
INFO  [run_id=20260815-001] silver.orders: total=25000 valid=24300 invalid=700 pass_rate=97.20%
INFO  [run_id=20260815-001] PIPELINE DQ SUMMARY: total_invalid_rows=700 overall_pass_rate=97.10%
```

---

## 7. Dimension 1 — Completeness

**Script:** `src/silver/01_quality_completeness.py`  
**Purpose:** Ensure required fields are present (not null and not empty string after trim).

**Global rule:** A null or blank (whitespace-only) value in a required column is a completeness failure.

**Threshold:** `0%` tolerance — any missing required value fails the check.  
**Invalid row flagging:** Append `completeness:<column>_null` to `_quality_issues`; set `_is_valid = false`.

---

### CMP-CUST-001 — Customer ID present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-CUST-001` |
| **Purpose** | Primary key must exist for every customer row |
| **Source table** | `bronze.customers` → `silver.customers` |
| **Columns** | `customer_id` |
| **Rule** | `customer_id IS NOT NULL` and not blank after trim |
| **Valid condition** | Non-null integer customer ID |
| **Invalid condition** | NULL or empty `customer_id` |
| **Severity** | CRITICAL |
| **Threshold** | 0% null rate |
| **Flagging** | `completeness:customer_id_null` |
| **Metric** | `COUNT(*) WHERE 'completeness:customer_id_null' IN _quality_issues` |
| **Expected intentional failures** | 0 (not injected in assignment) |
| **Test approach** | Seed row with NULL `customer_id`; assert issue code present and `_is_valid = false` |

---

### CMP-CUST-002 — Customer name present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-CUST-002` |
| **Purpose** | Customer name required for identification |
| **Source table** | `bronze.customers` → `silver.customers` |
| **Columns** | `customer_name` |
| **Rule** | `customer_name IS NOT NULL` and `TRIM(customer_name) != ''` |
| **Valid condition** | Non-empty name string |
| **Invalid condition** | NULL or blank name |
| **Severity** | HIGH |
| **Threshold** | 0% null rate |
| **Flagging** | `completeness:customer_name_null` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 (unless added in data generation) |
| **Test approach** | Seed blank name; assert flag |

---

### CMP-CUST-003 — Country present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-CUST-003` |
| **Purpose** | Country required for geographic analytics |
| **Source table** | `bronze.customers` → `silver.customers` |
| **Columns** | `country` |
| **Rule** | `country IS NOT NULL` and not blank |
| **Valid condition** | Non-empty country code/name |
| **Invalid condition** | NULL or blank country |
| **Severity** | HIGH |
| **Threshold** | 0% null rate |
| **Flagging** | `completeness:country_null` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed NULL country; assert flag |

---

### CMP-CUST-004 — Email present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-CUST-004` |
| **Purpose** | Email required for customer contact and communication analytics |
| **Source table** | `bronze.customers` → `silver.customers` |
| **Columns** | `email` |
| **Rule** | `email IS NOT NULL` and `TRIM(email) != ''` |
| **Valid condition** | Non-empty email string |
| **Invalid condition** | NULL or blank email |
| **Severity** | HIGH |
| **Threshold** | 0% null rate |
| **Flagging** | `completeness:email_null` |
| **Metric** | `issue_count` where code = `completeness:email_null` |
| **Expected intentional failures** | **50** (assignment DQ-C01) |
| **Test approach** | Run on generated data; assert `issue_count = 50`; verify `_is_valid = false` on those rows |

---

### CMP-CUST-005 — Signup date present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-CUST-005` |
| **Purpose** | Signup date required for cohort analysis |
| **Source table** | `bronze.customers` → `silver.customers` |
| **Columns** | `signup_date` |
| **Rule** | `signup_date IS NOT NULL` |
| **Valid condition** | Non-null date |
| **Invalid condition** | NULL signup date |
| **Severity** | HIGH |
| **Threshold** | 0% null rate |
| **Flagging** | `completeness:signup_date_null` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed NULL date; assert flag |

---

### CMP-CUST-006 — Customer segment present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-CUST-006` |
| **Purpose** | Segment required for Gold customer segmentation |
| **Source table** | `bronze.customers` → `silver.customers` |
| **Columns** | `customer_segment` |
| **Rule** | `customer_segment IS NOT NULL` and not blank |
| **Valid condition** | Non-empty segment label |
| **Invalid condition** | NULL or blank segment |
| **Severity** | HIGH |
| **Threshold** | 0% null rate |
| **Flagging** | `completeness:customer_segment_null` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed NULL segment; assert flag |

---

### CMP-PROD-001 — Product ID present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-PROD-001` |
| **Purpose** | Primary key must exist |
| **Source table** | `bronze.products` → `silver.products` |
| **Columns** | `product_id` |
| **Rule** | `product_id IS NOT NULL` |
| **Valid condition** | Non-null integer |
| **Invalid condition** | NULL product ID |
| **Severity** | CRITICAL |
| **Threshold** | 0% |
| **Flagging** | `completeness:product_id_null` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed NULL PK; assert flag |

---

### CMP-PROD-002 — Product name present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-PROD-002` |
| **Purpose** | Product name required for sales reporting |
| **Source table** | `bronze.products` → `silver.products` |
| **Columns** | `product_name` |
| **Rule** | Not null and not blank |
| **Valid condition** | Non-empty string |
| **Invalid condition** | NULL or blank |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `completeness:product_name_null` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed blank name; assert flag |

---

### CMP-PROD-003 — Category present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-PROD-003` |
| **Purpose** | Category required for product analytics |
| **Source table** | `bronze.products` → `silver.products` |
| **Columns** | `category` |
| **Rule** | Not null and not blank |
| **Valid condition** | Non-empty category |
| **Invalid condition** | NULL or blank |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `completeness:category_null` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed NULL category; assert flag |

---

### CMP-PROD-004 — Price present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-PROD-004` |
| **Purpose** | Price required for revenue calculations |
| **Source table** | `bronze.products` → `silver.products` |
| **Columns** | `price` |
| **Rule** | `price IS NOT NULL` |
| **Valid condition** | Non-null decimal |
| **Invalid condition** | NULL price |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `completeness:price_null` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed NULL price; assert flag |

---

### CMP-ORD-001 — Order ID present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-ORD-001` |
| **Purpose** | Primary key must exist |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `order_id` |
| **Rule** | `order_id IS NOT NULL` |
| **Valid condition** | Non-null integer |
| **Invalid condition** | NULL order ID |
| **Severity** | CRITICAL |
| **Threshold** | 0% |
| **Flagging** | `completeness:order_id_null` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed NULL PK; assert flag |

---

### CMP-ORD-002 — Customer ID present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-ORD-002` |
| **Purpose** | Every order must reference a customer |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `customer_id` |
| **Rule** | `customer_id IS NOT NULL` |
| **Valid condition** | Non-null integer customer ID |
| **Invalid condition** | NULL customer ID |
| **Severity** | CRITICAL |
| **Threshold** | 0% |
| **Flagging** | `completeness:customer_id_null` |
| **Metric** | `issue_count` where code = `completeness:customer_id_null` |
| **Expected intentional failures** | **100** (assignment DQ-O01) |
| **Test approach** | Run on generated data; assert `issue_count = 100` |

---

### CMP-ORD-003 — Product ID present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-ORD-003` |
| **Purpose** | Every order must reference a product |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `product_id` |
| **Rule** | `product_id IS NOT NULL` |
| **Valid condition** | Non-null integer product ID |
| **Invalid condition** | NULL product ID |
| **Severity** | CRITICAL |
| **Threshold** | 0% |
| **Flagging** | `completeness:product_id_null` |
| **Metric** | `issue_count` where code = `completeness:product_id_null` |
| **Expected intentional failures** | **200** (assignment DQ-O02) |
| **Test approach** | Run on generated data; assert `issue_count = 200` |

---

### CMP-ORD-004 — Order date present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-ORD-004` |
| **Purpose** | Order date required for trend analytics |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `order_date` |
| **Rule** | `order_date IS NOT NULL` |
| **Valid condition** | Non-null date |
| **Invalid condition** | NULL order date |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `completeness:order_date_null` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed NULL date; assert flag |

---

### CMP-ORD-005 — Quantity present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-ORD-005` |
| **Purpose** | Quantity required for sales calculations |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `quantity` |
| **Rule** | `quantity IS NOT NULL` |
| **Valid condition** | Non-null integer |
| **Invalid condition** | NULL quantity |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `completeness:quantity_null` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed NULL quantity; assert flag |

---

### CMP-ORD-006 — Unit price present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-ORD-006` |
| **Purpose** | Unit price required for amount validation |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `unit_price` |
| **Rule** | `unit_price IS NOT NULL` |
| **Valid condition** | Non-null decimal |
| **Invalid condition** | NULL unit price |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `completeness:unit_price_null` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed NULL; assert flag |

---

### CMP-ORD-007 — Total amount present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-ORD-007` |
| **Purpose** | Total amount required for revenue analytics |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `total_amount` |
| **Rule** | `total_amount IS NOT NULL` |
| **Valid condition** | Non-null decimal |
| **Invalid condition** | NULL total amount |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `completeness:total_amount_null` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed NULL; assert flag |

---

### CMP-ORD-008 — Order status present

| Field | Value |
|-------|-------|
| **Check ID** | `CMP-ORD-008` |
| **Purpose** | Status required for order lifecycle tracking |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `order_status` |
| **Rule** | Not null and not blank |
| **Valid condition** | Non-empty status string |
| **Invalid condition** | NULL or blank status |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `completeness:order_status_null` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed blank status; assert flag |

> **Note:** `payment_date` is nullable by design — no completeness check applies.

---

## 8. Dimension 2 — Uniqueness

**Script:** `src/silver/02_quality_uniqueness.py`  
**Purpose:** Detect duplicate primary key values within each entity.

**Global rule:** If a PK value appears more than once, **every row** with that PK value is flagged.

**Threshold:** `0%` duplicate rate.  
**Invalid row flagging:** Append `uniqueness:duplicate_<entity>_id` to `_quality_issues`.

---

### UNQ-CUST-001 — Unique customer ID

| Field | Value |
|-------|-------|
| **Check ID** | `UNQ-CUST-001` |
| **Purpose** | Each customer must have a unique identifier |
| **Source table** | `bronze.customers` → `silver.customers` |
| **Columns** | `customer_id` |
| **Rule** | `COUNT(*) OVER (PARTITION BY customer_id) = 1` for non-null IDs |
| **Valid condition** | `customer_id` appears exactly once |
| **Invalid condition** | `customer_id` shared by 2+ rows |
| **Severity** | CRITICAL |
| **Threshold** | 0% duplicates |
| **Flagging** | `uniqueness:duplicate_customer_id` on **all** rows sharing the duplicated key |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | **≥10 rows** flagged (assignment injects 10 duplicate `customer_id` values; if each duplicate appears twice, 20 rows flagged) |
| **Test approach** | Inject duplicate IDs; assert all duplicate rows flagged; assert no rows deleted |

---

### UNQ-PROD-001 — Unique product ID

| Field | Value |
|-------|-------|
| **Check ID** | `UNQ-PROD-001` |
| **Purpose** | Each product must have a unique identifier |
| **Source table** | `bronze.products` → `silver.products` |
| **Columns** | `product_id` |
| **Rule** | `product_id` appears exactly once among non-null values |
| **Valid condition** | Unique non-null `product_id` |
| **Invalid condition** | Duplicated `product_id` |
| **Severity** | CRITICAL |
| **Threshold** | 0% |
| **Flagging** | `uniqueness:duplicate_product_id` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 (unless added in data generation to reach ~700 rows) |
| **Test approach** | Inject duplicate; assert all copies flagged |

---

### UNQ-ORD-001 — Unique order ID

| Field | Value |
|-------|-------|
| **Check ID** | `UNQ-ORD-001` |
| **Purpose** | Each order must have a unique identifier |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `order_id` |
| **Rule** | `order_id` appears exactly once among non-null values |
| **Valid condition** | Unique non-null `order_id` |
| **Invalid condition** | Duplicated `order_id` |
| **Severity** | CRITICAL |
| **Threshold** | 0% |
| **Flagging** | `uniqueness:duplicate_order_id` on all rows sharing the key |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | **≥20 rows** flagged (assignment injects 20 duplicate `order_id` values) |
| **Test approach** | Run on generated data; assert duplicate order rows flagged; row count unchanged |

---

## 9. Dimension 3 — Type Validation

**Script:** `src/silver/03_quality_type_validation.py`  
**Purpose:** Verify values are castable to expected data types and formats.

**Threshold:** `0%` type failure rate on required typed columns.  
**Invalid row flagging:** Append `type:<column>_invalid` to `_quality_issues`.

---

### TYP-CUST-001 — Customer ID is integer

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-CUST-001` |
| **Purpose** | PK must be a valid integer |
| **Source table** | `bronze.customers` → `silver.customers` |
| **Columns** | `customer_id` |
| **Rule** | Castable to `INT`; no decimal, no alphabetic characters |
| **Valid condition** | Integer value |
| **Invalid condition** | Non-numeric or out-of-range value |
| **Severity** | CRITICAL |
| **Threshold** | 0% |
| **Flagging** | `type:customer_id_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed `"ABC"` as customer_id; assert flag |

---

### TYP-CUST-002 — Signup date is valid date

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-CUST-002` |
| **Purpose** | Signup date must parse as DATE |
| **Source table** | `bronze.customers` → `silver.customers` |
| **Columns** | `signup_date` |
| **Rule** | Parseable as `DATE` (`YYYY-MM-DD`) |
| **Valid condition** | Valid date |
| **Invalid condition** | Unparseable string (e.g., `2025-13-45`) |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `type:signup_date_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed invalid date string; assert flag |

---

### TYP-CUST-003 — Lifetime value is decimal

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-CUST-003` |
| **Purpose** | Lifetime value must be numeric |
| **Source table** | `bronze.customers` → `silver.customers` |
| **Columns** | `lifetime_value` |
| **Rule** | Castable to `DECIMAL(12,2)` |
| **Valid condition** | Valid decimal |
| **Invalid condition** | Non-numeric string |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `type:lifetime_value_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed `"N/A"`; assert flag |

---

### TYP-CUST-004 — Email format

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-CUST-004` |
| **Purpose** | Email must match basic format when present |
| **Source table** | `bronze.customers` → `silver.customers` |
| **Columns** | `email` |
| **Rule** | When non-null: matches pattern `^[^@]+@[^@]+\.[^@]+$` |
| **Valid condition** | Well-formed email |
| **Invalid condition** | Non-null but malformed (e.g., `not-an-email`) |
| **Severity** | MEDIUM |
| **Threshold** | 0% |
| **Flagging** | `type:email_format_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 (unless added in data generation) |
| **Test approach** | Seed malformed email (non-null); assert flag; NULL email caught by CMP-CUST-004 only |

---

### TYP-PROD-001 — Product ID is integer

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-PROD-001` |
| **Purpose** | PK must be valid integer |
| **Source table** | `bronze.products` → `silver.products` |
| **Columns** | `product_id` |
| **Rule** | Castable to `INT` |
| **Valid condition** | Integer |
| **Invalid condition** | Non-numeric |
| **Severity** | CRITICAL |
| **Threshold** | 0% |
| **Flagging** | `type:product_id_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed invalid ID; assert flag |

---

### TYP-PROD-002 — Price is decimal

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-PROD-002` |
| **Purpose** | Price must be numeric |
| **Source table** | `bronze.products` → `silver.products` |
| **Columns** | `price` |
| **Rule** | Castable to `DECIMAL(10,2)` |
| **Valid condition** | Valid decimal |
| **Invalid condition** | Non-numeric |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `type:price_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed `"FREE"`; assert flag |

---

### TYP-PROD-003 — Cost is decimal

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-PROD-003` |
| **Purpose** | Cost must be numeric |
| **Source table** | `bronze.products` → `silver.products` |
| **Columns** | `cost` |
| **Rule** | Castable to `DECIMAL(10,2)` |
| **Valid condition** | Valid decimal |
| **Invalid condition** | Non-numeric |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `type:cost_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed invalid cost; assert flag |

---

### TYP-PROD-004 — Stock quantity is integer

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-PROD-004` |
| **Purpose** | Stock must be whole number |
| **Source table** | `bronze.products` → `silver.products` |
| **Columns** | `stock_quantity` |
| **Rule** | Castable to `INT` |
| **Valid condition** | Integer |
| **Invalid condition** | Non-integer |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `type:stock_quantity_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed `12.5`; assert flag |

---

### TYP-ORD-001 — Order ID is integer

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-ORD-001` |
| **Purpose** | PK must be valid integer |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `order_id` |
| **Rule** | Castable to `INT` |
| **Valid condition** | Integer |
| **Invalid condition** | Non-numeric |
| **Severity** | CRITICAL |
| **Threshold** | 0% |
| **Flagging** | `type:order_id_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed invalid ID; assert flag |

---

### TYP-ORD-002 — Customer ID is integer

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-ORD-002` |
| **Purpose** | FK must be integer when present |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `customer_id` |
| **Rule** | When non-null: castable to `INT` |
| **Valid condition** | Integer or NULL (NULL handled by completeness) |
| **Invalid condition** | Non-null non-integer (e.g., `"CUST-001"`) |
| **Severity** | CRITICAL |
| **Threshold** | 0% |
| **Flagging** | `type:customer_id_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed non-integer FK; assert flag |

---

### TYP-ORD-003 — Product ID is integer

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-ORD-003` |
| **Purpose** | FK must be integer when present |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `product_id` |
| **Rule** | When non-null: castable to `INT` |
| **Valid condition** | Integer or NULL |
| **Invalid condition** | Non-null non-integer |
| **Severity** | CRITICAL |
| **Threshold** | 0% |
| **Flagging** | `type:product_id_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed non-integer FK; assert flag |

---

### TYP-ORD-004 — Order date is valid date

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-ORD-004` |
| **Purpose** | Order date must parse as DATE |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `order_date` |
| **Rule** | Parseable as `DATE` |
| **Valid condition** | Valid date |
| **Invalid condition** | Unparseable date |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `type:order_date_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed `99/99/9999`; assert flag |

---

### TYP-ORD-005 — Quantity is integer

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-ORD-005` |
| **Purpose** | Quantity must be whole number |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `quantity` |
| **Rule** | Castable to `INT` |
| **Valid condition** | Integer |
| **Invalid condition** | Non-integer (e.g., `2.5`) |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `type:quantity_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed decimal quantity; assert flag |

---

### TYP-ORD-006 — Unit price is decimal

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-ORD-006` |
| **Purpose** | Unit price must be numeric |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `unit_price` |
| **Rule** | Castable to `DECIMAL(10,2)` |
| **Valid condition** | Valid decimal |
| **Invalid condition** | Non-numeric |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `type:unit_price_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed invalid price; assert flag |

---

### TYP-ORD-007 — Total amount is decimal

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-ORD-007` |
| **Purpose** | Total amount must be numeric |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `total_amount` |
| **Rule** | Castable to `DECIMAL(12,2)` |
| **Valid condition** | Valid decimal |
| **Invalid condition** | Non-numeric |
| **Severity** | HIGH |
| **Threshold** | 0% |
| **Flagging** | `type:total_amount_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed invalid amount; assert flag |

---

### TYP-ORD-008 — Payment date is valid date (when present)

| Field | Value |
|-------|-------|
| **Check ID** | `TYP-ORD-008` |
| **Purpose** | Payment date must parse when provided |
| **Source table** | `bronze.orders` → `silver.orders` |
| **Columns** | `payment_date` |
| **Rule** | When non-null: parseable as `DATE` |
| **Valid condition** | Valid date or NULL |
| **Invalid condition** | Non-null unparseable date |
| **Severity** | MEDIUM |
| **Threshold** | 0% |
| **Flagging** | `type:payment_date_invalid` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 |
| **Test approach** | Seed invalid payment date; assert flag |

---

## 10. Dimension 4 — Referential Integrity

**Script:** `src/silver/04_quality_referential_integrity.py`  
**Purpose:** Verify foreign keys in orders resolve to existing parent records in Silver dimensions.

**Prerequisite:** `silver.customers` and `silver.products` must be validated first.  
**Threshold:** `0%` orphan rate for non-null FKs.  
**NULL FK handling:** Referential checks are **skipped** when FK is NULL (completeness already flags).

---

### REF-ORD-001 — Customer ID exists in customers

| Field | Value |
|-------|-------|
| **Check ID** | `REF-ORD-001` |
| **Purpose** | Every non-null `customer_id` must exist in `silver.customers` |
| **Source table** | `silver.orders` (FK) ← `silver.customers` (PK) |
| **Columns** | `orders.customer_id` → `customers.customer_id` |
| **Rule** | `customer_id IN (SELECT customer_id FROM silver.customers)` when not null |
| **Valid condition** | FK matches an existing customer row (any validity status) |
| **Invalid condition** | Non-null `customer_id` with no matching parent |
| **Severity** | CRITICAL |
| **Threshold** | 0% orphan rate |
| **Flagging** | `referential:invalid_customer_id` |
| **Metric** | `issue_count` where code = `referential:invalid_customer_id` |
| **Expected intentional failures** | **50** (assignment DQ-O03) |
| **Test approach** | Run on generated data; assert `issue_count = 50`; seed orphan ID in unit test |

---

### REF-ORD-002 — Product ID exists in products

| Field | Value |
|-------|-------|
| **Check ID** | `REF-ORD-002` |
| **Purpose** | Every non-null `product_id` must exist in `silver.products` |
| **Source table** | `silver.orders` (FK) ← `silver.products` (PK) |
| **Columns** | `orders.product_id` → `products.product_id` |
| **Rule** | `product_id IN (SELECT product_id FROM silver.products)` when not null |
| **Valid condition** | FK matches existing product |
| **Invalid condition** | Non-null `product_id` with no matching parent |
| **Severity** | CRITICAL |
| **Threshold** | 0% orphan rate |
| **Flagging** | `referential:invalid_product_id` |
| **Metric** | `issue_count` where code = `referential:invalid_product_id` |
| **Expected intentional failures** | **30** (assignment DQ-O04) |
| **Test approach** | Run on generated data; assert `issue_count = 30` |

---

## 11. Dimension 5 — Business Logic Validation

**Script:** `src/silver/05_quality_business_logic.py`  
**Purpose:** Enforce domain rules beyond structural validity.

**Prerequisite:** Type validation must pass on columns used in business rules (skip rule if type check failed).  
**Threshold:** `0%` violation rate unless noted.

---

### BUS-CUST-001 — Lifetime value non-negative

| Field | Value |
|-------|-------|
| **Check ID** | `BUS-CUST-001` |
| **Purpose** | Lifetime value cannot be negative |
| **Source table** | `silver.customers` |
| **Columns** | `lifetime_value` |
| **Rule** | `lifetime_value >= 0` |
| **Valid condition** | Zero or positive value |
| **Invalid condition** | Negative lifetime value |
| **Severity** | MEDIUM |
| **Threshold** | 0% |
| **Flagging** | `business:negative_lifetime_value` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | 0 (may be added in data generation to reach ~700 rows) |
| **Test approach** | Seed `-100.00`; assert flag |

---

### BUS-PROD-001 — Price positive

| Field | Value |
|-------|-------|
| **Check ID** | `BUS-PROD-001` |
| **Purpose** | Selling price must be greater than zero |
| **Source table** | `silver.products` |
| **Columns** | `price` |
| **Rule** | `price > 0` |
| **Valid condition** | Positive price |
| **Invalid condition** | Zero or negative price |
| **Severity** | MEDIUM |
| **Threshold** | 0% |
| **Flagging** | `business:non_positive_price` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | TBD in data generation (candidate for ~700 row gap) |
| **Test approach** | Seed `price = 0`; assert flag |

---

### BUS-PROD-002 — Cost non-negative

| Field | Value |
|-------|-------|
| **Check ID** | `BUS-PROD-002` |
| **Purpose** | Cost cannot be negative |
| **Source table** | `silver.products` |
| **Columns** | `cost` |
| **Rule** | `cost >= 0` |
| **Valid condition** | Zero or positive cost |
| **Invalid condition** | Negative cost |
| **Severity** | MEDIUM |
| **Threshold** | 0% |
| **Flagging** | `business:negative_cost` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | TBD in data generation |
| **Test approach** | Seed negative cost; assert flag |

---

### BUS-PROD-003 — Stock quantity non-negative

| Field | Value |
|-------|-------|
| **Check ID** | `BUS-PROD-003` |
| **Purpose** | Inventory cannot be negative |
| **Source table** | `silver.products` |
| **Columns** | `stock_quantity` |
| **Rule** | `stock_quantity >= 0` |
| **Valid condition** | Zero or positive stock |
| **Invalid condition** | Negative stock |
| **Severity** | MEDIUM |
| **Threshold** | 0% |
| **Flagging** | `business:negative_stock_quantity` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | TBD in data generation |
| **Test approach** | Seed `-5`; assert flag |

---

### BUS-PROD-004 — Reorder level non-negative

| Field | Value |
|-------|-------|
| **Check ID** | `BUS-PROD-004` |
| **Purpose** | Reorder threshold cannot be negative |
| **Source table** | `silver.products` |
| **Columns** | `reorder_level` |
| **Rule** | `reorder_level >= 0` |
| **Valid condition** | Zero or positive |
| **Invalid condition** | Negative reorder level |
| **Severity** | LOW |
| **Threshold** | 0% |
| **Flagging** | `business:negative_reorder_level` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | TBD in data generation |
| **Test approach** | Seed negative value; assert flag |

---

### BUS-ORD-001 — Quantity positive

| Field | Value |
|-------|-------|
| **Check ID** | `BUS-ORD-001` |
| **Purpose** | Order quantity must be at least 1 |
| **Source table** | `silver.orders` |
| **Columns** | `quantity` |
| **Rule** | `quantity > 0` |
| **Valid condition** | Positive integer quantity |
| **Invalid condition** | Zero or negative quantity |
| **Severity** | MEDIUM |
| **Threshold** | 0% |
| **Flagging** | `business:non_positive_quantity` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | TBD in data generation (candidate for ~700 row gap) |
| **Test approach** | Seed `quantity = 0`; assert flag |

---

### BUS-ORD-002 — Unit price positive

| Field | Value |
|-------|-------|
| **Check ID** | `BUS-ORD-002` |
| **Purpose** | Unit price must be greater than zero |
| **Source table** | `silver.orders` |
| **Columns** | `unit_price` |
| **Rule** | `unit_price > 0` |
| **Valid condition** | Positive unit price |
| **Invalid condition** | Zero or negative unit price |
| **Severity** | MEDIUM |
| **Threshold** | 0% |
| **Flagging** | `business:non_positive_unit_price` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | TBD in data generation |
| **Test approach** | Seed `unit_price = 0`; assert flag |

---

### BUS-ORD-003 — Total amount matches quantity × unit price

| Field | Value |
|-------|-------|
| **Check ID** | `BUS-ORD-003` |
| **Purpose** | Line total must be arithmetically consistent |
| **Source table** | `silver.orders` |
| **Columns** | `quantity`, `unit_price`, `total_amount` |
| **Rule** | `ABS(total_amount - (quantity * unit_price)) <= 0.01` |
| **Valid condition** | Total within $0.01 of computed value |
| **Invalid condition** | Mismatched total amount |
| **Severity** | MEDIUM |
| **Threshold** | 0% mismatch |
| **Flagging** | `business:total_amount_mismatch` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | TBD in data generation (candidate for ~700 row gap) |
| **Test approach** | Seed qty=2, price=10.00, total=25.00; assert flag |

---

### BUS-ORD-004 — Order status in allowed set

| Field | Value |
|-------|-------|
| **Check ID** | `BUS-ORD-004` |
| **Purpose** | Status must be a recognized order lifecycle state |
| **Source table** | `silver.orders` |
| **Columns** | `order_status` |
| **Rule** | `order_status IN ('Completed', 'Pending', 'Cancelled', 'Shipped', 'Returned')` |
| **Valid condition** | Known status value |
| **Invalid condition** | Unknown status string |
| **Severity** | MEDIUM |
| **Threshold** | 0% |
| **Flagging** | `business:invalid_order_status` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | TBD in data generation |
| **Test approach** | Seed `order_status = 'UNKNOWN'`; assert flag |

---

### BUS-ORD-005 — Payment date not before order date

| Field | Value |
|-------|-------|
| **Check ID** | `BUS-ORD-005` |
| **Purpose** | Payment cannot precede order placement |
| **Source table** | `silver.orders` |
| **Columns** | `order_date`, `payment_date` |
| **Rule** | When `payment_date IS NOT NULL`: `payment_date >= order_date` |
| **Valid condition** | Payment on or after order date |
| **Invalid condition** | Payment date before order date |
| **Severity** | MEDIUM |
| **Threshold** | 0% |
| **Flagging** | `business:payment_before_order` |
| **Metric** | Count rows with issue code |
| **Expected intentional failures** | TBD in data generation |
| **Test approach** | Seed payment_date < order_date; assert flag |

---

## 12. Expected Quality Metrics (Intentional Sample Data)

After Silver validation on the assignment dataset, the following metrics are **expected targets**. Exact totals depend on final data generation volumes documented in `DATA_GENERATION_NOTES.md`.

### 12.1 Mandatory Assignment Defects — Issue Count Targets

| Check ID | Issue Code | Expected `issue_count` |
|----------|------------|------------------------|
| `CMP-CUST-004` | `completeness:email_null` | **50** |
| `UNQ-CUST-001` | `uniqueness:duplicate_customer_id` | **≥10 rows** (all rows sharing 10 duplicated keys) |
| `CMP-ORD-002` | `completeness:customer_id_null` | **100** |
| `CMP-ORD-003` | `completeness:product_id_null` | **200** |
| `REF-ORD-001` | `referential:invalid_customer_id` | **50** |
| `REF-ORD-002` | `referential:invalid_product_id` | **30** |
| `UNQ-ORD-001` | `uniqueness:duplicate_order_id` | **≥20 rows** (all rows sharing 20 duplicated keys) |

**Specified issue instance minimum:** 460 (sum of injection counts)

### 12.2 Problematic Row Target

| Metric | Expected Value | Notes |
|--------|----------------|-------|
| `total_invalid_rows` (all entities) | **≈ 700** | Unique rows where `_is_valid = false` |
| `multi_issue_rows` | > 0 | Compound failures reduce unique row count vs issue instances |

### 12.3 Illustrative Entity-Level Metrics

> Replace `N` with actual row counts from data generation. Formulas are fixed.

| Entity | Metric | Formula / Target |
|--------|--------|------------------|
| `silver.customers` | `total_records` | N_customers |
| `silver.customers` | `invalid_records` | ≥ 60 (50 NULL email + duplicate rows) |
| `silver.customers` | `pass_rate_pct` | `(valid / total) × 100` |
| `silver.orders` | `invalid_records` | Majority of ~700 target |
| `silver.orders` | `pass_rate_pct` | `(valid / total) × 100` |
| `silver.products` | `invalid_records` | TBD — product business-logic defects for ~700 gap |
| **Pipeline** | `overall_pass_rate_pct` | `(SUM(valid) / SUM(total)) × 100` |

### 12.4 Validation Assertions (Acceptance)

| Assertion | Query / Check |
|-----------|---------------|
| No row deletion | `COUNT(bronze.*) = COUNT(silver.*)` per entity |
| Email nulls detected | `issue_count = 50` for `completeness:email_null` |
| Order null FKs detected | `issue_count = 100` and `200` respectively |
| Orphan FKs detected | `issue_count = 50` and `30` respectively |
| ~700 invalid rows | `SUM(invalid_records) BETWEEN 680 AND 720` (±3% tolerance) |
| Pass rate calculable | `pass_rate_pct` present in summary for every entity |
| Audit trail exists | `silver.data_quality_summary` has row per check per run |

---

## 13. Gold Consumption Rule

| Rule | Description |
|------|-------------|
| **Default filter** | Gold SQL uses `WHERE _is_valid = true` on all Silver inputs |
| **Invalid rows** | Excluded from revenue, sales, and segmentation metrics |
| **DQ analysis** | Ad-hoc queries may include invalid rows using `_quality_issues` — not used in standard Gold tables |
| **Quarantine views** | `silver.*_quarantine` views (optional) surface invalid rows for investigation |

---

## 14. Check Catalog Summary

| Dimension | Script | Check Count | Assignment-Mandated Checks |
|-----------|--------|-------------|---------------------------|
| Completeness | `01_quality_completeness.py` | 17 | 3 (email, customer_id, product_id nulls) |
| Uniqueness | `02_quality_uniqueness.py` | 3 | 2 (duplicate customer_id, order_id) |
| Type validation | `03_quality_type_validation.py` | 16 | 0 |
| Referential integrity | `04_quality_referential_integrity.py` | 2 | 2 (invalid customer_id, product_id) |
| Business logic | `05_quality_business_logic.py` | 10 | 0 (TBD for ~700 row gap) |
| **Total** | | **48** | **7 mandatory injection types** |

---

## 15. Implementation Notes (Design Only)

| Topic | Design Decision |
|-------|-----------------|
| Row retention | `create_silver_tables.py` writes all Bronze rows to Silver |
| Flag consolidation | Each dimension script returns issue codes per row; orchestrator merges into `_quality_issues` |
| Final validity | `_is_valid = (size(_quality_issues) = 0)` |
| Summary write | After all entities validated, aggregate issue counts into `silver.data_quality_summary` |
| Re-runs | Full overwrite of Silver tables and DQ summary per run; `_run_id` distinguishes runs |
| Tests | `tests/test_silver_quality.py` validates each mandatory check count and row retention |

---

## 16. Document Cross-References

| Topic | Document |
|-------|----------|
| Table schemas | `data-model.md` §5 |
| Architecture & DQ reporting table | `design-notes.md` §4, §11 |
| Assignment defect specification | `requirements-analysis.md` §6.4 |
| Implementation tasks | `cursor-workflow/task-breakdown.md` Phase 3 |

---

*Last updated: 2026-08-15*
