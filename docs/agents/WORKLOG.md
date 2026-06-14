# Worklog

Append-only log. Newest entries on top.

## 2026-06-14T15:56:43+03:00 - mcp-agent-entrypoints-agent-routing-deployed
- Task: Commit, push, and deploy `MCP-ENTRYPOINTS-001` agent-routing.
- Files: `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`, `docs/agents/tasks/2026-06-14-mcp-agent-entrypoints-tool-contract-implementation-result.md`
- Result: Committed `1b748263b86694c13370ea82b73bbeb7d042303b` (`Convert MCP how-to tool to agent routing`) on `edmem-req-003-memory-access`, pushed it to `origin`, and deployed that exact MCP ref to `preprod-onto` with `hope4b/mcp-server` workflow run `27499418591`.
- Validation: Deploy workflow completed successfully; log showed `Building image onto-mcp from hope4b/mcp ref='1b748263b86694c13370ea82b73bbeb7d042303b'` and recreated `onto-mcp-server`. No separate runtime MCP tool smoke or Onto object action was performed.
- Next: Owner can smoke a newly connected agent against preprod MCP. Production deploy remains closed until merge/main approval.

## 2026-06-14T14:23:47+03:00 - mcp-agent-entrypoints-agent-routing
- Task: Convert `how_to_use_onto_mcp` from contract/classifier-style output into an agent onboarding/routing tool.
- Files: `onto_mcp/api_resources.py`, `onto_mcp/agent_contract.py`, `onto_mcp/agent_contract.json`, `docs/AGENT_ENTRY_GUIDE.md`, `tests/test_agent_contract.py`, `README.md`, `docs/agents/tasks/2026-06-14-mcp-agent-entrypoints-tool-contract-implementation-result.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`, `docs/agents/DECISIONS.md`
- Result: Public signature is now `how_to_use_onto_mcp(question="", safety_mode="read_only")`; response shape is agent-oriented `{answer,next_calls,clarifying_question?,avoid_tools?,safety_notes?}` with concrete next-call entries `{step,tool,purpose,params,missing_args}`. General ontology Q&A is scope-guarded, read-only mode blocks immediate mutation guidance, and destructive/lifecycle actions still require exact named IDs plus explicit confirmation.
- Validation: `python -m unittest tests.test_agent_contract` passed `13 tests`; `python -m unittest discover -s tests -p "test_*.py"` passed `50 tests`; `python -X pycache_prefix=$env:TEMP\onto_mcp_compile_cache -m compileall onto_mcp` passed; `git diff --check` passed with CRLF normalization warnings only. `python -m pytest tests` was blocked because `pytest` is not installed in the active interpreter.
- Next: QA/Reviewer Agent can review the local agent-routing contract. Status: implemented locally, not committed, not pushed, not deployed; runtime/preprod MCP checks, Onto object actions, commits, pushes, and deploys were not performed.

## 2026-06-11T17:35:00+03:00 - edmem-req-005-mcp-memory-artifact-tools
- Task: Implement dedicated MCP tools for `EDMEM-REQ-005` memory artifacts on branch `edmem-req-003-memory-access`.
- Files: `onto_mcp/api_resources.py`, `tests/test_memory_artifact_tools.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-06-11-edmem-req-005-mcp-implementation-result.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`
- Result: Added dedicated `MemoryArtifact` MCP tools over `/realm/{realmId}/agent-memory/artifact...` for draft create, read by id, accepted path read, own draft/proposed path read, compact accepted search, draft update, append, submit, accept, revoke, and supersede. Existing `search_agent_memory` and `get_agent_memory_record` remain dedicated to first-wave `AgentMemory` records.
- Validation: `python -m pytest tests\test_memory_artifact_tools.py` passed `10 passed, 15 subtests`; `python -m pytest tests\test_memory_artifact_tools.py tests\test_agent_memory_tools.py` passed `16 passed, 25 subtests`; `python -m compileall onto_mcp` passed with workspace-local cache prefix; `python -m pytest tests` passed `37 passed, 45 subtests`; `git diff --check` passed with CRLF normalization warnings only.
- Next: MCP QA handoff and QA/transport smoke when authorized. Commit, push, deploy, object-chat writes, ordinary Onto artifact workarounds, fallback, dual-shape handling, legacy paths, and alternate endpoints remain closed.

