# Tool Workflow

How this project uses its development toolchain.

## Tools

| Tool | Role |
|------|------|
| **Python / PySpark** | Bronze & Silver pipelines, data generation |
| **SQL** | Gold aggregations, dashboard queries |
| **Databricks** | Execution runtime, Delta Lake storage |
| **Delta Lake** | ACID tables across all layers |
| **Git** | Version control and collaboration |
| **Cursor** | AI-assisted development with documented prompts |

## Development Flow

1. **Plan** — Update `cursor-workflow/task-breakdown.md` before starting a layer.
2. **Implement** — Code in the appropriate `src/<layer>/` directory.
3. **Validate** — Add tests under `tests/` or document manual validation steps.
4. **Document** — Log the Cursor session in `ai-prompts/<layer>.md`.
5. **Review** — Check against `requirements-analysis.md` and data quality strategy.

## Databricks Execution

- Bronze notebooks/scripts run first and write to `bronze.*` tables.
- Silver quality scripts read Bronze, write flagged records to `silver.*`.
- Gold SQL/Python reads Silver, writes to `gold.*`.
- Dashboard queries read from Gold tables only.

## Branching (Recommended)

```
main
 └── feature/bronze-ingest
 └── feature/silver-quality
 └── feature/gold-aggregations
```

Merge each layer only after validation passes.
