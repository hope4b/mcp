# Handoff

## Role Directory
- `Coordinator`: `unassigned` (backup: `unassigned`)
- `Feature Agent`: `feature-main` (backup: `fix-main`)
- `Data/API Agent`: `unassigned` (backup: `unassigned`)
- `Platform/Infra Agent`: `unassigned` (backup: `unassigned`)
- `QA/Reviewer Agent`: `unassigned` (backup: `unassigned`)

## Active Claims
- None.

## Next Priority Queue
1. Track EDMEM-REQ-003 PR `https://github.com/hope4b/mcp/pull/9`; live QA passed and the temporary QA realm was deleted. The repository GitHub Actions workflow is being removed by owner direction, so GitHub check results are not an acceptance gate. Deploy has not been requested.
1. `fix/get-entity-related-details` was merged as PR `#8`; no separate local action remains for that branch.
2. Run live smoke for `add_existing_nodes_to_diagram` by placing `EDREST-REQ-001..005` on diagram `7fdd80aa-9bba-4fa6-9c93-f8e11dcef67b` and confirm `get_diagram` reports `Representations: 5`.
2. Run live smoke for `search_diagrams`, `search_context_tags`, `create_context_tag_from_object`, `add_diagram_tag`, and `remove_diagram_tag` with a temporary realm/object/diagram fixture.
3. Run live smoke for `get_node_chat_messages` and `create_node_chat_message` against a temporary realm/node fixture.
4. Run live local backend smoke for `search_entities_by_relations` against `http://localhost:8080/api/core` with an `X-API-Key` source and confirm the `{items,total,first,offset}` envelope is rendered correctly through MCP.
5. Re-run the batch classification scenario with `meta_entity_id` inside batch items to confirm the contract-consistency fix.
6. Validate HTTP transport session-state helpers with a real `SESSION_STATE_API_KEY`.
7. Verify whether any relation `additional_properties` normalization is still required for the release surface.
8. Run a real MCP HTTP client probe for `X-Onto-Api-Key` passthrough and confirm the client preserves both custom headers and MCP session id across `initialize` and `tools/call`.
9. Re-run the live stdio smoke for `search_relation_templates` and confirm that top-level backend `name` now renders correctly in multi-result output.
10. Keep `docs/income/QA_MCP_TOOL_CATALOG.md` synchronized with the runtime tool surface if more optional endpoints are added.

## Last Completed
- `2026-06-10T09:25:00+03:00`: Removed the repository GitHub Actions workflow from the EDMEM-REQ-003 branch by owner direction and recorded that GitHub check results are not an acceptance gate for this project. No MCP runtime behavior changed.
- `2026-06-10T07:31:29+03:00`: Pushed `edmem-req-003-memory-access` and opened PR `https://github.com/hope4b/mcp/pull/9` for EDMEM-REQ-003. Commit `5aabcf1` contains the dedicated MCP agent-memory read tools and report. Live QA PASS is recorded in `onto-docs`; no deploy was requested.
- `2026-06-09T23:30:00+03:00`: Verified and reported EDMEM-REQ-003 MCP target-scoped memory access implementation. Targeted pytest passed `6 passed, 10 subtests`; `compileall onto_mcp` passed with workspace-local cache prefix; `python -m pytest tests` passed `27 passed, 30 subtests`; real stdio MCP transport smoke passed after local FastMCP/pywin32 path setup and `FASTMCP_CHECK_FOR_UPDATES=off`. Plain `python -m pytest` remains blocked by existing stale `dev-scripts/test_search_objects.py` importing removed `onto_mcp.resources`. Status: implemented locally, not committed, not pushed, not deployed.
- `2026-06-05T16:00:28+03:00`: Fixed `get_entity(..., related_entities=true)` formatting so related entity ids/names and available relation metadata are visible instead of only a count. Live STDIO smoke passed on realm `000ba00a-00a0-0a00-a000-000a0a0a0aa3`, entity `123e2296-a62a-41bf-936e-1a12da6ce44b`. Next step: commit/PR when requested.
- `2026-05-29T00:00:00+03:00`: Added `add_existing_nodes_to_diagram` over the existing-node representation batch endpoint.
- `2026-05-26T00:00:00+03:00`: Added diagram discovery and context tag MCP tools, including read-modify-write diagram tag add/remove helpers.
- `2026-05-23T00:00:00+03:00`: Added `get_node_chat_messages` and `create_node_chat_message` over object/node chat endpoints.
- `2026-05-08T18:50:00Z`: Recorded repo-level scope constraint: agents in this repo should accept only MCP development, validation, operation, or deployment work.
- `2026-05-08T18:40:00Z`: Updated `search_entities_by_relations` to unwrap the production-ready search envelope, expose pagination/sort options, and pass wrapper tests.
- `2026-04-30T05:50:00Z`: QA for `search_entities_by_relations` passed on real `stdio MCP` against both the local backend fixture and a temporary preprod QA realm created and deleted during the run.
- `2026-04-30T13:30:00+03:00`: Added `search_entities_by_relations` over `POST /realm/{realmId}/entity/search` with local structural validation and wrapper tests.
- `2026-04-23T00:00:00Z`: Added HTTP Onto API key passthrough and removed the blanket session-state startup requirement.
