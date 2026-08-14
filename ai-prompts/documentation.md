# AI Prompts — Documentation

## Session Log

### 2026-08-15 — Requirements analysis

**Goal:** Create a professional `requirements-analysis.md` covering all 20 sections, intentional DQ defects, ~700 problematic rows, and a traceability matrix.

**Prompt (summary):**

> Analyze assignment requirements and create requirements-analysis.md with problem statement, business/functional/non-functional/technical requirements, layer-specific requirements, DQ defects (50 NULL emails, 10 dup customer_id, order defects, ~700 problematic rows), acceptance criteria, assumptions, edge cases, risks, clarifications, and traceability matrix. No implementation code.

**Outcome:**

- Comprehensive `requirements-analysis.md` (v1.0) with 20 sections and 35-row traceability matrix
- Explicit defect counts documented (460 specified instances; ~700 problematic-row target)
- Open questions flagged for data generation reconciliation

**Files touched:**

- `requirements-analysis.md`
- `ai-prompts/documentation.md`

---

### 2026-08-14 — Project foundation

**Goal:** Create repository structure, documentation, `.gitignore`, and Cursor rules without implementing pipeline code.

**Prompt (summary):**

> Create the complete medallion pipeline project foundation: folder structure, markdown docs, stub Python/SQL files, `.gitignore`, and `.cursor/rules` enforcing bronze/silver/gold principles, logging, type hints, no secret hardcoding, quality flagging, deterministic data generation, and AI prompt documentation. Do NOT implement pipeline logic yet.

**Outcome:**

- Full directory tree created per specification
- Foundation documentation: requirements, design, data model, DQ strategy
- Cursor rules at `.cursor/rules/medallion-pipeline.mdc`
- Stub source files with module docstrings only
- Placeholder CSVs with headers only

**Files touched:**

- Root documentation (`README.md`, `requirements-analysis.md`, `design-notes.md`, etc.)
- `src/` stubs across all layers
- `.gitignore`, `.cursor/rules/medallion-pipeline.mdc`
- `ai-prompts/`, `cursor-workflow/`, `database/`, `tests/`