## 2026-06-10T09:25:00+03:00 - remove-github-actions-workflow
- Task: Remove repository GitHub Actions workflow from the EDMEM-REQ-003 branch by owner direction.
- Files: `.github/workflows/python-app.yml`, `docs/agents/tasks/2026-06-10-remove-github-actions-workflow.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`
- Result: The branch no longer defines a GitHub Actions workflow; GitHub check results are not an acceptance gate for this project.
- Validation: Documentation/workflow deletion review; no MCP runtime files changed.
- Next: Track PR `https://github.com/hope4b/mcp/pull/9` by implementation review and recorded QA evidence.

## 2026-06-10T07:31:29+03:00 - edmem-req-003-pr-opened
- Task: Push and open PR for EDMEM-REQ-003 dedicated MCP agent-memory read tools.
- Files: `docs/agents/HANDOFF.md`, `docs/agents/WORKLOG.md`
- Result: Branch `edmem-req-003-memory-access` was pushed and PR `https://github.com/hope4b/mcp/pull/9` was opened against `main`.
- Evidence: Implementation commit `5aabcf1` includes `search_agent_memory`, `get_agent_memory_record`, focused tests, catalog/setup docs, and implementation report. Live QA PASS is recorded in `onto-docs`; temporary QA realm cleanup succeeded.
- Next: Track PR checks/review. Deploy has not been requested.

## 2026-06-09T23:30:00+03:00 - edmem-req-003-mcp-memory-access-result
- Task: Complete takeover verification and implementation reporting for EDMEM-REQ-003 dedicated MCP agent-memory target list/search and read-by-id tools.
- Files: `onto_mcp/api_resources.py`, `tests/test_agent_memory_tools.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-06-09-edmem-req-003-mcp-implementation-result.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`
- Validation: `python -m pytest tests\test_agent_memory_tools.py` with `.deps` passed `6 passed, 10 subtests`; `python -m compileall onto_mcp` passed with workspace-local cache prefix; `python -m pytest tests` with `.deps` passed `27 passed, 30 subtests`; real FastMCP stdio transport smoke passed after adding `.deps\win32`, `.deps\win32\lib`, `.deps\pywin32_system32`, and `FASTMCP_CHECK_FOR_UPDATES=off`.
- Notes: Plain `python -m pytest` still fails on existing stale `dev-scripts/test_search_objects.py` importing removed `onto_mcp.resources`. No commit, push, or deploy was performed.
- Next: Orchestrator/QA may run a live backend fixture smoke with a real API key if required, then decide commit/PR routing.

## 2026-06-05T16:00:28+03:00 - get-entity-related-details
- Task: Fix `get_entity(..., related_entities=true)` so MCP exposes related entity ids/names and available relation metadata instead of only a count.
- Files: `onto_mcp/api_resources.py`, `tests/test_get_entity_related_entities.py`, `docs/agents/tasks/2026-06-05-get-entity-related-details.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`
- Validation: `python -m unittest tests.test_get_entity_related_entities`; `python -m unittest discover -s tests -p "test_*.py"`; syntax parse via `ast.parse`; live STDIO smoke on realm `000ba00a-00a0-0a00-a000-000a0a0a0aa3`, entity `123e2296-a62a-41bf-936e-1a12da6ce44b` passed. `python -m compileall onto_mcp` was blocked by local `__pycache__` write permission.
- Next: Commit and open PR when requested.

