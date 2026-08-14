# Databricks Medallion Pipeline — E-Commerce

A Bronze → Silver → Gold data engineering project for e-commerce analytics, built with **Python**, **PySpark**, **SQL**, **Databricks**, and **Delta Lake**.

## Architecture

```
Source CSVs → Bronze (raw) → Silver (validated + flagged) → Gold (aggregations) → Dashboard
```

| Layer  | Purpose |
|--------|---------|
| Bronze | Ingest raw data unchanged into Delta tables |
| Silver | Apply data quality checks; flag — never silently drop bad records |
| Gold   | Business-ready metrics and aggregations |

## Repository Layout

| Path | Description |
|------|-------------|
| `src/` | Pipeline source code by layer |
| `data/` | Sample CSV source files |
| `database/` | Schema definitions and setup notes |
| `tests/` | Unit and integration tests |
| `ai-prompts/` | Cursor / AI interaction log |
| `cursor-workflow/` | Project spec, context, and task breakdown |

## Documentation

- [Requirements Analysis](requirements-analysis.md)
- [Design Notes](design-notes.md)
- [Data Model](data-model.md)
- [Data Quality Strategy](data-quality-strategy.md)
- [Tool Workflow](tool-workflow.md)

## Status

**Foundation phase** — project structure and documentation are in place. Pipeline implementation has not started.

## Prerequisites

- Databricks workspace with Unity Catalog (or Hive metastore)
- Python 3.10+
- Databricks CLI (optional, for bundle deploy)

## Getting Started

1. Review `cursor-workflow/spec.md` and `design-notes.md`.
2. Generate sample data via `src/data_generation/` (when implemented).
3. Run Bronze → Silver → Gold pipelines in order.
4. Execute dashboard queries from `src/dashboard/`.

> **Note:** Do not change the medallion architecture without team approval. See `.cursor/rules/medallion-pipeline.mdc`.
