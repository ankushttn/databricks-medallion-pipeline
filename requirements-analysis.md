# Requirements Analysis

**Project:** E-Commerce Medallion Architecture Data Pipeline  
**Version:** 1.0  
**Status:** Foundation complete — implementation pending  
**Source of truth:** Assignment specification, project `cursor-workflow/spec.md`, and repository design documents

---

## 1. Problem Statement

An e-commerce organization needs a reliable analytics data pipeline that ingests customer, order, and product data from CSV sources, lands it in a governed lakehouse, validates data quality without losing auditability, and produces business-ready metrics for sales, revenue, trends, and customer segmentation.

The source data is intentionally imperfect. Approximately **700 rows** across the dataset contain known quality defects (nulls, duplicates, invalid foreign keys). The pipeline must ingest all records, **detect and flag** defects in Silver, and build Gold analytics from validated data — not by silently discarding problematic source rows.

---

## 2. Business Objective

| Objective | Description |
|-----------|-------------|
| **Trusted analytics** | Deliver accurate sales and customer insights from governed Gold tables |
| **Data quality visibility** | Make quality issues measurable and auditable at the Silver layer |
| **Scalable pattern** | Demonstrate a reusable Bronze → Silver → Gold medallion architecture on Databricks |
| **Operational readiness** | Production-oriented code with logging, tests, documentation, and version control |

**Success looks like:** Stakeholders can query Gold tables and dashboards for e-commerce KPIs, while data engineers can quantify how many records failed each quality rule and why.

---

## 3. Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-01 | Generate deterministic sample CSV data for customers, orders, and products |
| FR-02 | Inject intentional data-quality defects per assignment specification (see §6) |
| FR-03 | Ingest all three CSV sources into Bronze Delta tables without business transformations |
| FR-04 | Apply five Silver quality dimensions: completeness, uniqueness, type validation, referential integrity, business logic |
| FR-05 | Flag invalid records in Silver; do **not** delete intentionally bad source rows |
| FR-06 | Produce four Gold aggregations: sales by product, revenue by customer, daily/weekly trends, customer segmentation |
| FR-07 | Provide dashboard SQL queries and setup guide consuming Gold tables |
| FR-08 | Orchestrate Bronze ingestion via `ingest_all.py` |
| FR-09 | Orchestrate Silver table creation via `create_silver_tables.py` |
| FR-10 | Orchestrate Gold table creation via `create_gold_tables.py` |
| FR-11 | Log quality metrics (totals, valid/invalid counts, issue breakdown) after Silver runs |

---

## 4. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | **Reproducibility** — sample data generation uses a fixed random seed |
| NFR-02 | **Maintainability** — readable Python with type hints and docstrings on important functions |
| NFR-03 | **Observability** — use `logging` (not `print`) for pipeline diagnostics |
| NFR-04 | **Security** — no hardcoded secrets; credentials via Databricks secrets or environment variables |
| NFR-05 | **Auditability** — Bronze preserves raw data; Silver adds `_is_valid`, `_quality_issues`, `_validated_at` |
| NFR-06 | **Testability** — every major component has automated tests or documented validation |
| NFR-07 | **Traceability** — AI-assisted development sessions documented in `ai-prompts/` |
| NFR-08 | **Portability** — pipeline runs on Databricks with Delta Lake storage |

---

## 5. Technical Requirements

| ID | Requirement |
|----|-------------|
| TR-01 | **Language:** Python (PySpark) for data generation, Bronze, Silver, and Gold orchestration |
| TR-02 | **Language:** SQL for Gold aggregations and dashboard queries |
| TR-03 | **Platform:** Databricks workspace for execution |
| TR-04 | **Storage:** Delta Lake tables in `bronze`, `silver`, and `gold` schemas (or equivalent catalog structure) |
| TR-05 | **Version control:** Git repository with structured commits |
| TR-06 | **AI tooling:** Cursor with project rules in `.cursor/rules/` |
| TR-07 | **Bronze metadata:** add `_ingested_at` (timestamp) and `_source_file` (string) on ingest |
| TR-08 | **Silver metadata:** add `_is_valid` (boolean), `_quality_issues` (array of strings), `_validated_at` (timestamp) |
| TR-09 | **Schema reference:** `database/schema.sql` defines catalog/schema structure |
| TR-10 | **No architectural drift** — Bronze/Silver/Gold responsibilities fixed unless explicitly approved |

