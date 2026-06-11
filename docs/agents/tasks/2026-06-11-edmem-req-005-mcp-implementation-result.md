# EDMEM-REQ-005 - MCP Implementation Result

## Task
- Short objective: Implement dedicated MCP tools for `EDMEM-REQ-005` memory artifacts over the deployed backend artifact API.
- Scope: `mcp` runtime repository only, existing branch `edmem-req-003-memory-access`.
- Out of scope: backend changes, `onto-docs` changes, Onto object search/substitution, object-chat milestone writes, MCP QA verdict, commit, push, deploy, fallback routes, dual-shape handling, legacy paths, ordinary Onto artifact workarounds.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes
- TEST_STRATEGY.md read: yes
- HANDOFF.md read: yes
- WORKLOG.md read: yes
- Onto Object Anchor Contract read: yes
- EDMEM-REQ-005 MCP handoff read: yes
- EDMEM-REQ-005 Change Spec read: yes
- Backend preprod deploy result read: yes
- EDMEM-REQ-003 MCP implementation result read: yes
- Relevant EDMEM-REQ-005 review log/backend QA route evidence read: yes

## Onto Anchor
- received: yes
- role: primary_change_object
- realm_id: `000ba00a-00a0-0a00-a000-000a0a0a0aa3`
- object_id: `65228682-487e-4745-a19a-2341f16293bd`
- object_code: `EDMEM-REQ-005`
- locked: yes
- substitution allowed: no
- object chat written: no

## Changes
- Files changed:
  - `onto_mcp/api_resources.py`
  - `tests/test_memory_artifact_tools.py`
  - `README.md`
  - `MCP_SETUP.md`
  - `docs/income/QA_MCP_TOOL_CATALOG.md`
  - `docs/agents/tasks/2026-06-11-edmem-req-005-mcp-implementation-result.md`
  - `docs/agents/WORKLOG.md`
  - `docs/agents/HANDOFF.md`
- Behavioral impact:
  - Added dedicated MCP memory artifact tools over `/realm/{realmId}/agent-memory/artifact...`.
  - Existing `search_agent_memory` and `get_agent_memory_record` remain unchanged and target `AgentMemory` records only.
  - No ordinary entity/template/relation/diagram/search or object-chat tool was repurposed as artifact storage or recovery.

## Tools And Operation Mapping
- `create_memory_artifact_draft`: create draft artifact.
- `get_memory_artifact`: read full artifact by id.
- `get_memory_artifact_by_path`: read current accepted artifact by path.
- `get_own_memory_artifact_draft_by_path`: read caller-owned draft/proposed artifact by path with selector-only principal.
- `search_memory_artifacts`: compact accepted artifact search/list.
- `update_memory_artifact_draft`: update draft body/summary/review destination/targets.
- `append_memory_artifact`: append to append-mode artifact where backend allows it.
- `submit_memory_artifact`: submit draft to proposed.
- `accept_memory_artifact`: accept proposed artifact through backend-authorized lifecycle route.
- `revoke_memory_artifact`: revoke artifact through backend-authorized lifecycle route.
- `supersede_memory_artifact`: supersede accepted replace-mode artifact with accepted successor.

## Backend Routes Called
- `POST /realm/{realmId}/agent-memory/artifact/draft`
- `GET /realm/{realmId}/agent-memory/artifact/{artifactId}`
- `POST /realm/{realmId}/agent-memory/artifact/path`
- `POST /realm/{realmId}/agent-memory/artifact/own/path`
- `POST /realm/{realmId}/agent-memory/artifact/search`
- `POST /realm/{realmId}/agent-memory/artifact/{artifactId}/draft`
- `POST /realm/{realmId}/agent-memory/artifact/{artifactId}/append`
- `POST /realm/{realmId}/agent-memory/artifact/{artifactId}/submit`
- `POST /realm/{realmId}/agent-memory/artifact/{artifactId}/accept`
- `POST /realm/{realmId}/agent-memory/artifact/{artifactId}/revoke`
- `POST /realm/{realmId}/agent-memory/artifact/{artifactId}/supersede`

No MCP tool was added for backend-only `GET /realm/{realmId}/agent-memory/artifact/{artifactId}/audit`.

