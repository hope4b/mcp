# MCP Agent Entrypoints and Tool Contract - Implementation Result

## Task
- Short objective: Implement approved MCP agent onboarding/routing behavior for `how_to_use_onto_mcp`.
- Scope: `mcp` only; runtime how-to tool signature/response, canonical contract metadata, rendered guide, safety/ID routing guidance, and local static/unit checks.
- Out of scope: `onto-docs` edits, runtime/preprod MCP checks, deploy, commit, push, PR, Onto object lookup/create/substitution, Onto object-chat writes, backend/frontend/GraphQL/deploy-infra changes, compatibility adapters, fallback, aliases, tool renames/removals, namespaces, or progressive disclosure beyond the explicit how-to tool.

## Context Used
- `mcp/AGENTS.md` read: yes
- `mcp/docs/agents/ROLES.md` read: yes
- `mcp/docs/agents/PROJECT_CONTEXT.md` read: yes
- `mcp/docs/agents/ARCHITECTURE_MAP.md` read: yes
- `mcp/docs/agents/TEST_STRATEGY.md` read: yes
- `mcp/docs/agents/HANDOFF.md` read: yes
- latest `mcp/docs/agents/WORKLOG.md` entries read: yes
- `onto-docs/docs/agents/process/ONTO_OBJECT_ANCHOR_CONTRACT.md` read: yes
- approved change spec read: yes
- review artifact read: yes
- implementation handoff read: yes
- relevant current MCP files read: `README.md`, `onto_mcp/api_resources.py`, `onto_mcp/server.py`, existing tests under `tests`.

## Onto Anchor And Milestone Status
- Locked primary Onto anchor received: no
- Milestone logging: deferred
- Onto lookup/create/substitution performed: no
- Object-chat writes performed: no

## Changes
- Files changed:
  - `README.md`
  - `pyproject.toml`
  - `onto_mcp/api_resources.py`
  - `onto_mcp/agent_contract.py`
  - `onto_mcp/agent_contract.json`
  - `docs/AGENT_ENTRY_GUIDE.md`
  - `tests/test_agent_contract.py`
  - `docs/agents/tasks/2026-06-14-mcp-agent-entrypoints-tool-contract-implementation-result.md`
  - `docs/agents/WORKLOG.md`
  - `docs/agents/HANDOFF.md`
  - `docs/agents/DECISIONS.md`
- Behavioral impact:
  - Added canonical machine-readable MCP Agent Contract at `onto_mcp/agent_contract.json`.
  - Added packaged contract loader and guidance builder in `onto_mcp/agent_contract.py`.
  - Added runtime-visible `how_to_use_onto_mcp(question="", safety_mode="read_only")` tool through the live `api_resources.py` MCP surface.
  - The public how-to response is now agent-shaped: `answer`, `next_calls`, optional `clarifying_question`, optional `avoid_tools`, and optional `safety_notes`.
  - `next_calls` entries use exact tool names with `step`, `tool`, `purpose`, `params`, and `missing_args`; `missing_args` only names values obtainable through another MCP tool.
  - Implemented conservative routing for no-task, known-task, unclear-task, ambiguous-task, read-only, write-intent missing-ID, destructive/lifecycle gating, and general ontology glossary prompts.
  - Added rendered human guide at `docs/AGENT_ENTRY_GUIDE.md`, checked against the contract by tests.
  - Added contract coverage tests so every registered MCP tool has exactly one contract entry and one family mapping.
  - Added package data configuration so the JSON contract is included with the Python package.
- Risks:
  - Routing remains keyword-based and conservative; future domain phrasing may require explicit oracle additions.
  - The how-to tool is intentionally conservative for high-risk memory artifact writes and does not make them immediate next calls in read-only routing.
  - Static tests inspect decorated tool functions in `api_resources.py`; if registration style changes, the coverage test will need to be updated with the new canonical registration source.