## 2026-05-29T00:00:00+03:00 - add-existing-nodes-to-diagram
- Task: Add MCP tool for placing existing Onto nodes on an existing diagram as visual representations.
- Files: `onto_mcp/api_resources.py`, `tests/test_add_existing_nodes_to_diagram.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-05-29-add-existing-nodes-to-diagram.md`
- Validation: `python -m unittest tests.test_add_existing_nodes_to_diagram`; `python -m unittest discover -s tests -p "test_*.py"`; syntax parse with `PYTHONDONTWRITEBYTECODE=1`; `python -m compileall onto_mcp`; `git diff --check`.
- Next: Run live smoke for the target EDREST requirements diagram and confirm representation count through `get_diagram`.

## 2026-05-26T00:00:00+03:00 - diagram-list-and-tags-tools
- Task: Add MCP tools for diagram listing/search, context tag search, context tag creation from an existing object, and diagram tag add/remove workflows.
- Files: `onto_mcp/api_resources.py`, `tests/test_diagram_list_and_tags_tools.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-05-26-diagram-list-and-tags-tools.md`
- Validation: `python -m unittest tests.test_diagram_list_and_tags_tools`; `python -m unittest discover -s tests -p "test_*.py"`; syntax parse with `PYTHONDONTWRITEBYTECODE=1`; `git diff --check`.
- Next: Run live smoke with a temporary realm/object/diagram fixture.

## 2026-05-23T00:00:00+03:00 - node-chat-tools
- Task: Add MCP tools for reading and appending Onto object/node chat messages.
- Files: `onto_mcp/api_resources.py`, `tests/test_node_chat_tools.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-05-23-node-chat-tools.md`
- Validation: `python -m unittest tests.test_node_chat_tools`; `python -m unittest discover -s tests -p "test_*.py"`; syntax parse with `PYTHONDONTWRITEBYTECODE=1`; `git diff --check`.
- Next: Run live smoke against a temporary realm/node when a backend test fixture is available.

## 2026-05-08T18:50:00Z - mcp-scope-constraint
- Task: Record the repo-level scope constraint that this repository only accepts MCP development, validation, operation, or deployment work.
- Files: `AGENTS.md`, `docs/agents/tasks/2026-05-08-mcp-scope-constraint.md`
- Validation: Documentation-only change.
- Next: Use the rule to reject or redirect unrelated backend/frontend/doc-only tasks unless needed for MCP integration.

## 2026-05-08T18:40:00Z - structural-search-envelope
- Task: Align `search_entities_by_relations` with the production-ready backend envelope and pagination/sort contract.
- Files: `onto_mcp/api_resources.py`, `tests/test_search_entities_by_relations.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-05-08-structural-search-envelope.md`
- Validation: `python -m unittest tests.test_search_entities_by_relations`; syntax parse with `PYTHONDONTWRITEBYTECODE=1`; `git diff --check`.
- Next: Run live local backend smoke with an `X-API-Key` source available to the test process.

## 2026-04-30T06:00:00Z - document-stdio-mcp-qa-runbook
- Task: Record the repeatable live `stdio MCP` QA baseline for auth, transport, preprod base URL, and temporary fixture cleanup.
- Files: `AGENTS.md`, `docs/agents/TEST_STRATEGY.md`, `docs/agents/tasks/2026-04-30-stdio-mcp-qa-runbook.md`
- Validation: Documentation-only review against the successful local and preprod stdio smoke pattern.
- Next: Reuse this runbook instead of reconstructing `stdio MCP` auth/transport setup from memory.

## 2026-04-30T05:50:00Z - qa-relation-aware-entity-search-mcp
- Task: Run QA for `search_entities_by_relations` with static review, wrapper tests, and real `stdio MCP` smoke.
- Files: `docs/agents/tasks/2026-04-30-relation-aware-entity-search-qa.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`
- Validation: `python -m unittest tests.test_search_entities_by_relations`, `python -m compileall onto_mcp`, real `stdio MCP` smoke against `http://localhost:8080/api/core` and `https://preprod.ontonet.ru/api/v2/core`, including a temporary preprod QA realm fixture with cleanup.
- Next: Reuse the preprod fixture pattern for future MCP smoke checks that need controlled structural-search semantics.

