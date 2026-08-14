# Project Context

## What This Project Is

An e-commerce **Medallion Architecture** data pipeline assignment using Databricks, PySpark, SQL, and Delta Lake.

## Domain

- **Customers** place **orders** for **products**.
- Analytics focus: sales, revenue, trends, and customer segmentation.

## Key Constraints

1. Bronze = raw, unchanged data
2. Silver = validation + quality flags (never delete bad records)
3. Gold = business aggregations
4. Deterministic sample data with intentional quality issues
5. All major AI sessions documented in `ai-prompts/`

## Current Phase

**Foundation complete.** Pipeline implementation not started.

## Reference Docs

| Document | Purpose |
|----------|---------|
| `requirements-analysis.md` | Assignment requirements |
| `design-notes.md` | Architecture decisions |
| `data-model.md` | Entities and relationships |
| `data-quality-strategy.md` | Silver quality approach |
| `cursor-workflow/spec.md` | Detailed specification |
| `cursor-workflow/task-breakdown.md` | Implementation task list |