### Technology Stack

```
Python + PySpark  →  Bronze ingestion, Silver validation, orchestrators
SQL               →  Gold aggregations, dashboard queries
Databricks        →  Execution runtime
Delta Lake        →  ACID table format (all layers)
Git + Cursor      →  Version control and AI-assisted development
```

---

## 6. Source Data Requirements

### 6.1 Entities and Files

| Entity | File | Primary Key | Foreign Keys |
|--------|------|-------------|--------------|
| Customers | `data/customers.csv` | `customer_id` | — |
| Products | `data/products.csv` | `product_id` | — |
| Orders | `data/orders.csv` | `order_id` | `customer_id` → customers; `product_id` → products |

### 6.2 Column Specifications

**Customers**

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `customer_id` | string | Yes | Must be unique in valid set |
| `name` | string | Yes | |
| `email` | string | Yes | Completeness check target |
| `segment` | string | Yes | Used in Gold segmentation |
| `created_at` | timestamp/date | Yes | |

**Products**

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `product_id` | string | Yes | Must be unique in valid set |
| `name` | string | Yes | |
| `category` | string | Yes | |
| `unit_price` | decimal | Yes | Business-logic validation target |

**Orders**

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `order_id` | string | Yes | Must be unique in valid set |
| `customer_id` | string | Yes | FK → `customers.customer_id` |
| `product_id` | string | Yes | FK → `products.product_id` |
| `quantity` | integer | Yes | Must be positive |
| `order_date` | date | Yes | Used in trend aggregations |
| `total_amount` | decimal | Yes | Business-logic validation target |

### 6.3 Data Generation Requirements

| ID | Requirement |
|----|-------------|
| SD-01 | Implement `src/data_generation/generate_sample_data.py` |
| SD-02 | Use a fixed random seed for deterministic output |
| SD-03 | Write output to `data/customers.csv`, `data/orders.csv`, `data/products.csv` |
| SD-04 | Document generation logic and defect injection in `DATA_GENERATION_NOTES.md` |
| SD-05 | Dataset must contain **approximately 700 problematic rows** (rows with at least one intentional quality defect) |

### 6.4 Intentional Data-Quality Defects (Assignment Specification)

The data generator **must** inject the following defects. Silver validation **must** detect and flag them.

#### Customers (`data/customers.csv`)

| Defect ID | Issue | Count | Silver Check |
|-----------|-------|-------|--------------|
| DQ-C01 | NULL `email` values | **50** | Completeness |
| DQ-C02 | Duplicate `customer_id` records | **10** | Uniqueness |

**Customer defect subtotal:** 60 specified issue instances

#### Orders (`data/orders.csv`)

| Defect ID | Issue | Count | Silver Check |
|-----------|-------|-------|--------------|
| DQ-O01 | NULL `customer_id` values | **100** | Completeness |
| DQ-O02 | NULL `product_id` values | **200** | Completeness |
| DQ-O03 | Invalid `customer_id` values (non-null, not in customers) | **50** | Referential integrity |
| DQ-O04 | Invalid `product_id` values (non-null, not in products) | **30** | Referential integrity |
| DQ-O05 | Duplicate `order_id` records | **20** | Uniqueness |

**Order defect subtotal:** 400 specified issue instances

#### Specified Defect Instance Total

| Category | Count |
|----------|-------|
| Customer defects | 60 |
| Order defects | 400 |
| **Specified issue instances** | **460** |

#### Approximately 700 Problematic Rows

The assignment requires the generated dataset to contain **approximately 700 rows with quality problems**. This is the target for **unique rows flagged as invalid** (`_is_valid = false`) across all Silver entity tables after validation.

| Metric | Value | Notes |
|--------|-------|-------|
| Specified defect injections | 460 instances | Counts in tables above |
| Target problematic rows | **~700** | Rows with ≥1 quality issue |
| Gap to reconcile | ~240 rows | Additional defects (e.g., product business-logic issues, order business-logic issues, or rows with multiple counted defects) must be designed during data generation to reach ~700 without conflicting with the specified counts above |

> **Note:** A single row may contribute to multiple issue types (e.g., an order with both NULL `customer_id` and NULL `product_id` counts as one problematic row but two completeness failures). Data generation must document how the ~700 target is achieved alongside the mandatory injection counts.

---

## 7. Bronze Requirements

