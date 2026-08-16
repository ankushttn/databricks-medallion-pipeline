# AI Prompts — Documentation

Evidence log for design, requirements, README, and AI workflow documentation sessions. Each entry documents a real session from the project transcript.

---

## Interaction 1 — Project foundation (2026-08-14)

### 1. Prompt sent

> Create the complete medallion pipeline project foundation: folder structure, markdown docs, stub Python/SQL files, `.gitignore`, and `.cursor/rules` enforcing bronze/silver/gold principles, logging, type hints, no secret hardcoding, quality flagging, deterministic data generation, and AI prompt documentation. Do NOT implement pipeline logic yet.

### 2. Purpose

Establish repository structure and governance before any implementation.

### 3. Cursor response summary

Cursor created full directory tree, foundation documentation stubs, Cursor rules at `.cursor/rules/medallion-pipeline.mdc`, stub source files with module docstrings, placeholder CSVs with headers only, `ai-prompts/` and `cursor-workflow/` folders.

### 4. What was accepted

- Complete folder structure per assignment spec
- Cursor rules enforcing medallion principles
- No pipeline logic in foundation phase
- `.gitignore` covering Python, Databricks, secrets, Delta artifacts

### 5. What was rejected

- Implementing ingestion or quality code in foundation phase
- Skipping AI prompt documentation structure

### 6. What was modified manually

None documented.

### 7. Why the decision was made

Design-first approach prevents architectural drift. Cursor rules persist context across sessions.

### 8. Validation performed

Repository structure inspection.

### 9. Result

Phase 0 complete. `cursor-workflow/project-context.md` initially set to "foundation phase."

---

## Interaction 2 — Requirements analysis (2026-08-15)

### 1. Prompt sent

> Analyze assignment requirements and create requirements-analysis.md with 20 sections, intentional DQ defects, ~700 problematic rows, acceptance criteria, assumptions, edge cases, risks, clarifications, and traceability matrix. No implementation code.

### 2. Purpose

Formal requirements baseline before architecture and implementation.

### 3. Cursor response summary

Created `requirements-analysis.md` v1.0 with 20 sections and 35-row traceability matrix. Documented all §6.4 defect counts (460 specified instances; ~700 problematic-row target).

### 4. What was accepted

- 20-section structure from prompt
- Explicit defect table with Silver dimension mapping
- Traceability matrix linking requirements to deliverables
- Open questions flagged for data generation reconciliation

### 5. What was rejected

- Implementation code in requirements phase
- Vague defect counts without numeric targets

### 6. What was modified manually

`DATA_GENERATION_NOTES.md` updated to point to §6.4 for authoritative defect counts.

### 7. Why the decision was made

Requirements doc is source of truth for all subsequent layers.

### 8. Validation performed

Cross-check against assignment specification.

### 9. Result

Phase 0.5 requirements complete.

---

## Interaction 3 — Architecture and data model design (2026-08-15)

### 1. Prompt sent

> Create architecture and data-model design. Update design-notes.md, data-model.md, cursor-workflow/spec.md, cursor-workflow/task-breakdown.md. Document all layers, data flow, PKs/FKs, types, partitioning, Delta Lake, error handling, logging, DQ reporting. Do not implement pipeline.

### 2. Purpose

Technical design before coding.

### 3. Cursor response summary

Updated four documents to v2.0:

| Document | Key content |
|----------|-------------|
| `design-notes.md` | Mermaid architecture diagram, all 5 layers, Delta/logging/error/DQ design |
| `data-model.md` | Full schemas, ER diagram, PKs/FKs, partitioning |
| `cursor-workflow/spec.md` | Technical spec with deliverables and acceptance criteria |
| `cursor-workflow/task-breakdown.md` | Phase 0.5 complete; Phases 1–5 aligned |

### 4. What was accepted

- Medallion flow: Source → Bronze → Silver → Gold → Dashboard
- `silver.data_quality_summary` reporting table
- Orders partitioned by `order_date` at Bronze and Silver
- INT primary keys, DECIMAL for monetary fields

### 5. What was rejected

- Implementation code in design phase
- Deviating from Bronze/Silver/Gold responsibilities

### 6. What was modified manually

None documented.

### 7. Why the decision was made

Architecture decisions must be documented and approved before implementation begins.

### 8. Validation performed

Internal consistency check across four documents.

### 9. Result

Phase 0.5 architecture complete.

---

## Interaction 4 — Data quality strategy (2026-08-15)

### 1. Prompt sent

> Create data-quality-strategy.md. Define formal DQ framework with 5 dimensions. For every check document check ID, purpose, rule, severity, flagging, metrics, expected intentional failures, test approach. Bad records must NOT be deleted.

