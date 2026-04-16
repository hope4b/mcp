## Task
- Short objective: Align relation and meta-relation QA wording with the actual release criteria validated in preprod.
- Scope: Update QA-facing documentation to remove non-release checks around relation roles and meta-relation cardinality/equality semantics.
- Out of scope: Runtime code changes, additional API verification, or expansion of the MCP surface.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-04-16-relation-qa-wording-fix.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`
- Behavioral impact: None. Documentation-only correction of QA criteria.
- Risks:
  - Historical notes or external QA checklists may still reference the older, stricter relation wording.
  - If release criteria change later, the catalog will need another explicit update.

## Validation
- Commands run:
  - `rg -n "start_min|start_max|end_min|end_max|equal|start_role|end_role|meta-relation|create_meta_relation|update_meta_relation|create_relation|update_relation" docs/income/QA_MCP_TOOL_CATALOG.md docs/agents/DECISIONS.md`
  - `Get-Content docs/income/QA_MCP_TOOL_CATALOG.md | Select-Object -Skip 220 -First 120`
  - `Get-Content docs/agents/DECISIONS.md | Select-Object -Last 80`
- Result:
  - Confirmed the catalog still required relation-role persistence and meta-relation cardinality/equality verification.
  - Updated the QA-facing wording to match the actual release gate used in testing.
- Not run (and why):
  - Live API checks: not needed for this wording-only correction.

## Commit Description (English)
- Short commit description: Fix relation QA wording to match release criteria
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work:
  - Continue with the remaining unopened QA blocks: fields and diagrams.
- Recommended next owner (area): `QA/Reviewer Agent`
