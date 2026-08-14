# Task Breakdown

## Phase 0 — Foundation ✅

- [x] Repository structure
- [x] Documentation (requirements, design, data model, DQ strategy)
- [x] `.gitignore`
- [x] Cursor rules (`.cursor/rules/medallion-pipeline.mdc`)
- [x] Stub source files
- [x] AI prompt templates

## Phase 1 — Data Generation

- [ ] Implement `generate_sample_data.py`
- [ ] Populate `data/customers.csv`, `data/orders.csv`, `data/products.csv`
- [ ] Document bad record injection in `DATA_GENERATION_NOTES.md`
- [ ] Add tests

## Phase 2 — Bronze Layer

- [ ] Implement customer ingestion
- [ ] Implement order ingestion
- [ ] Implement product ingestion
- [ ] Implement `ingest_all.py` orchestrator
- [ ] Add ingestion metadata (`_ingested_at`, `_source_file`)
- [ ] Add tests

## Phase 3 — Silver Layer

- [ ] Completeness checks (`01_quality_completeness.py`)
- [ ] Uniqueness checks (`02_quality_uniqueness.py`)
- [ ] Type validation (`03_quality_type_validation.py`)
- [ ] Referential integrity (`04_quality_referential_integrity.py`)
- [ ] Business logic (`05_quality_business_logic.py`)
- [ ] `create_silver_tables.py` orchestrator
- [ ] Quality metrics reporting
- [ ] Add tests

## Phase 4 — Gold Layer

- [ ] Sales by product SQL
- [ ] Revenue by customer SQL
- [ ] Daily/weekly trends SQL
- [ ] Customer segmentation SQL
- [ ] `create_gold_tables.py` orchestrator
- [ ] Add tests

## Phase 5 — Dashboard & Wrap-up

- [ ] Dashboard queries
- [ ] Dashboard setup guide
- [ ] Complete `reflection.md`
- [ ] Complete `final-ai-usage-summary.md`
- [ ] Final review against `requirements-analysis.md`
