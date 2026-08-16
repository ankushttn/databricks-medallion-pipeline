# Cursor Rules & Instructions

**Last updated:** 2026-08-16

## Active Rules

Project rules live in `.cursor/rules/medallion-pipeline.mdc` and apply to every Cursor session.

## Quick Reference

| Rule | Summary |
|------|---------|
| Python quality | Type hints, docstrings, logging (not print) |
| Exceptions | Never silently swallow |
| Secrets | Never hardcode |
| Bronze | Raw, unchanged |
| Silver | Validate and flag; never delete bad records |
| Gold | Business aggregations from valid Silver only |
| SQL | Readable and formatted |
| Tests | Required for major implementations |
| AI docs | Log sessions in `ai-prompts/` with evidence format |
| Reuse | Inspect existing code before adding utilities |

## Before Starting a Task

1. Read `cursor-workflow/project-context.md` — current implementation state
2. Check `cursor-workflow/task-breakdown.md` for open items
3. Review relevant layer file in `ai-prompts/`
4. Follow `.cursor/rules/medallion-pipeline.mdc`

## AI Evidence Documentation Format

For every major Cursor interaction, document in the appropriate `ai-prompts/<layer>.md`:

1. **Prompt sent** — actual user prompt (or summary if very long)
2. **Purpose** — why the session happened
3. **Cursor response summary** — what Cursor proposed/built
4. **What was accepted** — decisions kept
5. **What was rejected** — incorrect or inappropriate AI suggestions
6. **What was modified manually** — human or follow-up fixes
7. **Why the decision was made** — rationale
8. **Validation performed** — commands run, reports produced
9. **Result** — outcome and artifacts

**Rules:**
- Do NOT fabricate Cursor responses
- Only document interactions that actually occurred
- Cross-reference `debugging-notes.md` for failures and fixes
- Distinguish **verified locally** vs **documented for Databricks only**

## Demonstrated Workflow Patterns

This project evidence demonstrates:

| Pattern | Example |
|---------|---------|
| Persistent project context | `project-context.md`, Cursor rules, design docs read before each layer |
| Iterative development | Gold reconciliation: implement → fail → diagnose → fix reconciler → pass |
| Validation | Layer-specific `validate_*_local.py` scripts + pytest (120 tests) |
| Debugging | 8 entries in `debugging-notes.md` |
| Rejection of incorrect AI suggestions | Did not change Gold SQL when reconciliation had Decimal/float bug |
| Refinement of AI-generated code | `reconciliation.py` rewritten 3 times; production-readiness hardening |

## Architecture Change Policy

Do not modify Bronze/Silver/Gold responsibilities without:

1. Documenting rationale in `design-notes.md`
2. Obtaining explicit approval
3. Updating `ai-prompts/` evidence log

## Session Workflow (observed across project)

```text
1. User prompt with constraints ("do not implement yet", "do not delete bad records")
2. Cursor reads existing docs + code (requirements, design, prior layer)
3. Cursor implements with tests and validation scripts
4. User requests senior validation / testing / production review
5. Cursor runs validators, fixes real bugs, documents false alarms
6. Cursor updates ai-prompts/, debugging-notes.md, task-breakdown.md
7. Repeat for next layer
```

## Key Rejection Examples (for reviewers)

| AI suggestion / finding | Rejected because |
|-------------------------|------------------|
| Change Gold SQL for trend mismatches | Reconciliation comparison bug, not Gold logic |
| Require 4 segmentation rows always | Inactive legitimately empty on sample data |
| Flag only duplicate "copy" rows | Uniqueness must flag all PK participants |
| Claim Databricks dashboard verified | UI never built in workspace |
| Broad `except Exception: pass` | Production-readiness review rejected this pattern |

## Related Files

| File | Purpose |
|------|---------|
| `ai-prompts/*.md` | Per-layer evidence logs |
| `debugging-notes.md` | Issue symptom → root cause → fix |
| `cursor-workflow/project-context.md` | Current state snapshot |
| `cursor-workflow/spec.md` | Technical specification with acceptance status |
| `cursor-workflow/task-breakdown.md` | Phase checklist |
| `tests/TEST_RESULTS.md` | Latest pytest run |
| Agent transcript `50551ecf-...` | Source of truth for prompts |
