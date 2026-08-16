# AI Prompts — Bronze Layer

Evidence log for Cursor interactions on Bronze ingestion. Each entry documents a real session from the project transcript.

---

## Interaction 1 — Bronze ingestion implementation (2026-08-16)

### 1. Prompt sent

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

### 2. Purpose

Land raw CSV data into Delta Bronze tables with audit metadata, ready for Silver quality checks.

### 3. Cursor response summary

Cursor implemented a modular Bronze package:

| Module | Purpose |
|--------|---------|
| `config.py` | `BronzeConfig`, entity specs, env/CLI configuration |
| `schemas.py` | Explicit Spark `StructType` schemas per entity |
| `ingest_utils.py` | Core ingest logic, logging, error handling |
| `validate_bronze_static.py` | Pre-flight CSV validation (no Spark) |
| `BRONZE_EXECUTION.md` | Databricks runbook |
| `01_–03_*.py`, `ingest_all.py` | Thin CLI entry points |

Static validation PASSED (10,010 / 500 / 100,020 rows). `pytest tests/test_bronze_ingest.py`: 10/10 PASSED.

### 4. What was accepted

| Decision | Rationale |
|----------|-----------|
| Shared `BronzeConfig` via env + CLI | Avoids duplicated paths; supports local `data/` and `dbfs:/` |
| Explicit Spark schemas with `nullValue=""` | Empty CSV fields become SQL NULL without business cleansing |
| `FAILFAST` CSV read mode | Malformed values fail loudly with useful errors |
| `overwrite` Delta write mode | Idempotent dev runs per design-notes Q-03 |
| Metadata via `current_timestamp()` + `lit(source_path)` | Adds `_ingested_at`, `_source_file` only |
| Orders partitioned by `order_date` | Per data-model.md §4.3 |
| Pre-read CSV header/row validation | Catches issues before Spark job on local paths |
| Thin entity scripts | Single `run_ingestion(spec)` pattern reduces duplication |
| `ingest_all` order: customers → products → orders | Dependency-neutral at Bronze; matches orchestrator spec |

### 5. What was rejected

| Rejected | Why |
|----------|-----|
| Read all columns as STRING | data-model.md specifies typed Bronze columns |
| Coalesce null FKs to sentinel values | Violates raw-ingest principle |
| Deduplicate on ingest | Explicitly forbidden |
| Hardcoded `/Workspace/Repos/...` paths | Environment-specific; use config instead |
| Append-only writes | Overwrite chosen for idempotent re-runs |
| Skip row-count verification | Required for auditability |

### 6. What was modified manually

No manual code changes outside Cursor session. User did not override architectural decisions.

### 7. Why the decision was made

Bronze must preserve source fidelity. Typed schemas + metadata columns satisfy audit requirements while keeping Silver as the sole quality layer.

### 8. Validation performed

```bash
python src/bronze/validate_bronze_static.py --source-base-path data
python -m pytest tests/test_bronze_ingest.py -v
```

**Result:** Static validation PASSED. 10/10 unit tests PASSED. Full Delta write requires Databricks cluster (documented in `BRONZE_EXECUTION.md`, not verified in repo).

### 9. Result

Phase 2 Bronze implementation complete. Tests later reorganized to `tests/bronze/` during automated testing strategy session (120 tests total at project end).

---

## Iterative refinement note (production-readiness, 2026-08-16)

Bronze layer was later hardened without changing ingest semantics:

- Narrowed `except Exception` to specific types in `ingest_utils.py`
- Added empty-dataset WARNING and elapsed-time logging
- Config fail-fast validation via `src/common/pipeline_utils.py`
- Header validation no longer silently skips missing files

See `ai-prompts/debugging.md` — Production-readiness session.