## Validation
- Commands run:
  - `python -m unittest tests.test_agent_contract`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - `python -m compileall onto_mcp`
  - `$cache = Join-Path $env:TEMP 'onto_mcp_compile_cache'; python -X pycache_prefix=$cache -m compileall onto_mcp`
  - `python -m pytest tests`
  - `git diff --check`
  - `git status --short`
  - `python --version`
- Result:
  - `python -m unittest tests.test_agent_contract`: passed, 13 tests in the latest agent-routing iteration.
  - `python -m unittest discover -s tests -p "test_*.py"`: passed, 50 tests in the latest agent-routing iteration.
  - Plain `python -m compileall onto_mcp`: failed because the interpreter could not write in-place bytecode under `onto_mcp/__pycache__` (`PermissionError: [Errno 13] Permission denied`).
  - Compile rerun with temporary cache prefix: passed in the latest agent-routing iteration.
  - `python -m pytest tests`: not run successfully; active interpreter has no `pytest` module.
  - `git diff --check`: passed; only CRLF normalization warnings for touched tracked files.
  - `python --version`: `Python 3.13.7`.
- Not run (and why):
  - Runtime/preprod MCP checks: explicitly out of scope.
  - Deploy checks: explicitly out of scope.
  - Onto object lookup/create/substitution or object-chat writes: explicitly out of scope and no locked Onto anchor was supplied.
  - `pytest` suite: blocked by missing `pytest` in active interpreter; equivalent `unittest` discovery over `tests` passed.

## Exact Environment Validity
- Verification timestamp: `2026-06-14T09:33:50+03:00`
- Latest verification timestamp: `2026-06-14T14:23:47+03:00`
- Working directory: `D:\git\onto\_onto\mcp`
- Shell: Windows PowerShell
- Python: `Python 3.13.7`
- Validation scope: local source/static/unit checks only; no runtime MCP transport, no preprod, no Onto backend state, no deployment.

## Commit / Push / Deploy Status
- Status: implemented locally, not committed, not pushed, not deployed.
- PR created: no.

## Handoff
- Remaining work:
  - Owner/QA may run backend_qa against the local implementation if opened separately.
  - If runtime/preprod validation is later requested, use the new `how_to_use_onto_mcp` entrypoint through a real MCP client and keep preprod checks separate from this implementation result.
  - Decide in a future approved scope whether high-risk memory artifact write guidance needs a dedicated safety mode.
- Recommended next owner (area): QA/Reviewer Agent for contract acceptance review.

## QA-FAIL-001 Fix Note
- Timestamp: `2026-06-14T09:59:45+03:00`
- Defect fixed: destructive/lifecycle ID gating was too permissive because a single UUID plus confirmation could satisfy every required ID in a matched task family.
- Files changed for fix:
  - `onto_mcp/agent_contract.py`
  - `tests/test_agent_contract.py`
  - `docs/agents/tasks/2026-06-14-mcp-agent-entrypoints-tool-contract-implementation-result.md`
  - `docs/agents/WORKLOG.md`
  - `docs/agents/HANDOFF.md`
- Behavior changed:
  - Removed the bare-UUID shortcut from required-ID matching.
  - Required-ID presence is now requirement-specific: a task must name the requirement token, such as `realm_id` and `diagram_id`/`artifact_id`, with a value.
  - `or` requirements are handled as alternatives; slash/list requirements are conservative and require each named token in the selected alternative.
  - Destructive/lifecycle probes with one UUID plus `confirmed` remain blocked when `realm_id` and target ID are not separately established.
- Regression tests added:
  - `delete diagram 11111111-1111-1111-1111-111111111111 confirmed` with `destructive_intent` keeps `delete_diagram` blocked and marks `realm_id`/`diagram_id` missing.
  - `accept artifact 11111111-1111-1111-1111-111111111111 confirmed` with `lifecycle_intent` keeps memory lifecycle tools blocked and marks `realm_id`/`artifact_id` missing.
  - Helper-level test confirms a bare UUID does not satisfy `realm_id` or `diagram_id`, while named values do.
