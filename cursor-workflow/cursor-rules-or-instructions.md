# Cursor Rules & Instructions

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
| Gold | Business aggregations |
| SQL | Readable and formatted |
| Tests | Required for major implementations |
| AI docs | Log sessions in `ai-prompts/` |
| Reuse | Inspect existing code before adding utilities |

## Before Starting a Task

1. Read `cursor-workflow/project-context.md`
2. Check `cursor-workflow/task-breakdown.md` for current status
3. Review relevant layer file in `ai-prompts/`
4. Follow `.cursor/rules/medallion-pipeline.mdc`

## Architecture Change Policy

Do not modify Bronze/Silver/Gold responsibilities without:

1. Documenting rationale in `design-notes.md`
2. Obtaining explicit approval
