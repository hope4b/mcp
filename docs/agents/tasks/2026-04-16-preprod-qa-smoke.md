## Task
- Short objective: Prepare and validate a QA smoke-testing baseline for the PreOnto MCP server against the provided preprod API key configuration.
- Scope: Runtime config validation, registered MCP surface verification, live read-only connectivity checks, and a practical regression checklist for further QA.
- Out of scope: Write-path mutations in shared realms, field/diagram tool verification, load/performance benchmarking, and CI automation.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `docs/agents/tasks/2026-04-16-preprod-qa-smoke.md`
- Behavioral impact: None. Documentation-only QA preparation.
- Risks:
  - The provided API key is active and should be rotated outside the repository if it is not intended for long-term shared testing.
  - Read-only smoke passed, but write-path behavior remains unverified in preprod.
  - Session-state helpers were not exercised because HTTP transport and `SESSION_STATE_API_KEY` were not part of this test scope.

## Validation
- Commands run:
  - `Get-Content AGENTS.md`
  - `Get-Content docs/agents/ROLES.md`
  - `Get-Content docs/agents/PROJECT_CONTEXT.md`
  - `Get-Content docs/agents/ARCHITECTURE_MAP.md`
  - `Get-Content docs/agents/TEST_STRATEGY.md`
  - `Get-Content docs/agents/HANDOFF.md`
  - `Get-Content docs/agents/WORKLOG.md | Select-Object -Last 80`
  - `rg -n "ONTO_API_KEY|ONTO_API_BASE|FastMCP|tool" onto_mcp README.md MCP_SETUP.md pyproject.toml`
  - `@' ... from onto_mcp.api_resources import mcp ... '@ | python -`
  - `@' ... from onto_mcp.settings import validate_runtime_settings ... '@ | python -`
  - `@' ... from onto_mcp.api_resources import _get_current_user_data ... '@ | python -`
  - `@' ... from onto_mcp.api_resources import _get_user_spaces_data, _request_json ... '@ | python -`
- Result:
  - Runtime settings validation passed for `ONTO_API_BASE=https://preprod.ontonet.ru/api/v2/core` and the provided `ONTO_API_KEY`.
  - Registered MCP tool surface resolved successfully and currently exposes 21 tools.
  - Live preprod smoke succeeded for `GET /user/v2/current`.
  - The configured API key can access 8 realms.
  - Default realm resolution succeeded with realm `520af61a-5324-4380-88d9-fd0721d138de`.
  - Read-only empty-result checks succeeded for `/meta/find`, `/entity/find`, and `/entity/find/v2`.
- Not run (and why):
  - `pytest`: no repository test suite currently present under `tests/`.
  - Write-path realm/template/entity/relation mutations: skipped to avoid shared-environment side effects without an isolated QA namespace.
  - HTTP/session-state checks: skipped because `SESSION_STATE_API_KEY` was not provided.

## Commit Description (English)
- Short commit description: Add preprod QA smoke baseline note
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work:
  - Run isolated write-path smoke for realm/template/entity/relation flows using a dedicated QA naming prefix and explicit cleanup.
  - Validate session-state helpers in HTTP mode with `SESSION_STATE_API_KEY`.
  - Convert the smoke checklist into repeatable automated tests when stable fixture realms are available.
- Recommended next owner (area): `QA/Reviewer Agent` with support from `Feature Agent` for write-path contract clarification.
