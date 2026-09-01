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
6. the exact task-local spec, handoff, review/QA evidence and source files
   supplied by the validated role manifest

`docs/agents/HANDOFF.md` and `docs/agents/WORKLOG.md` are frozen coordination
history. They are not bootstrap, current state, recovery input, output or
fallback. Read an exact bounded hashed range only for an explicitly assigned
historical audit.

## Required Update Order (After Any Edit)
1. Add task note based on `docs/agents/TASK_TEMPLATE.md`
2. Keep next owner, follow-up and evidence in that exact task-local artifact.
3. Append to `docs/agents/DECISIONS.md` only if canonical process,
   architecture or MCP semantics changed.
4. If code was changed, end assistant response with short commit description in English (mandatory final line format: `Commit description (EN): <short text>`)

## Project Baseline
- Stack: Python, FastMCP, API-key-backed Onto API integration
- Package manager: `pip`
- Python version: use the version declared by current package/runtime evidence;
  verify when runtime-sensitive
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

Resident `mcp-owner` owns MCP runtime/tool/guidance and the MCP HTTP delivery
tract. Route independent QA, general infrastructure, backend implementation
and agent-governance work to their responsible residents; do not substitute
legacy local role names for accepted/current realm authority.

## Guardrails
- Do not commit secrets.
- Do not rewrite unrelated files.
- Keep changes minimal and scoped.
- Validate behavior with tests/lint when possible.
- After each code change task, assistant MUST end the final response with `Commit description (EN): <short text>` in English.