## 2026-04-30T13:30:00+03:00 - add-relation-aware-entity-search-tool
- Task: Added `search_entities_by_relations` as a read-only MCP wrapper over the live relation-aware Onto entity search endpoint.
- Files: `onto_mcp/api_resources.py`, `tests/test_search_entities_by_relations.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-04-30-relation-aware-entity-search-tool.md`
- Validation: `python -m unittest tests.test_search_entities_by_relations`; `python -m unittest discover -s tests -p "test_*.py"`; `python -m compileall onto_mcp`
- Next: Run live Onto smoke for `POST /realm/{realmId}/entity/search` through MCP using a real realm/API key.

## 2026-04-17T00:43:00Z - normalize-batch-meta-key
- Task: Normalize batch entity classification input to use snake_case consistently with the rest of the MCP surface.
- Files: `onto_mcp/api_resources.py`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-04-17-batch-meta-key-alias.md`
- Validation: Imported `onto_mcp.api_resources`; live Onto QA deferred.
- Next: Re-run the batch classification scenario with `meta_entity_id` inside batch items.

## 2026-04-17T00:28:00Z - add-diagram-surface
- Task: Implement the remaining diagram MCP tools and expose the confirmed diagram v2 CRUD surface.
- Files: `onto_mcp/api_resources.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-04-17-diagram-surface.md`
- Validation: Imported `onto_mcp.api_resources`, confirmed diagram tool registration in `FastMCP`, deferred live Onto QA.
- Next: Run QA for the new diagram tools, then validate optional session-state HTTP behavior.

## 2026-04-16T23:59:00Z - add-fields-surface
- Task: Implement the matrix-aligned fields MCP tools and keep entity/template field semantics explicit without extra wrappers.
- Files: `onto_mcp/api_resources.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-04-16-fields-surface.md`
- Validation: Imported `onto_mcp.api_resources`, inspected registered FastMCP tools, deferred live Onto QA.
- Next: Run QA for the new fields tools, then implement the diagrams block.

## 2026-04-17T00:05:00Z - align-template-fields-contract
- Task: Align template field saves with the confirmed preprod contract instead of the stale OpenAPI shape.
- Files: `onto_mcp/api_resources.py`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-04-16-fields-surface.md`, `docs/agents/DECISIONS.md`
- Validation: Updated payload/endpoint contract from a confirmed working example; import smoke still relies on the same runtime path.
- Next: Re-run QA for `save_template_fields`, then continue the remaining fields lifecycle.

## 2026-04-17T00:08:00Z - format-template-fields-response
- Task: Align `save_template_fields` summaries with the confirmed list-shaped success response from preprod.
- Files: `onto_mcp/api_resources.py`, `docs/agents/tasks/2026-04-16-fields-surface.md`, `docs/agents/WORKLOG.md`
- Validation: Imported `onto_mcp.api_resources` after the formatter change.
- Next: Re-run QA for `save_template_fields` and use the returned field ids in the remaining field lifecycle.

## 2026-04-17T00:11:00Z - align-entity-fields-contract
- Task: Align `save_entity_fields` with the confirmed preprod endpoint and payload shape.
- Files: `onto_mcp/api_resources.py`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-04-16-fields-surface.md`, `docs/agents/WORKLOG.md`
- Validation: Contract updated from a confirmed working preprod example; runtime import still required no additional code-path changes.
- Next: Re-run the full fields block with the confirmed entity/template field save contracts.

## 2026-04-17T00:14:00Z - hardcode-string-field-type
- Task: Remove false field type variability from MCP field saves by hardcoding the only confirmed Onto type.
- Files: `onto_mcp/api_resources.py`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/WORKLOG.md`, `docs/agents/DECISIONS.md`
- Validation: Runtime import smoke required after the change.
- Next: Re-run fields QA with `T_STRING` treated as the only supported field type.

