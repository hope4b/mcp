# Multi-Agent Context Protocol

This repository uses a shared context protocol for all coding agents.

## Goal
Keep project knowledge in versioned files so any agent can continue work safely.

## Scope Constraint
Agents working in this repository must accept only tasks directly related to developing, validating, operating, or deploying the Onto MCP server. Backend, frontend, or unrelated documentation work is out of scope unless it is necessary to verify an MCP contract or keep the MCP integration working.

## Required Read Order (Before Any Edit)
1. `AGENTS.md`
2. `docs/agents/ROLES.md`
3. `docs/agents/PROJECT_CONTEXT.md`
4. `docs/agents/ARCHITECTURE_MAP.md`
5. `docs/agents/TEST_STRATEGY.md`
6. `docs/agents/HANDOFF.md`
7. Last entries in `docs/agents/WORKLOG.md`

## Required Update Order (After Any Edit)
1. Add task note based on `docs/agents/TASK_TEMPLATE.md`
2. Append a short entry to `docs/agents/WORKLOG.md`
3. Update `docs/agents/HANDOFF.md` if there are next steps
4. Append to `docs/agents/DECISIONS.md` if process/architecture changed
5. If code was changed, end assistant response with short commit description in English (mandatory final line format: `Commit description (EN): <short text>`)

## Project Baseline
- Stack: Python, FastMCP, Keycloak-backed Onto API integration
- Package manager: `pip`
- Python version: `3.12+` assumed from local bytecode artifacts; verify if runtime-sensitive
- Main source: `onto_mcp/`
- Locales: English docs and API-facing text; some repository/user-facing content may be Russian

## MCP QA Quick Reference
- Default auth path for `stdio` runtime QA: configured `ONTO_API_KEY` -> outbound `X-API-Key`.
- Default preprod base URL for live MCP smoke: `https://preprod.ontonet.ru/api/v2/core`.
- For real `stdio` smoke on Windows in this workspace:
  - use an installed/runtime-available `fastmcp` client;
  - if needed, add repository-local dependencies through `.deps` and prepend them via `PYTHONPATH`;
  - when `stdio` subprocess transport hits sandbox pipe restrictions, rerun the real smoke outside the sandbox rather than falling back to direct function import.
- For write-assisted MCP smoke, prefer a temporary QA realm, record IDs in the QA note, and delete the realm after the run.

## Role Model
1. `Coordinator`
2. `Feature Agent`
3. `Data/API Agent`
4. `Platform/Infra Agent`
5. `QA/Reviewer Agent`

## Guardrails
- Do not commit secrets.
- Do not rewrite unrelated files.
- Keep changes minimal and scoped.
- Validate behavior with tests/lint when possible.
- After each code change task, assistant MUST end the final response with `Commit description (EN): <short text>` in English.
