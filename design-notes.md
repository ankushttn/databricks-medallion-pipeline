# Design Notes

## Architecture Decision: Medallion (Bronze → Silver → Gold)

### Bronze — Raw Landing Zone

- **Principle:** Store data as-ingested; no business logic.
- **Format:** Delta Lake tables under `bronze` schema/catalog.
- **Tables:** `bronze.customers`, `bronze.orders`, `bronze.products`
- **Metadata:** Add ingestion timestamp and source file name only.

### Silver — Curated & Validated

- **Principle:** Cleanse and validate; never silently discard bad records.
- **Pattern:** Add quality flag columns (e.g., `_is_valid`, `_quality_issues`).
- **Tables:** `silver.customers`, `silver.orders`, `silver.products`
- **Quarantine:** Optional `silver.*_quarantine` views for invalid rows.

### Gold — Business Analytics

- **Principle:** Denormalized, aggregation-ready datasets for BI.
- **Tables:** Created by SQL scripts and `create_gold_tables.py`.
- **Consumers:** Dashboard, ad-hoc SQL, downstream ML (future).

## Naming Conventions

| Item | Convention | Example |
|------|------------|---------|
| Bronze tables | `bronze.<entity>` | `bronze.orders` |
| Silver tables | `silver.<entity>` | `silver.orders` |
| Gold tables | `gold.<metric>` | `gold.sales_by_product` |
| Quality flags | `_` prefix | `_is_valid`, `_quality_issues` |
| Scripts | Numbered prefix | `01_ingest_customers.py` |

## Technology Choices

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Storage | Delta Lake | ACID, time travel, Databricks native |
| Bronze/Silver | PySpark | Flexible validation logic |
| Gold | SQL + PySpark orchestrator | Readable analytics SQL |
| Sample data | Python with `random.seed()` | Reproducible test data |

## Change Control

> Architectural changes require explicit approval. Document rationale in this file before implementing.