## 2026-04-17T00:18:00Z - generate-field-ids-client-side
- Task: Generate field ids on the MCP side for field creates because preprod does not appear to create them implicitly.
- Files: `onto_mcp/api_resources.py`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-04-16-fields-surface.md`, `docs/agents/WORKLOG.md`, `docs/agents/DECISIONS.md`
- Validation: Runtime import smoke required after the change.
- Next: Re-run fields QA with client-generated field ids in both entity and template save payloads.

## 2026-04-17T00:21:00Z - hide-field-type-from-callers
- Task: Stop requiring QA and other callers to know about `fieldTypeName` while MCP injects the only supported type internally.
- Files: `onto_mcp/api_resources.py`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-04-16-fields-surface.md`, `docs/agents/WORKLOG.md`, `docs/agents/DECISIONS.md`
- Validation: Runtime import smoke required after the change.
- Next: Re-run fields QA without `fieldTypeName` in the input payloads.

## 2026-04-16T23:55:00Z - relation-qa-wording-fix
- Task: Align relation and meta-relation QA wording with the actual release criteria used in preprod validation.
- Files: `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-04-16-relation-qa-wording-fix.md`
- Validation: Reviewed relation/meta-relation catalog wording and removed non-release checks around roles and cardinality/equality.
- Next: Continue QA on the remaining fields and diagrams blocks.

## 2026-04-16T23:35:00Z - fix-onto-search-pagination-order
- Task: Align entity and object search pagination with the real Onto API contract.
- Files: `onto_mcp/api_resources.py`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/DECISIONS.md`
- Validation: Re-imported `onto_mcp.api_resources`, confirmed search tools remain registered, reviewed patch diff.
- Next: Re-run positive-path QA for `search_entities` and `search_entities_with_related_meta`.

## 2026-04-16T23:20:00Z - fix-get-entity-result-unwrapping
- Task: Align `get_entity` summary shaping with the real Onto `getEntity` response contract.
- Files: `onto_mcp/api_resources.py`, `docs/income/QA_MCP_TOOL_CATALOG.md`
- Validation: Re-imported `onto_mcp.api_resources`, confirmed `get_entity` remains registered.
- Next: Re-run entity lifecycle QA and verify `get_entity` now exposes identity and related counts correctly.

## 2026-04-16T23:05:00Z - fix-save-entity-message-id-shaping
- Task: Align `save_entity` summary shaping with the real Onto `saveEntity` response contract.
- Files: `onto_mcp/api_resources.py`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/DECISIONS.md`
- Validation: Re-imported `onto_mcp.api_resources`, confirmed `save_entity` remains registered, reviewed patch diff.
- Next: Re-run entity lifecycle QA starting from create and verify downstream steps now receive a usable entity id.

## 2026-04-16T22:45:00Z - remove-deprecated-meta-filtered-surface
- Task: Remove deprecated `/meta/filtered` template listing from the public MCP surface.
- Files: `onto_mcp/api_resources.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/DECISIONS.md`
- Validation: Re-imported `onto_mcp.api_resources`, confirmed `list_templates` is no longer registered, reviewed patch diff.
- Next: Keep QA focused on the non-deprecated template lifecycle and hierarchy tools.

## 2026-04-16T22:35:00Z - add-template-parent-unlink
- Task: Add the missing template-parent unlink MCP tool for the Onto meta hierarchy.
- Files: `onto_mcp/api_resources.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`
- Validation: Re-imported `onto_mcp.api_resources`, confirmed `unlink_template_from_parents` is registered, reviewed patch diff.
- Next: Include unlink coverage in the next template hierarchy QA pass.

