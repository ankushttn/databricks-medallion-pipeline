# AI Prompts — Gold Layer

Evidence log for Cursor interactions on Gold analytics. Each entry documents a real session from the project transcript.

---

## Interaction 1 — Gold layer implementation (2026-08-16)

### 1. Prompt sent

> Implement the Gold layer.
>
> Read the existing architecture and Silver implementation first.
>
> Create:
> - `src/gold/01_sales_by_product.sql`
> - `src/gold/02_revenue_by_customer.sql`
> - `src/gold/03_daily_weekly_trends.sql`
> - `src/gold/04_customer_segmentation.sql`
> - `src/gold/create_gold_tables.py`
>
> Implement aggregations for sales by product, revenue by customer, daily/weekly trends, and customer segmentation (High-Value, Repeat, One-Time, Inactive).
>
> Use valid Silver data only. Document assumptions.

### 2. Purpose

Produce four business-ready Gold tables from `_is_valid = TRUE` Silver rows for dashboard consumption.

### 3. Cursor response summary

Cursor implemented four Gold SQL scripts, `gold_engine.py` orchestrator, `validate_gold_local.py`, `GOLD_ARCHITECTURE.md`, and `tests/test_gold_aggregations.py`.

Key design decisions communicated:
- `WHERE _is_valid = TRUE` on all inputs
- `COUNT(DISTINCT order_id)` to prevent double counting
- Segmentation priority: Inactive → High-Value (≥ $2,500) → Repeat (2+ orders) → One-Time
- 597 orphan valid orders (valid order + invalid customer) excluded from `revenue_by_customer` by design

Validation run `gold-validation-001`: 15/15 validation queries PASS, 6/6 unit tests PASS.

### 4. What was accepted

- Valid-Silver-only filter
- `COUNT(DISTINCT order_id)` for order metrics
- Mutually exclusive segmentation with documented priority
- Orphan order exclusion from customer Gold (documented, not treated as bug)
- Local validation without Delta

### 5. What was rejected

- Requiring all four segment rows when Inactive count is zero on sample data
- Including invalid Silver rows in aggregations
- Treating orphan orders as Gold logic errors

### 6. What was modified manually

`validations.py` updated during session: validation changed from "must have 4 segments" to "at most 4 allowed segment types" after discovering Inactive is empty on seed-42 data.

### 7. Why the decision was made

All 9,940 valid customers have at least one valid order — Inactive segment is legitimately empty. Validation rules must reflect business logic, not force artificial segment rows.

### 8. Validation performed

```bash
python src/gold/validate_gold_local.py --data-dir data --output-dir data
python -m pytest tests/test_gold_aggregations.py -v
```

**Result:** 6/6 tests PASS. Report: `data/GOLD_VALIDATION_REPORT.md`.

### 9. Result

Gold SQL and orchestrator implemented. Senior reconciliation requested in follow-up session before marking complete.

---

## Interaction 2 — Senior-level Gold validation (2026-08-16)

### 1. Prompt sent

> Perform a senior-level validation of the Gold layer. Do not assume the aggregation logic is correct.
>
> For each Gold table independently calculate expected results using an alternative method.
>
> Validate counts, sums, averages, joins, duplicate handling, null handling, revenue calculations, segmentation logic.
>
> Create reconciliation queries or tests.
>
> For at least 5 representative products and 5 representative customers reconcile source → Silver → Gold.
>
> If discrepancies occur: identify root cause, fix implementation, rerun validation, document in debugging-notes.md.
>
> Do not mark Gold complete until reconciliation passes.

### 2. Purpose

Independent verification that Gold SQL is correct — not just that validation scripts pass.

### 3. Cursor response summary

Cursor built `reconciliation.py` (alternate-path recomputation), `reconcile_gold_local.py` (CLI + reports), and `tests/test_gold_reconciliation.py` (11 tests).

Initial reconciliation reported 1,824 daily-trend mismatches. Cursor diagnosed this as a **reconciliation comparison bug** (Decimal/float + `collect()` equality), not Gold SQL error. Fixed by rewriting `compare_dataframes()` to use Spark joins with explicit decimal casting.

JSON export crashed with `Decimal is not JSON serializable` — fixed with `default=str` in `json.dumps`.

Final result: all 11 reconciliation checks PASS; 5 product traces (83, 121, 197, 236, 469) and 5 customer traces (1, 10, 866, 1966, 264) PASS.

### 4. What was accepted

- Independent alternate-path calculations (deduped order facts, semi-joins, Python `classify_segment()`)
- Fixing reconciliation tooling when Gold SQL was already correct
- Documenting orphan orders (597) and revenue_by_customer vs trends order-count delta
- Entity traces for invalid Silver customers correctly absent from Gold

### 5. What was rejected

- Changing Gold SQL to fix reconciliation false failures
- Using Python `collect()` + float equality for monetary comparisons
- Marking Gold complete while reconciliation failed

### 6. What was modified manually

`reconciliation.py` — multiple iterations:
1. Date key normalization attempt
2. Full rewrite to Spark join-based comparison
3. Explicit `decimal(14,2)` casting on expected aggregates

`reconcile_gold_local.py` — added `default=str` for JSON export.

### 7. Why the decision was made

Senior validation must use a genuinely independent code path. When alternate path disagrees, investigate whether Gold or the reconciler is wrong — here, the reconciler was wrong.

### 8. Validation performed

```bash
python -m pytest tests/test_gold_reconciliation.py tests/test_gold_aggregations.py -v
python src/gold/reconcile_gold_local.py --data-dir data --output-dir data
```

**Result:** 17/17 Gold tests PASS (~5m 22s). Reports: `data/GOLD_RECONCILIATION_REPORT.md`, `.json`.

### 9. Result

Gold layer reconciliation-complete. Phase 4 marked done in `task-breakdown.md` (except `database/schema.sql` Gold DDL).

---

## Reconciliation summary (verified)

| Check | Method | Result |
|-------|--------|--------|
| sales_by_product | Deduped valid orders + product semi-join | PASS (500 keys) |
| revenue_by_customer | Valid customer semi-join + lifetime sum | PASS (9,940 keys) |
| daily/weekly trends | Date/week grain re-aggregation | PASS (912 daily + 132 weekly) |
| customer_segmentation | Python `classify_segment()` loop | PASS (High-Value 9,652 / Repeat 284 / One-Time 4) |
| Duplicate/null exclusion | Invalid order revenue delta | PASS |
| Orphan orders | 597 valid orders with invalid customers | Documented, excluded from customer Gold |
