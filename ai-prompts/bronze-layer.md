# AI Prompts — Bronze Layer

## Session Log

### 2026-08-16 — Bronze ingestion implementation

#### Prompt

> Implement the Bronze ingestion layer.
>
> Inspect requirements-analysis.md, design-notes.md, data-model.md, data-quality-strategy.md, generated source files, and Cursor rules.
>
> Implement:
> - `src/bronze/01_ingest_customers.py`
> - `src/bronze/02_ingest_orders.py`
> - `src/bronze/03_ingest_products.py`
> - `src/bronze/ingest_all.py`
>
> Requirements: read CSVs; support Databricks/DBFS paths via configuration; create Bronze Delta tables; preserve source data; explicit schemas; log ingestion timestamp, source file, row count, success/failure; handle missing/malformed input; fail with useful errors; reusable config (no hardcoded paths).
>
> Bronze must NOT: deduplicate, remove nulls, fix FKs, change business values, or perform Silver transforms.
>
> Add ingestion metadata without modifying business columns. Perform local/static validation and document Databricks execution.

#### Response Summary

Implemented a modular Bronze package under `src/bronze/`:

| Module | Purpose |
|--------|---------|
| `config.py` | `BronzeConfig`, entity specs, env/CLI configuration |
| `schemas.py` | Explicit Spark `StructType` schemas per entity |
| `ingest_utils.py` | Core ingest logic, logging, error handling |
| `validate_bronze_static.py` | Pre-flight CSV validation (no Spark) |
| `BRONZE_EXECUTION.md` | Databricks runbook |
| `01_–03_*.py`, `ingest_all.py` | Thin CLI entry points |

**Validation results:**
- Static validation: **PASSED** (customers 10,010 / products 500 / orders 100,020 rows)
- `pytest tests/test_bronze_ingest.py`: **10/10 PASSED**
- Full Delta write: requires Databricks cluster (documented in `BRONZE_EXECUTION.md`)

#### Accepted Decisions

| Decision | Rationale |
|----------|-----------|
| **Shared `BronzeConfig` via env + CLI** | Avoids duplicated paths; supports local `data/` and `dbfs:/` |
| **Explicit Spark schemas with `nullValue=""`** | Empty CSV fields become SQL NULL without business cleansing |
| **`FAILFAST` CSV read mode** | Malformed values fail loudly with useful errors |
| **`overwrite` Delta write mode** | Idempotent dev runs per design-notes Q-03 resolution |
| **Metadata via `current_timestamp()` + `lit(source_path)`** | Adds `_ingested_at`, `_source_file` only |
| **Orders partitioned by `order_date`** | Per data-model.md §4.3 |
| **Pre-read CSV header/row validation** | Catches issues before Spark job on local paths |
| **Thin entity scripts** | Single `run_ingestion(spec)` pattern reduces duplication |
| **`ingest_all` order: customers → products → orders** | Dependency-neutral at Bronze; matches orchestrator spec |

#### Rejected Decisions

| Rejected | Why |
|----------|-----|
| **Read all columns as STRING** | data-model.md specifies typed Bronze columns; Silver handles validation |
| **Coalesce null FKs to sentinel values** | Violates raw-ingest principle |
| **Deduplicate on ingest** | Explicitly forbidden |
| **Hardcoded `/Workspace/Repos/...` paths** | Environment-specific; use config instead |
| **Append-only writes** | Overwrite chosen for idempotent re-runs |
| **Skip row-count verification** | Required for auditability and catching partial reads |

#### Modifications

| File | Change |
|------|--------|
| `src/bronze/config.py` | **Created** — configuration and entity specs |
| `src/bronze/schemas.py` | **Created** — Spark schemas |
| `src/bronze/ingest_utils.py` | **Created** — core ingestion engine |
| `src/bronze/validate_bronze_static.py` | **Created** — static pre-flight validator |
| `src/bronze/BRONZE_EXECUTION.md` | **Created** — Databricks execution guide |
| `src/bronze/01_ingest_customers.py` | **Implemented** |
| `src/bronze/02_ingest_orders.py` | **Implemented** |
| `src/bronze/03_ingest_products.py` | **Implemented** |
| `src/bronze/ingest_all.py` | **Implemented** |
| `tests/test_bronze_ingest.py` | **Created** — 10 unit/static tests |
| `database/schema.sql` | **Updated** — Bronze table notes |
| `cursor-workflow/task-breakdown.md` | Phase 2 marked complete |

---

### [Pending] Silver quality pipeline

**Goal:** Implement five quality dimensions with flagging (no record deletion).

**Prompt:** _To be added when implementation starts._

**Outcome:** _Pending._

**Files touched:** _Pending._