## 2026-04-16T22:20:00Z - fix-wrapper-tools-via-helpers
- Task: Fix compatibility wrapper tools that were failing by calling decorated `FunctionTool` objects.
- Files: `onto_mcp/api_resources.py`, `docs/agents/tasks/2026-04-16-wrapper-helper-refactor.md`
- Validation: Re-imported `onto_mcp.api_resources`, confirmed affected tools remain registered, reviewed patch diff.
- Next: Re-run QA for `create_template` and `create_entities_batch` runtime paths.

## 2026-04-16T22:05:00Z - fix-get-template-result-unwrapping
- Task: Fix `get_template` to unwrap the real Onto `result` payload before summary formatting.
- Files: `onto_mcp/api_resources.py`, `docs/agents/tasks/2026-04-16-get-template-result-unwrapping.md`
- Validation: Re-imported `onto_mcp.api_resources` and reviewed the patch diff.
- Next: Re-run template lifecycle QA and check whether other tools also need `result` envelope normalization.

## 2026-04-30T05:50:00Z - qa-relation-aware-entity-search-mcp
- Task: Run QA for `search_entities_by_relations` with static review, wrapper tests, and real `stdio MCP` smoke.
- Files: `docs/agents/tasks/2026-04-30-relation-aware-entity-search-qa.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`
- Validation: `python -m unittest tests.test_search_entities_by_relations`, `python -m compileall onto_mcp`, real `stdio MCP` smoke against `http://localhost:8080/api/core` and `https://preprod.ontonet.ru/api/core`
- Next: Investigate why direct preprod `/entity/search` returns `500` for valid MCP calls while the same tool passes against the local backend fixture.

## 2026-06-14T09:59:45+03:00 - fix-mcp-entrypoints-qa-fail-001
- Task: Fix blocking QA defect `QA-FAIL-001` for `MCP-ENTRYPOINTS-001` destructive/lifecycle required-ID gating.
- Files: `onto_mcp/agent_contract.py`, `tests/test_agent_contract.py`, `docs/agents/tasks/2026-06-14-mcp-agent-entrypoints-tool-contract-implementation-result.md`
- Validation: `python -m unittest tests.test_agent_contract` passed `12 tests`; `python -m unittest discover -s tests -p "test_*.py"` passed `49 tests`; temp-cache `compileall onto_mcp` passed; `git diff --check` passed with CRLF warnings only. `python -m pytest tests` remains blocked because `pytest` is not installed in the active interpreter.
- Next: QA/Reviewer Agent can rerun local source/static/unit QA for the fixed `QA-FAIL-001` probes. Status: implemented locally, not committed, not pushed, not deployed; no runtime/preprod checks and no Onto object actions were performed.

## 2026-06-14T09:33:50+03:00 - mcp-agent-entrypoints-tool-contract
- Task: Implement approved Phase 1 MCP Agent Contract and runtime how-to entrypoint for `MCP-ENTRYPOINTS-001`.
- Files: `onto_mcp/agent_contract.json`, `onto_mcp/agent_contract.py`, `onto_mcp/api_resources.py`, `docs/AGENT_ENTRY_GUIDE.md`, `tests/test_agent_contract.py`, `README.md`, `pyproject.toml`, `docs/agents/tasks/2026-06-14-mcp-agent-entrypoints-tool-contract-implementation-result.md`
- Validation: `python -m unittest tests.test_agent_contract` passed `9 tests`; `python -m unittest discover -s tests -p "test_*.py"` passed `46 tests`; plain `compileall` hit a local `__pycache__` permission error, then `python -X pycache_prefix=$env:TEMP\onto_mcp_compile_cache -m compileall onto_mcp` passed; `git diff --check` passed with CRLF warnings only. `python -m pytest tests` was blocked because `pytest` is not installed in the active interpreter.
- Next: QA/Reviewer Agent can review the local contract/runtime guidance and run backend_qa if separately opened. Status: implemented locally, not committed, not pushed, not deployed; no runtime/preprod checks and no Onto object actions were performed.