| ID | Requirement |
|----|-------------|
| BR-01 | Ingest `data/customers.csv` → `bronze.customers` via `01_ingest_customers.py` |
| BR-02 | Ingest `data/orders.csv` → `bronze.orders` via `02_ingest_orders.py` |
| BR-03 | Ingest `data/products.csv` → `bronze.products` via `03_ingest_products.py` |
| BR-04 | Orchestrate all ingestions via `ingest_all.py` |
| BR-05 | Preserve source column values exactly as read from CSV (raw landing zone) |
| BR-06 | Append ingestion metadata: `_ingested_at`, `_source_file` |
| BR-07 | Write to Delta Lake format |
| BR-08 | Do **not** apply quality rules, deduplication, or business logic in Bronze |
| BR-09 | Log ingestion row counts and file paths |

---

## 8. Silver Requirements

| ID | Requirement |
|----|-------------|
| SV-01 | Read from Bronze tables; write to `silver.customers`, `silver.orders`, `silver.products` |
| SV-02 | Implement completeness checks in `01_quality_completeness.py` |
| SV-03 | Implement uniqueness checks in `02_quality_uniqueness.py` |
| SV-04 | Implement type validation in `03_quality_type_validation.py` |
| SV-05 | Implement referential integrity in `04_quality_referential_integrity.py` |
| SV-06 | Implement business logic in `05_quality_business_logic.py` |
| SV-07 | Orchestrate Silver pipeline via `create_silver_tables.py` |
| SV-08 | Set `_is_valid = true` only when all applicable checks pass |
| SV-09 | Populate `_quality_issues` with descriptive, machine-readable issue codes |
| SV-10 | Set `_validated_at` on every validation run |
| SV-11 | **Never delete** intentionally bad records — retain all Bronze rows in Silver |
| SV-12 | Emit quality summary metrics: `total_records`, `valid_records`, `invalid_records`, `issue_breakdown` |
| SV-13 | Detect all intentional defects listed in §6.4 |

### Silver Quality Dimensions

| Dimension | Script | Key Checks |
|-----------|--------|------------|
| Completeness | `01_quality_completeness.py` | Non-null PKs; required fields (e.g., `email`, `customer_id`, `product_id`) |
| Uniqueness | `02_quality_uniqueness.py` | Duplicate `customer_id`, `order_id`, `product_id` |
| Type validation | `03_quality_type_validation.py` | Numeric types, date formats, email format |
| Referential integrity | `04_quality_referential_integrity.py` | `orders.customer_id` → customers; `orders.product_id` → products |
| Business logic | `05_quality_business_logic.py` | Positive `quantity`; valid `unit_price`; `total_amount` consistency |

---

## 9. Gold Requirements

| ID | Requirement |
|----|-------------|
| GD-01 | Read from validated Silver data (`_is_valid = true` unless explicitly analyzing quality) |
| GD-02 | Create `gold.sales_by_product` via `01_sales_by_product.sql` |
| GD-03 | Create `gold.revenue_by_customer` via `02_revenue_by_customer.sql` |
| GD-04 | Create `gold.daily_weekly_trends` via `03_daily_weekly_trends.sql` |
| GD-05 | Create `gold.customer_segmentation` via `04_customer_segmentation.sql` |
| GD-06 | Orchestrate Gold builds via `create_gold_tables.py` |
| GD-07 | Write results to Delta Lake Gold tables |
| GD-08 | SQL must be readable, formatted, and analytics-facing |

### Gold Deliverables

| Table | Grain | Key Metrics |
|-------|-------|-------------|
| `gold.sales_by_product` | product | units sold, revenue |
| `gold.revenue_by_customer` | customer | total revenue, order count |
| `gold.daily_weekly_trends` | day / week | revenue, order count over time |
| `gold.customer_segmentation` | customer segment | segment-level KPIs |

---

## 10. Dashboard Requirements

| ID | Requirement |
|----|-------------|
| DB-01 | Provide analytics SQL in `src/dashboard/dashboard_queries.sql` |
| DB-02 | Queries must read from Gold tables only |
| DB-03 | Cover all four Gold use cases: sales by product, revenue by customer, trends, segmentation |
| DB-04 | Document BI setup steps in `DASHBOARD_GUIDE.md` |
| DB-05 | Support Databricks SQL Dashboard or equivalent BI tool |

---

## 11. Data Quality Requirements

