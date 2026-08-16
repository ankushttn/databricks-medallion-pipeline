# Project Context

**Last updated:** 2026-08-16  
**Status:** Implementation complete locally — Databricks deployment not verified in this repo

---

## What This Project Is

An e-commerce **Medallion Architecture** data pipeline assignment using Databricks, PySpark, SQL, and Delta Lake. Cursor AI assisted development with all major sessions documented in `ai-prompts/`.

## Domain

- **Customers** place **orders** for **products**.
- Analytics focus: sales, revenue, trends, and customer segmentation.

## Architecture

```text
Source CSV  →  Bronze  →  Silver  →  Gold  →  Databricks SQL Dashboard
```

See `design-notes.md` for the full Mermaid diagram.

## Key Constraints

1. Bronze = raw, unchanged data
2. Silver = validation + quality flags (never delete bad records)
3. Gold = business aggregations from valid Silver only
4. Deterministic sample data (seed 42) with intentional quality issues
5. All major AI sessions documented in `ai-prompts/`

## Current Implementation State

| Layer | Status | Local validation |
|-------|--------|------------------|
| Data generation | Complete | `validate_sample_data.py` — 34 checks PASS |
| Bronze | Complete | `validate_bronze_static.py` — PASS |
| Silver | Complete | `validate_silver_local.py` — all mandatory defects detected |
| Gold | Complete | `validate_gold_local.py` + `reconcile_gold_local.py` — all PASS |
| Dashboard SQL | Complete | `validate_dashboard_local.py` — 12/12 queries PASS |
| Databricks Delta execution | Documented | **Not verified** in this repo |
| Databricks SQL Dashboard UI | Documented | **Not verified** in this repo |

## Sample Data (seed 42)

| Entity | Rows | Notes |
|--------|------|-------|
| customers | 10,010 | +10 duplicate rows |
| products | 500 | No intentional defects |
| orders | 100,020 | +20 duplicate rows |

**Intentional defects:** 50 null emails; 100 null customer_id; 200 null product_id; 50 invalid customer FKs; 30 invalid product FKs; 10 duplicate customer rows (20 flagged); 20 duplicate order rows (40 flagged); ~420 invalid orders in Silver.

## Gold Metrics (verified locally)

| Metric | Value |
|--------|-------|
| Valid orders in trends | 99,600 |
| Valid customers in Gold | 9,940 |
| Orphan valid orders (excluded from customer Gold) | 597 |
| Segments | High-Value 9,652 / Repeat 284 / One-Time 4 (Inactive absent) |

## Testing

**120/120 pytest tests PASS** (~8m 48s, Windows, Python 3.10.9). See `tests/TEST_RESULTS.md`.

## AI/Cursor Workflow

| Resource | Purpose |
|----------|---------|
| `ai-prompts/*.md` | Per-layer evidence logs (prompt, accepted/rejected, validation) |
| `cursor-workflow/spec.md` | Technical specification |
| `cursor-workflow/task-breakdown.md` | Phase checklist |
| `cursor-workflow/cursor-rules-or-instructions.md` | How to use Cursor rules |
| `debugging-notes.md` | Issue resolutions |
| Agent transcript | `50551ecf-026a-4549-8321-588606fc1847` |

## Outstanding Items

- [ ] `database/schema.sql` — Silver/Gold DDL stubs incomplete
- [ ] End-to-end validation on Databricks cluster
- [ ] Databricks SQL Dashboard UI build and verify
- [ ] `reflection.md`, `final-ai-usage-summary.md`, `candidate-info.md`

## Reference Docs

| Document | Purpose |
|----------|---------|
| `requirements-analysis.md` | Assignment requirements |
| `design-notes.md` | Architecture decisions |
| `data-model.md` | Entities and relationships |
| `data-quality-strategy.md` | Silver quality approach |
| `ERROR_HANDLING.md` | Logging and exception strategy |
| `README.md` | Full project guide (22 sections) |
| `cursor-workflow/spec.md` | Detailed specification |
| `cursor-workflow/task-breakdown.md` | Implementation task list |