## 2026-04-16T21:45:00Z - fix-save-template-id-fallback
- Task: Ensure `save_template` returns a usable identifier even when Onto omits `id/uuid` in the create response.
- Files: `onto_mcp/api_resources.py`, `docs/agents/tasks/2026-04-16-save-template-id-fallback.md`
- Validation: Re-imported `onto_mcp.api_resources` and inspected the patch diff after the formatter fallback change.
- Next: Re-run template lifecycle on preprod and confirm the fallback id matches the actual persisted template id.

## 2026-04-16T21:35:00Z - add-qa-agent-tool-catalog
- Task: Produce a detachable QA-agent document for the current MCP tool surface and its implemented semantics.
- Files: `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-04-16-qa-tool-catalog.md`
- Validation: Introspected registered FastMCP tools and matched them against the documented catalog.
- Next: Keep the QA-agent catalog in sync as field and diagram tools are added.

## 2026-04-16T21:25:00Z - preprod-qa-smoke-baseline
- Task: Prepare a QA smoke baseline for the preprod MCP runtime using the provided Onto API key configuration.
- Files: `docs/agents/tasks/2026-04-16-preprod-qa-smoke.md`
- Validation: Validated runtime settings, inspected registered FastMCP tools, confirmed live preprod user/realm access, and verified empty-result read-only searches.
- Next: Run isolated write-path smoke checks for realm/template/entity/relation operations and then cover HTTP session-state helpers.

## 2026-04-16T21:05:00Z - add-relation-matrix-surface
- Task: Implement the matrix-aligned relation and meta-relation MCP tools.
- Files: `onto_mcp/api_resources.py`, `README.md`, `MCP_SETUP.md`, `docs/agents/tasks/2026-04-16-relation-surface.md`
- Validation: Imported `onto_mcp.api_resources`, inspected registered FastMCP tools, reviewed patch diff.
- Next: Implement field-layer tools, then diagram tools, then run live write-path smoke checks.

## 2026-04-16T20:40:00Z - add-entity-matrix-surface
- Task: Add HTTP Onto API key passthrough via request header and remove the blanket session-state startup requirement for HTTP mode.
- Files: `.gitignore`, `onto_mcp/settings.py`, `onto_mcp/api_resources.py`, `tests/test_http_onto_api_key_passthrough.py`, `tests/test_settings_http_validation.py`, `README.md`, `MCP_SETUP.md`, `docs/agents/tasks/2026-04-23-http-api-key-passthrough.md`
- Validation: `python -m unittest discover -s tests -p "test_*.py"`, `python -m compileall onto_mcp`, local HTTP `POST /mcp` initialize probe without `SESSION_STATE_API_KEY`
- Next: Run a real MCP HTTP client probe that preserves custom headers and session id across `initialize` and `tools/call`.

- Task: Fix `search_relation_templates` name rendering for live backend payloads that expose relation-template name as top-level `name`.
- Files: `onto_mcp/api_resources.py`, `tests/test_search_relation_templates.py`, `docs/agents/tasks/2026-04-21-relation-template-name-fix.md`
- Validation: `python -m unittest tests.test_search_relation_templates`, `python -m compileall onto_mcp`
- Next: Re-run the real stdio smoke to confirm visible relation names are no longer rendered as `N/A`.

- Task: Add a read-only relation-template discovery MCP tool aligned with the new `/meta/relation/find` backend contract.
- Files: `.gitignore`, `onto_mcp/api_resources.py`, `tests/test_search_relation_templates.py`, `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/tasks/2026-04-21-relation-template-discovery.md`
- Validation: `python -m unittest tests.test_search_relation_templates`, `python -m compileall onto_mcp`
- Next: Run a live Onto smoke check for `search_relation_templates` and confirm whether any extra summary fields are worth exposing.