| ID | Requirement |
|----|-------------|
| DQ-01 | All intentional defects (§6.4) must be present in generated source data |
| DQ-02 | Approximately **700 rows** must be flagged as problematic after Silver validation |
| DQ-03 | Quality issues must be **flagged**, not silently removed |
| DQ-04 | Each failed check must appear in `_quality_issues` with a traceable code |
| DQ-05 | Quality metrics must be **measurable** (counts per issue type, valid/invalid totals) |
| DQ-06 | Gold aggregations exclude invalid Silver rows by default |
| DQ-07 | Five quality dimensions must each have a dedicated Silver script |
| DQ-08 | Duplicate PK records remain in Silver but are flagged (`_is_valid = false`) |
| DQ-09 | NULL FK values are completeness failures; invalid FK values are referential integrity failures |

### Defect-to-Check Mapping

| Defect | Count | Quality Dimension | Expected Flag Example |
|--------|-------|-------------------|----------------------|
| NULL email (customers) | 50 | Completeness | `completeness:email_null` |
| Duplicate customer_id | 10 | Uniqueness | `uniqueness:duplicate_customer_id` |
| NULL customer_id (orders) | 100 | Completeness | `completeness:customer_id_null` |
| NULL product_id (orders) | 200 | Completeness | `completeness:product_id_null` |
| Invalid customer_id (orders) | 50 | Referential integrity | `referential:invalid_customer_id` |
| Invalid product_id (orders) | 30 | Referential integrity | `referential:invalid_product_id` |
| Duplicate order_id | 20 | Uniqueness | `uniqueness:duplicate_order_id` |

---

## 12. Testing Requirements

| ID | Requirement |
|----|-------------|
| TS-01 | Every major implementation component must have tests or explicit validation steps |
| TS-02 | Data generation tests: verify seed reproducibility and defect counts |
| TS-03 | Bronze tests: verify row counts match CSV; metadata columns present; no transformations |
| TS-04 | Silver tests: verify each defect type is flagged; `_is_valid` logic correct; no row deletion |
| TS-05 | Gold tests: verify aggregation correctness on known valid subset |
| TS-06 | Tests live under `tests/` |
| TS-07 | Validation must confirm ~700 problematic rows are flagged in Silver |

---

## 13. Documentation Requirements

| ID | Requirement |
|----|-------------|
| DC-01 | `README.md` — project overview and getting started |
| DC-02 | `candidate-info.md` — submission metadata and checklist |
| DC-03 | `requirements-analysis.md` — this document |
| DC-04 | `design-notes.md` — architecture decisions |
| DC-05 | `data-model.md` — entity relationships and schemas |
| DC-06 | `data-quality-strategy.md` — Silver quality approach |
| DC-07 | `tool-workflow.md` — development toolchain |
| DC-08 | `debugging-notes.md` — issue log |
| DC-09 | `reflection.md` — post-project reflection (completed at submission) |
| DC-10 | `final-ai-usage-summary.md` — AI usage summary (completed at submission) |
| DC-11 | `database/setup-notes.md` and `database/seed-data-notes.md` |
| DC-12 | `src/data_generation/DATA_GENERATION_NOTES.md` |
| DC-13 | `src/dashboard/DASHBOARD_GUIDE.md` |

---

## 14. AI / Cursor Workflow Requirements

| ID | Requirement |
|----|-------------|
| AI-01 | Use Cursor as the AI development assistant |
| AI-02 | Enforce standards via `.cursor/rules/medallion-pipeline.mdc` |
| AI-03 | Log every major Cursor session in `ai-prompts/` (prompt, outcome, files touched) |
| AI-04 | Maintain `cursor-workflow/project-context.md`, `spec.md`, `task-breakdown.md` |
| AI-05 | Inspect existing project before large changes; reuse components |
| AI-06 | Do not create duplicate utilities or logic |
| AI-07 | Complete `final-ai-usage-summary.md` at project end |
| AI-08 | Do not modify architecture without documented rationale and approval |

---

## 15. Git / Version-Control Requirements

| ID | Requirement |
|----|-------------|
| VC-01 | All project artifacts tracked in Git |
| VC-02 | Use meaningful commit messages describing *why* changes were made |
| VC-03 | Recommended feature branches per layer (`feature/bronze-ingest`, etc.) |
| VC-04 | Do not commit secrets (`.env`, credentials, tokens) — enforced by `.gitignore` |
| VC-05 | Repository structure matches assignment specification |
| VC-06 | Cloud agents work on separate branches; never push directly to `main` |

