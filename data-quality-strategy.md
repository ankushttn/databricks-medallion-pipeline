# Data Quality Strategy

## Principles

1. **Detect, don't delete** — Silver never removes intentionally bad source records.
2. **Flag and measure** — Every check produces countable, auditable outcomes.
3. **Layer separation** — Quality logic lives only in Silver; Gold reads valid (or flagged) Silver data.

## Five Quality Dimensions

| # | Dimension | Script | Checks (planned) |
|---|-----------|--------|------------------|
| 1 | Completeness | `01_quality_completeness.py` | Non-null PKs, required fields |
| 2 | Uniqueness | `02_quality_uniqueness.py` | Duplicate PK detection |
| 3 | Type validation | `03_quality_type_validation.py` | Numeric, date, email format |
| 4 | Referential integrity | `04_quality_referential_integrity.py` | FK resolution |
| 5 | Business logic | `05_quality_business_logic.py` | Positive qty, amount = qty × price |

## Flagging Pattern

```text
_is_valid          : boolean   — true when zero quality issues
_quality_issues    : array     — e.g. ["completeness:email_null", "business:negative_quantity"]
_validated_at      : timestamp — last validation run
```

## Metrics & Reporting

After each Silver run, log or persist:

| Metric | Description |
|--------|-------------|
| `total_records` | Rows processed |
| `valid_records` | Rows where `_is_valid = true` |
| `invalid_records` | Rows where `_is_valid = false` |
| `issue_breakdown` | Count per issue type |

## Gold Consumption Rule

Gold aggregations should filter to `_is_valid = true` unless explicitly analyzing data quality.

## Sample Data

Intentionally inject bad records during generation (documented in `DATA_GENERATION_NOTES.md`) to prove quality checks work.