- Task: Implement the matrix-aligned entity MCP tools around Onto upsert semantics and explicit meta reclassification behavior.
- Files: `onto_mcp/api_resources.py`, `README.md`, `MCP_SETUP.md`, `docs/agents/tasks/2026-04-16-entity-surface.md`
- Validation: Imported `onto_mcp.api_resources`, inspected registered FastMCP tools, reviewed patch diff.
- Next: Implement relation/meta-relation tools, then field-layer and diagram-layer tools.

## 2026-04-16T20:05:00Z - add-realm-template-matrix-surface
- Task: Implement the first matrix-aligned realm/template MCP tools without hidden dedup or preflight idempotency.
- Files: `onto_mcp/api_resources.py`, `README.md`, `MCP_SETUP.md`, `docs/agents/tasks/2026-04-16-realm-template-surface.md`
- Validation: Imported `onto_mcp.api_resources`, inspected registered FastMCP tools, reviewed patch diff.
- Next: Implement the entity-layer around `saveEntity` upsert semantics, including declassification and reclassification behavior.

## 2026-04-16T19:05:00Z - add-about-onto-tool
- Task: Add a tool that explains Onto in the style of the canonical about text.
- Files: `onto_mcp/about_content.py`, `onto_mcp/api_resources.py`, `README.md`, `MCP_SETUP.md`, `docs/agents/tasks/2026-04-16-about-onto-tool.md`
- Validation: Confirmed `about_onto` appears in registered FastMCP tools.
- Next: Expand or revise the static text when the editorial source changes.

## 2026-04-16T12:25:00Z - onto-api-key-runtime
- Task: Switch runtime MCP access from Keycloak user auth to config-driven Onto API key.
- Files: `onto_mcp/api_resources.py`, `onto_mcp/server.py`, `onto_mcp/settings.py`, `onto_mcp/__init__.py`, `.env.example`, `README.md`, `MCP_SETUP.md`, `docs/agents/tasks/2026-04-16-onto-api-key-auth.md`
- Validation: Imported server, imported server module with `ONTO_API_BASE` and `ONTO_API_KEY`, inspected registered FastMCP tools from `onto_mcp.api_resources`.
- Next: Run live Onto API smoke checks with a real API key and refine error handling from observed responses.

## 2026-04-16T12:40:00Z - remove-legacy-keycloak
- Task: Delete legacy Keycloak/auth modules and fully clean the public documentation.
- Files: `onto_mcp/auth.py`, `onto_mcp/keycloak_auth.py`, `onto_mcp/resources.py`, `onto_mcp/token_storage.py`, `README.md`, `MCP_SETUP.md`
- Validation: Confirmed files removed from `onto_mcp/`, imported `onto_mcp.server`, searched for stale Keycloak/login references, inspected active FastMCP tools.
- Next: Run live Onto API smoke checks with a real API key.

## 2026-04-16T12:05:00Z - runtime-contract-alignment
- Task: Make server startup/import predictable and align MCP tools with implemented auth flows.
- Files: `onto_mcp/settings.py`, `onto_mcp/server.py`, `onto_mcp/resources.py`, `README.md`, `MCP_SETUP.md`, `docs/agents/tasks/2026-04-16-mcp-runtime-contract.md`
- Validation: Imported `onto_mcp.server` without env, imported server module with minimal env, inspected registered FastMCP tools.
- Next: Decide whether session-state thread helpers stay public and then run live auth/API smoke checks.

## 2026-04-16T11:25:32Z - bootstrap-agents-context
- Task: Create and tailor the multi-agent bootstrap files for this Onto MCP repository.
- Files: `AGENTS.md`, `docs/agents/*`
- Validation: Reviewed repository structure and project metadata from `README.md` and `pyproject.toml`.
- Next: Use these files as the read/update contract for future tasks.