---

## 16. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-01 | All three CSV sources ingested into Bronze Delta tables unchanged (plus metadata) | Row-count match; spot-check raw values |
| AC-02 | Silver implements all five quality dimensions | Each script runs; flags populated |
| AC-03 | All §6.4 intentional defects are detected and flagged | Issue counts match expected injection counts |
| AC-04 | Approximately **700 rows** flagged as problematic in Silver | `invalid_records` sum ≈ 700 across entities |
| AC-05 | No intentionally bad records deleted from Silver | Bronze row count = Silver row count per entity |
| AC-06 | Four Gold tables created with correct business logic | SQL output matches expected aggregates on valid data |
| AC-07 | Dashboard queries run against Gold tables | Queries execute without error in Databricks SQL |
| AC-08 | Pipeline runs end-to-end on Databricks | Bronze → Silver → Gold completes |
| AC-09 | Tests or validation exist for major components | Test suite passes or validation documented |
| AC-10 | No secrets in source code | Code review / `.gitignore` check |
| AC-11 | AI usage documented in `ai-prompts/` and summary file | All layer prompt files updated |
| AC-12 | `reflection.md` and `candidate-info.md` completed | Submission checklist complete |
| AC-13 | Sample data is deterministic (fixed seed) | Re-running generator produces identical CSVs |

---

## 17. Assumptions

| # | Assumption |
|---|------------|
| A-01 | Databricks workspace is available with permissions to create schemas and Delta tables |
| A-02 | Unity Catalog or Hive metastore is configured; schemas named `bronze`, `silver`, `gold` |
| A-03 | CSV files are the sole source system for this assignment |
| A-04 | "Invalid" foreign keys are non-null values that do not exist in the parent entity |
| A-05 | "NULL" means empty/missing values in CSV (empty string or null literal) |
| A-06 | Duplicate records share the same primary key value as another row in the same entity |
| A-07 | Additional product-level or business-logic defects may be injected to reach ~700 problematic rows beyond the 460 specified instances |
| A-08 | Gold excludes `_is_valid = false` rows unless a query explicitly analyzes data quality |
| A-09 | Python 3.10+ and PySpark compatible with the target Databricks runtime |
| A-10 | Assignment does not require real-time streaming — batch processing is sufficient |

---

## 18. Edge Cases

| # | Edge Case | Expected Handling |
|---|-----------|-------------------|
| EC-01 | Order has both NULL and invalid `customer_id` | Flag both issues in `_quality_issues`; `_is_valid = false` |
| EC-02 | Duplicate `customer_id` where one row also has NULL email | Both uniqueness and completeness flags applied |
| EC-03 | Duplicate `order_id` with different attribute values | Both/all rows flagged; none deleted |
| EC-04 | NULL `product_id` — referential check skipped or fails completeness first | Completeness flagged; referential check does not mask completeness failure |
| EC-05 | Valid order references customer flagged invalid in Silver | Gold excludes invalid orders; customer may still appear with zero revenue |
| EC-06 | All orders for a product are invalid | `gold.sales_by_product` shows zero or omits product |
| EC-07 | Re-running Bronze ingest on existing Delta table | Define idempotent strategy (overwrite/append) — document in implementation |
| EC-08 | CSV encoding or date format inconsistencies | Type validation flags affected rows |
| EC-09 | Empty CSV file (header only) | Bronze ingests zero rows; Silver/Gold handle gracefully with logging |
| EC-10 | Multiple defects on one row counted toward ~700 target | Row counted once as problematic; issues array lists all failures |

---

## 19. Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| R-01 | ~700 problematic rows not achieved during data generation | Silver validation metrics fail acceptance | Document injection plan in `DATA_GENERATION_NOTES.md`; add generation validation tests |
| R-02 | Accidental row deletion in Silver | Loss of auditability; assignment failure | Code review; test asserting row-count parity Bronze ↔ Silver |
| R-03 | Gold includes invalid Silver rows | Inflated revenue/metrics | Default filter `_is_valid = true`; test Gold input filters |
| R-04 | Hardcoded secrets committed | Security exposure | `.gitignore`; Cursor rules; pre-commit review |
| R-05 | Non-deterministic data generation | Non-reproducible tests | Fixed `random.seed()`; test byte/hash comparison |
| R-06 | Referential integrity order of execution | Customers/products must exist before order FK checks | Orchestrate Silver: dimensions first, then orders |
| R-07 | Duplicate PK handling ambiguity | Unclear which duplicate is "valid" | Flag **all** rows sharing a duplicate key as invalid |
| R-08 | Databricks environment differences | Runtime failures | Document DBR version and cluster/serverless config in `setup-notes.md` |
| R-09 | Insufficient test coverage | Undetected regressions | Require tests per layer before merge |
| R-10 | AI-generated code diverges from medallion principles | Architecture drift | Cursor rules; review against this document |

