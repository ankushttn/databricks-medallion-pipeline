# AI Prompts — Data Generation

## Session Log

### 2026-08-15 — Implement sample data generation

**Goal:** Implement `generate_sample_data.py` with deterministic realistic data and exact intentional defects.

**Outcome:**

- `generate_sample_data.py` — modular generators, defect injection, validation, CLI (`--output-dir`, `--seed`)
- CSVs generated: 10,010 customers, 500 products, 100,020 orders
- All mandatory defect counts verified; no uncontrolled quality issues
- `tests/test_data_generation.py` — 4 tests passing
- `DATA_GENERATION_NOTES.md` updated

**Files touched:**

- `src/data_generation/generate_sample_data.py`
- `src/data_generation/DATA_GENERATION_NOTES.md`
- `data/customers.csv`, `data/orders.csv`, `data/products.csv`
- `tests/test_data_generation.py`
- `cursor-workflow/task-breakdown.md`