## Request Fields Accepted From MCP Callers
- Common: `realm_id`, `artifact_id`, `artifact_path`.
- Create/supersede: `artifact_kind`, `write_mode`, `body`, `summary`, `source_ref`, `source_context`, `review_destination`, `agent_principal`, `targets`.
- Update draft: `body`, `summary`, `review_destination`, `agent_principal`, `targets`.
- Append: `body`, `summary`, `source_ref`, `source_context`, `agent_principal`.
- Search: `artifact_kind`, `write_mode`, `artifact_path`, `review_destination`, `target_kind`, `target_id`, `query`, `first`, `offset`.
- Path reads: `artifact_path`; own draft/proposed path reads also require selector-only `agent_principal`.

## Backend-Derived Fields Not Trusted From MCP Input
- Effective caller principal.
- Authorization and realm role.
- Audit actor.
- Lifecycle status transitions and terminal-state rules.
- Accepted-path uniqueness.
- Supersession validity and same-path replacement checks.
- Creation/update/accepted/superseded/revoked timestamps.
- Artifact ids, append-entry ids, audit ids, and persisted system-layer identity.

## Response Shape Summary
- Compact search/list:
  - Renders `{items,total,first,offset}`.
  - Suppresses any unexpected `body` or `append_entries` fields in search items by setting them to `null`.
  - Includes compact item metadata and raw compact page JSON.
- Full reads and write lifecycle responses:
  - Render full backend artifact JSON including `body`, targets, append entries when returned, supersession/revocation markers, and `audit_summary`.
  - Do not expose full backend audit event streams.

## Validation And Error Behavior
- MCP validates required `realm_id`, UUID-shaped artifact ids, artifact kind/write-mode pairing, pagination bounds, non-empty target lists, target kind/id shape, and empty update payloads before backend calls.
- `supersede_memory_artifact` requires replacement `write_mode=replace` before backend call.
- Backend errors are surfaced through the existing plain-text `Onto API error <status>` handling.
- Backend remains authoritative for principal matching, authorization, target existence, lifecycle conflicts, accepted-path uniqueness, and no-existence-leak behavior.

## Ordinary Tool Exclusion Evidence
- `save_entity`, `save_template`, relation, diagram, search, and object-chat tools were not changed into artifact routes.
- `search_agent_memory` and `get_agent_memory_record` signatures and routes remain dedicated to first-wave `AgentMemory` records.
- Focused tests assert artifact tools use `/agent-memory/artifact...`, do not route through `/chat/`, and no full audit MCP tool is exposed.

## Developer Checks Run
- `$env:PYTHONPATH='D:\git\onto\_onto\mcp\.deps'; python -m pytest tests\test_memory_artifact_tools.py`
  - Result: `10 passed, 15 subtests passed`
- `$env:PYTHONPATH='D:\git\onto\_onto\mcp\.deps'; python -m pytest tests\test_memory_artifact_tools.py tests\test_agent_memory_tools.py`
  - Result: `16 passed, 25 subtests passed`
- `$env:PYTHONPYCACHEPREFIX='D:\git\onto\_onto\mcp\.pycache-check'; python -m compileall onto_mcp`
  - Result: passed
- `$env:PYTHONPATH='D:\git\onto\_onto\mcp\.deps'; python -m pytest tests`
  - Result: `37 passed, 45 subtests passed`
- `git -C D:\git\onto\_onto\mcp diff --check`
  - Result: no whitespace errors; Git reported CRLF normalization warnings for touched files.

## Skipped Checks
- Live MCP transport smoke: skipped; QA gate is separate and no live MCP QA verdict is part of this developer implementation task.
- Live backend artifact write smoke: skipped; QA role owns controlled live fixture execution and cleanup.
- Deployed MCP smoke against `https://preprod.ontonet.ru/mcp`: skipped; deploy/QA gate is separate.
- Plain `python -m pytest`: skipped because the repo has a known stale root collection issue from `dev-scripts/test_search_objects.py` importing removed `onto_mcp.resources`; `python -m pytest tests` passed.

## Delivery Status
- Commit: not performed.
- Push: not performed.
- Deploy: not performed.
- Branch: stayed on `edmem-req-003-memory-access`.
- Object chat: not written.

## Handoff
- Remaining work: MCP QA handoff and QA/transport smoke for dedicated artifact tools, including live checks against `https://preprod.ontonet.ru/api/v2/core` and deployed MCP endpoint when authorized.
- Recommended next owner: QA/Reviewer Agent for MCP QA.

## Commit Description (English)
- Short commit description: Add MCP memory artifact tools.
