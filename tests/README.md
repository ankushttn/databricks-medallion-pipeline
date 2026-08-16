# Test Suite

Automated tests for the Databricks Medallion Pipeline. Tests verify **business outcomes**, not just that code runs.

## Structure

```text
tests/
├── conftest.py                 # Shared Spark fixtures (bronze → silver → gold)
├── helpers/                    # Synthetic data + dimension test utilities
├── data_generation/            # Sample data generation + intentional defects
├── bronze/                     # Bronze config, CSV schema, Spark read
├── silver/                     # Quality dimensions (completeness → business rules)
├── gold/                       # Aggregations, reconciliation, segmentation
├── dashboard/                  # Dashboard SQL queries
├── integration/                # End-to-end pipeline tests
└── common/                     # Config validation and pipeline utilities
```

## Test categories

| Area | Location | What is verified |
|------|----------|------------------|
| Sample data generation | `data_generation/` | Row counts, determinism, defect injection |
| Intentional quality issues | `data_generation/test_intentional_defects.py` | 34-check independent CSV validator |
| Bronze ingestion/schema | `bronze/` | Headers, row counts, Spark schema types, metadata |
| Completeness | `silver/test_silver_completeness.py` | NULL email/FK detection (positive + negative) |
| Uniqueness | `silver/test_silver_uniqueness.py` | Duplicate PK flags all participants |
| Referential integrity | `silver/test_silver_referential_integrity.py` | Orphan FK detection, NULL FK skip |
| Type validation | `silver/test_silver_type_validation.py` | Email format, allowed segments |
| Business rules | `silver/test_silver_business_rules.py` | Amount mismatch, payment date rules |
| Gold aggregations | `gold/test_gold_aggregations.py` | Invalid order exclusion, grain, LTV |
| Segmentation | `gold/test_gold_segmentation.py` | Priority rules, deterministic segment counts |

## Positive vs negative cases

- **Positive:** Valid synthetic rows pass individual dimension checks; clean sample-data subsets pass business rules.
- **Negative:** Injected NULLs, duplicates, orphan FKs, bad emails, and amount mismatches are flagged with correct `issue_code` values and `_is_valid = false`.

## Running tests

```bash
# Full suite (requires Java + PySpark; ~10–15 minutes)
python -m pytest tests/ -v

# Fast unit tests only (no Spark)
python -m pytest tests/ -m unit -v

# By layer
python -m pytest tests/data_generation/ -v
python -m pytest tests/bronze/ -v
python -m pytest tests/silver/ -v
python -m pytest tests/gold/ -v
python -m pytest tests/dashboard/ -v
python -m pytest tests/integration/ -v

# By marker
python -m pytest tests/ -m "silver and not integration" -v
python -m pytest tests/ -m gold -v
```

## Prerequisites

- Python 3.10+
- `pytest` (`pip install pytest`)
- PySpark (same version as Databricks runtime)
- Java 8 or 11 (for local Spark)
- Committed sample CSVs in `data/` (seed 42)

## Deterministic data

Tests use:

1. **Committed `data/*.csv`** — generated with seed 42 for integration tests.
2. **In-memory synthetic rows** — for isolated dimension positive/negative cases.
3. **In-memory generation** — `GenerationConfig(seed=N)` for generation unit tests.

## Error handling

See `ERROR_HANDLING.md` at the repository root for logging standards, exception taxonomy, and input-validation behavior.

## Related validation scripts

These complement pytest but are not substitutes:

| Script | Purpose |
|--------|---------|
| `src/data_generation/validate_sample_data.py` | 34-check CSV validator (also tested in pytest) |
| `src/bronze/validate_bronze_static.py` | Static Bronze source checks |
| `src/silver/validate_silver_local.py` | Silver quality report |
| `src/gold/reconcile_gold_local.py` | Gold reconciliation report |
| `src/dashboard/validate_dashboard_local.py` | Dashboard query validation |

## Latest results

See `tests/TEST_RESULTS.md` for the most recent full-suite run.