---

## 20. Clarifications / Questions

| # | Question | Proposed Resolution | Status |
|---|----------|---------------------|--------|
| Q-01 | How exactly should ~700 problematic rows be reached given 460 specified defect instances? | Inject additional product business-logic defects (e.g., invalid `unit_price`) and/or order business-logic defects; document final counts in `DATA_GENERATION_NOTES.md` | **Open** — confirm with assignment instructor |
| Q-02 | Are duplicate PK rows counted as one or multiple problematic rows toward ~700? | Count each **row** with `_is_valid = false` once toward the total | **Assumed** per EC-10 |
| Q-03 | Should Bronze use overwrite or merge on re-run? | Overwrite per entity for idempotent dev runs | **Open** |
| Q-04 | Unity Catalog vs Hive metastore naming? | Configurable catalog prefix; default `bronze.*`, `silver.*`, `gold.*` | **Open** |
| Q-05 | Are product-level intentional defects specified beyond orders/customers? | Not in assignment text; may be needed to reach ~700 rows | **Open** |
| Q-06 | Which Databricks compute model (classic cluster vs serverless)? | Document choice in `database/setup-notes.md` | **Open** |
| Q-07 | Exact row volumes for customers, orders, products? | Sized to accommodate defect injections and realistic analytics; document in data generation | **Open** |

---

## Traceability Matrix

