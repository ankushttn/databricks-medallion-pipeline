# Error Handling Strategy

This document describes how the medallion pipeline handles failures, logs operational events, and validates inputs across Bronze, Silver, Gold, and data-generation layers.

## Principles

1. **Fail fast** — invalid configuration, missing source files, and schema mismatches are detected before expensive Spark work where possible.
2. **Never swallow errors silently** — no bare `except:` or empty `except` blocks. Every caught exception is logged with context (`exc_info=True` where appropriate) and either re-raised or converted to a domain-specific error.
3. **Domain-specific exceptions** — each layer raises typed errors (`BronzeIngestionError`, `SilverValidationError`, `GoldBuildError`, `ConfigurationError`) so callers can distinguish failure modes.
4. **Quality vs pipeline failures** — Silver intentionally flags bad records (`_is_valid = false`) rather than raising; pipeline exceptions indicate unreadable inputs or infrastructure failures.
5. **Structured logging** — pipeline start/end, source paths, row counts, validation results, table creation, and quality failures are logged at INFO/WARNING/ERROR.

## Exception taxonomy

| Layer | Exception | When raised |
|-------|-----------|-------------|
| Common | `ConfigurationError` | Invalid write mode, missing local source directory, empty schema name |
| Bronze | `BronzeSourceFileError` | Missing CSV, empty file (no header) |
| Bronze | `BronzeIngestionError` | Header mismatch, row-count mismatch, malformed CSV, Delta write failure |
| Silver | `SilverValidationError` | Bronze table unreadable, row-count parity violation, Silver write failure |
| Gold | `GoldBuildError` | Missing SQL script, Gold SQL execution failure |
| Data generation | `DataGenerationValidationError` | Defect counts or row counts do not match specification |

## Input validation by scenario

| Scenario | Detection point | Behavior |
|----------|-----------------|----------|
| Missing files | `verify_source_file_exists()` (Bronze), `run_validation()` (sample data) | `BronzeSourceFileError` or failed validation report |
| Malformed CSV | Spark `FAILFAST` read + `AnalysisException` / `Py4JJavaError` | `BronzeIngestionError` with source path in message |
| Schema mismatch | `validate_csv_header()` before Spark read | `BronzeIngestionError` with expected vs actual columns |
| Empty datasets | `count_csv_data_rows()` + Spark `df.count()` | WARNING logged; ingest allowed if counts match (0 rows) |
| Duplicate data | Silver uniqueness dimension | Flagged in `_quality_issues`; not raised |
| Invalid foreign keys | Silver referential dimension | Flagged; NULL FKs skip referential check |
| Unexpected nulls | Silver completeness dimension | Flagged with `completeness:*` issue codes |
| Invalid dates / numerics | Silver type + business dimensions | Flagged with `type:*` or `business:*` issue codes |
| Missing upstream tables | Silver/Gold `spark.table()` | `AnalysisException` → layer-specific error |

## Logging events

### Pipeline lifecycle

```
Pipeline START layer=bronze run_id=... source_base_path=...
Pipeline END   layer=bronze run_id=... status=SUCCESS elapsed_s=12.34
```

Silver uses `run_id` throughout quality metrics. Gold and Bronze log start/end via `common.pipeline_utils`.

### Bronze ingestion

| Event | Level | Example |
|-------|-------|---------|
| Ingestion start | INFO | `Starting Bronze ingestion entity=orders source=... target=...` |
| Row count | INFO | `rows_read=100020 rows_written=100020` |
| Empty source | WARNING | `Bronze source has zero data rows: entity=...` |
| Header mismatch | ERROR | `CSV header mismatch for ...` |
| Ingestion failure | ERROR | `Bronze ingestion FAILED entity=... error=...` |

### Silver quality

| Event | Level | Example |
|-------|-------|---------|
| Pipeline start | INFO | `Starting Silver pipeline run_id=...` |
| Entity processing | INFO | `Processing Silver entity=orders bronze=... silver=...` |
| Row parity | INFO | `Row count parity OK entity=orders bronze=... silver=...` |
| Quality failures | INFO | `DQ check failure entity=orders issue_code=... count=...` |
| Pipeline end | INFO | `Silver pipeline completed successfully run_id=...` |

### Gold build

| Event | Level | Example |
|-------|-------|---------|
| Script execution | INFO | `Executing Gold script 01_sales_by_product.sql` |
| Table created | INFO | `Table created: table=gold.sales_by_product row_count=500` |
| Empty Gold table | WARNING | `Table created with zero rows: table=...` |
| Validation | INFO/ERROR | `Validation PASS/FAIL layer=gold check=...` |

## Configuration validation

All three layer configs validate at load time:

- `write_mode` ∈ `{overwrite, append}`
- `bronze_schema`, `silver_schema`, `gold_schema` non-empty
- Local `source_base_path` exists (Bronze only; DBFS paths skipped)

Invalid configuration raises `ConfigurationError` before Spark session work begins.

## Python pattern (required)

```python
logger = logging.getLogger(__name__)

try:
    df = read_bronze_csv(spark, path, spec)
except AnalysisException as exc:
    logger.error("Failed to read CSV: %s", path, exc_info=True)
    raise BronzeIngestionError(f"Malformed input for {path}: {exc}") from exc
```

**Do not:**

```python
try:
    df = spark.read.csv(path)
except Exception:
    pass  # NEVER
```

## Local validation scripts

| Script | On failure |
|--------|------------|
| `validate_bronze_static.py` | Exit code 1, aggregated error list |
| `validate_silver_local.py` | Report + exit code 1 |
| `reconcile_gold_local.py` | Report + exit code 1 |
| `validate_dashboard_local.py` | Per-query failure logged; report + exit code 1 |

## Related documentation

- `design-notes.md` §9–10 — original design principles
- `src/bronze/BRONZE_EXECUTION.md` — Bronze runbook
- `src/silver/SILVER_ARCHITECTURE.md` — quality framework
- `src/gold/GOLD_ARCHITECTURE.md` — Gold business rules
- `tests/` — automated validation of defect detection and pipeline behavior
