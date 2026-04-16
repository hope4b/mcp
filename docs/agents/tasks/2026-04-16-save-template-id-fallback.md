# Task Note

## Task
- Short objective: Fix `save_template` so create responses always expose a usable template identifier for the rest of the lifecycle.
- Scope: Adjust MCP summary shaping to fall back to the generated request id when Onto create response omits `id/uuid`.
- Out of scope: Backend API response changes on preprod.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`
- Behavioral impact:
  - `save_template` now returns the generated request id when the Onto response lacks `id/uuid`.
  - Template lifecycle is no longer blocked on MCP summary shaping for create responses.
- Risks:
  - This is an MCP-side fallback, not proof that Onto persisted the same id in every backend scenario.

## Validation
- Commands run:
  - `python - <<import snippet>>`
  - `git diff -- onto_mcp/api_resources.py`
- Result:
  - `onto_mcp.api_resources` still imports successfully after the formatter change.
- Not run (and why):
  - Live create/get/delete verification was not rerun in this step.

## Commit Description (English)
- Short commit description: add fallback template id in save_template summary
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: rerun template lifecycle on preprod and confirm the fallback id matches actual persisted template id.
- Recommended next owner (area): QA/Reviewer Agent / Data/API Agent