| Requirement ID | Requirement | Implementation File | Test | Expected Result | Status |
|----------------|-------------|---------------------|------|-----------------|--------|
| FR-01 | Deterministic sample data generation | `src/data_generation/generate_sample_data.py` | `tests/test_data_generation.py` | Identical CSVs on repeated runs | Pending |
| FR-02 | Inject intentional DQ defects (§6.4) | `src/data_generation/generate_sample_data.py` | `tests/test_data_generation.py` | 50 NULL emails, 10 dup customer_id, 100 NULL customer_id, 200 NULL product_id, 50 invalid customer_id, 30 invalid product_id, 20 dup order_id | Pending |
| FR-03 | Bronze ingest all CSVs | `src/bronze/01_*.py`, `ingest_all.py` | `tests/test_bronze_ingest.py` | Delta tables populated; raw values preserved | Pending |
| FR-04 | Five Silver quality dimensions | `src/silver/01_–05_*.py` | `tests/test_silver_quality.py` | All dimensions execute; flags set | Pending |
| FR-05 | Flag, don't delete bad records | `src/silver/create_silver_tables.py` | `tests/test_silver_quality.py` | Bronze row count = Silver row count | Pending |
| FR-06 | Four Gold aggregations | `src/gold/01_–04_*.sql`, `create_gold_tables.py` | `tests/test_gold_aggregations.py` | Four Gold tables exist with correct metrics | Pending |
| FR-07 | Dashboard queries | `src/dashboard/dashboard_queries.sql` | Manual / integration validation | Queries return results from Gold | Pending |
| FR-08 | Bronze orchestrator | `src/bronze/ingest_all.py` | `tests/test_bronze_ingest.py` | All three entities ingested in one run | Pending |
| FR-09 | Silver orchestrator | `src/silver/create_silver_tables.py` | `tests/test_silver_quality.py` | All Silver tables created with quality metadata | Pending |
| FR-10 | Gold orchestrator | `src/gold/create_gold_tables.py` | `tests/test_gold_aggregations.py` | All Gold tables built from SQL scripts | Pending |
| FR-11 | Quality metrics logging | `src/silver/create_silver_tables.py` | `tests/test_silver_quality.py` | Logs show total/valid/invalid/issue breakdown | Pending |
| SD-05 | ~700 problematic rows | `src/data_generation/generate_sample_data.py` | `tests/test_data_generation.py` | Silver `invalid_records` ≈ 700 | Pending |
| DQ-C01 | 50 NULL emails | `src/silver/01_quality_completeness.py` | `tests/test_silver_quality.py` | 50 rows flagged `completeness:email_null` | Pending |
| DQ-C02 | 10 duplicate customer_id | `src/silver/02_quality_uniqueness.py` | `tests/test_silver_quality.py` | 10+ rows flagged for duplicate customer_id | Pending |
| DQ-O01 | 100 NULL customer_id | `src/silver/01_quality_completeness.py` | `tests/test_silver_quality.py` | 100 rows flagged `completeness:customer_id_null` | Pending |
| DQ-O02 | 200 NULL product_id | `src/silver/01_quality_completeness.py` | `tests/test_silver_quality.py` | 200 rows flagged `completeness:product_id_null` | Pending |
| DQ-O03 | 50 invalid customer_id | `src/silver/04_quality_referential_integrity.py` | `tests/test_silver_quality.py` | 50 rows flagged `referential:invalid_customer_id` | Pending |
| DQ-O04 | 30 invalid product_id | `src/silver/04_quality_referential_integrity.py` | `tests/test_silver_quality.py` | 30 rows flagged `referential:invalid_product_id` | Pending |
| DQ-O05 | 20 duplicate order_id | `src/silver/02_quality_uniqueness.py` | `tests/test_silver_quality.py` | 20+ rows flagged for duplicate order_id | Pending |
| BR-05 | Bronze preserves raw data | `src/bronze/01_–03_*.py` | `tests/test_bronze_ingest.py` | Column values match CSV source | Pending |
| BR-06 | Bronze ingestion metadata | `src/bronze/01_–03_*.py` | `tests/test_bronze_ingest.py` | `_ingested_at`, `_source_file` populated | Pending |
| SV-08 | `_is_valid` logic | `src/silver/create_silver_tables.py` | `tests/test_silver_quality.py` | `true` only when zero issues | Pending |
| SV-09 | `_quality_issues` array | `src/silver/01_–05_*.py` | `tests/test_silver_quality.py` | Failed checks listed per row | Pending |
| GD-01 | Gold reads valid Silver only | `src/gold/01_–04_*.sql` | `tests/test_gold_aggregations.py` | Invalid rows excluded from aggregates | Pending |
| NFR-04 | No hardcoded secrets | All `src/**/*.py` | Code review | No tokens/passwords in repo | Pending |
| NFR-06 | Tests for major components | `tests/` | `pytest` | All tests pass | Pending |
| AI-03 | AI session documentation | `ai-prompts/*.md` | Manual review | Each layer session logged | In Progress |
| DC-03 | Requirements analysis | `requirements-analysis.md` | Manual review | This document complete | **Complete** |
| AC-08 | End-to-end pipeline on Databricks | All `src/` layers | Integration test / manual | Bronze → Silver → Gold succeeds | Pending |
| VC-04 | Secrets excluded from Git | `.gitignore` | Manual review | No secrets tracked | Complete |

---

## Document Review (Completeness Check)

| Section | Covered |
|---------|---------|
| 1. Problem statement | ✅ |
| 2. Business objective | ✅ |
| 3. Functional requirements | ✅ |
| 4. Non-functional requirements | ✅ |
| 5. Technical requirements | ✅ |
| 6. Source data requirements | ✅ — includes §6.4 intentional defects and ~700 row target |
| 7. Bronze requirements | ✅ |
| 8. Silver requirements | ✅ |
| 9. Gold requirements | ✅ |
| 10. Dashboard requirements | ✅ |
| 11. Data quality requirements | ✅ — defect-to-check mapping included |
| 12. Testing requirements | ✅ |
| 13. Documentation requirements | ✅ |
| 14. AI/Cursor workflow requirements | ✅ |
| 15. Git/version-control requirements | ✅ |
| 16. Acceptance criteria | ✅ |
| 17. Assumptions | ✅ |
| 18. Edge cases | ✅ |
| 19. Risks | ✅ |
| 20. Clarifications/questions | ✅ |
| Traceability matrix | ✅ — 35 requirements mapped |

**Gaps flagged for resolution during implementation:** Q-01 (reconciling 460 specified instances to ~700 problematic rows), Q-03 (Bronze idempotency), Q-05 (product-level defects).

---

*Last updated: 2026-08-15*