- Checks rerun:
  - `python -m unittest tests.test_agent_contract`: passed, 12 tests.
  - `python -m unittest discover -s tests -p "test_*.py"`: passed, 49 tests.
  - `$cache = Join-Path $env:TEMP 'onto_mcp_compile_cache'; python -X pycache_prefix=$cache -m compileall onto_mcp`: passed.
  - `git diff --check`: passed; CRLF normalization warnings only for already touched tracked files.
  - `python -m pytest tests`: blocked because `pytest` is not installed in the active interpreter.
- Not run:
  - Runtime/preprod MCP checks, deploy checks, Onto object lookup/create/substitution/object-chat writes: explicitly out of scope.
- Delivery status after fix: implemented locally, not committed, not pushed, not deployed.

## Agent Routing Iteration Note
- Timestamp: `2026-06-14T14:23:47+03:00`
- Approved task implemented: Change existing local `how_to_use_onto_mcp` iteration from contract-ish classifier output into an agent onboarding/routing tool.
- Files changed for iteration:
  - `onto_mcp/api_resources.py`
  - `onto_mcp/agent_contract.py`
  - `onto_mcp/agent_contract.json`
  - `docs/AGENT_ENTRY_GUIDE.md`
  - `tests/test_agent_contract.py`
  - `README.md`
  - `docs/agents/tasks/2026-06-14-mcp-agent-entrypoints-tool-contract-implementation-result.md`
  - `docs/agents/WORKLOG.md`
  - `docs/agents/HANDOFF.md`
  - `docs/agents/DECISIONS.md`
- Behavior changed:
  - Public signature is now `how_to_use_onto_mcp(question: str = "", safety_mode: str = "read_only")`.
  - Tool docstring says to call it first before other Onto MCP tools when choosing the correct Onto tool sequence for a user goal.
  - Public response shape is `{answer,next_calls,clarifying_question?,avoid_tools?,safety_notes?}`.
  - `next_calls` entries are concrete and agent-invocable: `{step,tool,purpose,params,missing_args}`.
  - `tool_families` remains internal contract data and is not exposed as main top-level guidance.
  - General ontology prompts such as `что такое онтология?` are scope-guarded and ask for an actionable MCP goal.
  - `read_only` mode keeps write/destructive/lifecycle/admin-like/high-risk tools out of immediate `next_calls`.
  - Destructive/lifecycle actions still require exact named IDs plus explicit operator confirmation; a bare UUID remains insufficient.
- Agent-shaped oracle tests added or updated:
  - Template management with no known inputs routes `list_available_realms` then `search_templates`, while write/delete tools are avoided.
  - Object-by-name search routes realm discovery then object/entity search, with `realm_id` missing arg sourced from `list_available_realms`.
  - Diagram update by name routes realm discovery, diagram search, and get; `update_diagram` is avoided until exact IDs and `write_intent`.
  - Template delete by name does not route `delete_template` immediately and asks for exact IDs plus confirmation.
  - Unclear goal asks a clarifying question and routes only safe discovery.
  - Russian ontology glossary prompt is scope-guarded with no glossary answer.
- Checks rerun:
  - `python -m unittest tests.test_agent_contract`: passed, 13 tests.
  - `python -m unittest discover -s tests -p "test_*.py"`: passed, 50 tests.
  - `python -X pycache_prefix=$env:TEMP\onto_mcp_compile_cache -m compileall onto_mcp`: passed.
  - `git diff --check`: passed; CRLF normalization warnings only for already touched tracked files.
  - `python -m pytest tests`: blocked because `pytest` is not installed in the active interpreter.
- Not run:
  - Runtime/preprod MCP checks, deploy checks, Onto object lookup/create/substitution/object-chat writes: explicitly out of scope.
- Delivery status after iteration: implemented locally, not committed, not pushed, not deployed.

## Commit Description (English)
- Short commit description: Convert MCP how-to tool to agent routing
