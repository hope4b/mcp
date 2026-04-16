# Task Note

## Task
- Short objective: Fix `get_template` summary shaping against the real Onto `getMetaEntity` response.
- Scope: Unwrap the `result` object before formatting template identity fields.
- Out of scope: Broader response normalization across all tools.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`
- Behavioral impact:
  - `get_template` now formats the actual template object from `result`.
  - `ID` and `Name` should no longer be lost when Onto returns the wrapped payload shape.
- Risks:
  - Other tools may still need similar response unwrapping if their endpoints also use nested `result` envelopes.

## Validation
- Commands run:
  - `python - <<import/introspection snippet>>`
  - `git diff -- onto_mcp/api_resources.py`
- Result:
  - `onto_mcp.api_resources` imports successfully after the fix.
- Not run (and why):
  - Live `get_template` recheck was not rerun in this step.

## Commit Description (English)
- Short commit description: unwrap result payload in get_template
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: rerun template lifecycle QA to confirm `get_template` summary now exposes `uuid` and `name`.
- Recommended next owner (area): QA/Reviewer Agent / Data/API Agent