### 2. Purpose

Formal Silver quality framework specification (48 checks).

### 3. Cursor response summary

Created `data-quality-strategy.md` v2.0 with complete check catalog, multi-failure model, audit columns, and expected metrics for intentional defects.

### 4. What was accepted

- Five dimensions: completeness, uniqueness, type, referential, business logic
- Flagging via `_quality_issues` array + `_is_valid` boolean
- Percentage passed/failed metrics
- Expected intentional failure counts per check

### 5. What was rejected

- Delete/quarantine bad records from Silver output tables
- Checks without documented IDs and test approaches

### 6. What was modified manually

None documented.

### 7. Why the decision was made

Silver quality is the core differentiator of this assignment — needs formal specification before coding.

### 8. Validation performed

Cross-reference with `requirements-analysis.md` §6.4 and §11.

### 9. Result

DQ strategy complete. Implementation in Silver session.

---

## Interaction 5 — Professional README (2026-08-16)

### 1. Prompt sent

> Create a professional README.md. Include 22 sections: overview, business problem, architecture, tech stack, repo structure, data model, sample data, intentional quality issues, Bronze/Silver/Gold/Dashboard, testing, configuration, local/Databricks execution, troubleshooting, DQ reporting, AI/Cursor workflow, limitations, future improvements. Include Mermaid diagram. Do not claim anything was executed if not verified. Concrete instructions.

### 2. Purpose

Enable another data engineer to understand and reproduce the project.

### 3. Cursor response summary

Rewrote `README.md` with all 22 sections, Mermaid architecture diagram, verification status table at top, concrete local reproduction commands, honest boundaries (local verified; Databricks Delta and Dashboard UI not verified in repo).

### 4. What was accepted

- Verification status table distinguishing local vs Databricks
- Full local reproduction path (generate → validate silver → gold → reconcile → dashboard)
- Links to layer-specific docs and test results
- Mermaid diagram matching `design-notes.md`

### 5. What was rejected

- Claiming Databricks pipeline or dashboard UI was verified
- Vague "run the pipeline" without concrete commands

### 6. What was modified manually

Minor fix: `BRONZE_EXECUTION.md` test path updated to `tests/bronze/` (during same session).

### 7. Why the decision was made

README is the entry point for reviewers and other engineers — must be honest about verification scope.

### 8. Validation performed

Cross-check against actual validation scripts and `tests/TEST_RESULTS.md` (120/120 PASS).

### 9. Result

Professional README complete.

---

## Interaction 6 — AI/Cursor evidence documentation (2026-08-16)

### 1. Prompt sent

> Create complete AI/Cursor evidence documentation. Update all ai-prompts/*.md and cursor-workflow/*.md. For every major interaction: prompt, purpose, response summary, accepted, rejected, manual changes, rationale, validation, result. Do NOT fabricate.

### 2. Purpose

Demonstrate persistent context, iterative development, validation, debugging, and AI suggestion rejection.

### 3. Cursor response summary

Updated all seven `ai-prompts/*.md` files and four `cursor-workflow/*.md` files from agent transcript `50551ecf-026a-4549-8321-588606fc1847.jsonl`.

### 4. What was accepted

- Structured evidence format across all layer docs
- Real prompts and outcomes only
- Cross-references to debugging-notes and test results

### 5. What was rejected

- Fabricated interactions or Cursor responses
- Claiming unverified Databricks execution

### 6. What was modified manually

This file and sibling evidence docs.

### 7. Why the decision was made

Assignment AI workflow requirement — auditable trail of human-AI collaboration.

### 8. Validation performed

Transcript cross-check; validation report cross-check.

### 9. Result

Evidence documentation package complete. Outstanding: `reflection.md`, `final-ai-usage-summary.md`, `candidate-info.md` (separate deliverables).

---

## Documentation artifacts index

| Artifact | Status | Verified locally |
|----------|--------|------------------|
| `requirements-analysis.md` | v1.0 complete | N/A (design doc) |
| `design-notes.md` | v2.0 complete | N/A |
| `data-model.md` | v2.0 complete | N/A |
| `data-quality-strategy.md` | v2.0 complete | N/A |
| `README.md` | 22 sections | Commands verified |
| `ERROR_HANDLING.md` | Complete | Via pytest |
| `tests/README.md` | Complete | 120 tests PASS |
| `tests/TEST_RESULTS.md` | Complete | 2026-08-16 run |
| `debugging-notes.md` | 8 issues logged | Cross-referenced |
| `ai-prompts/*.md` | Complete | This package |
| `reflection.md` | Stub | Pending |
| `final-ai-usage-summary.md` | Stub | Pending |
