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
1. Commit and open PR for `fix/get-entity-related-details` when requested.
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
- `2026-06-05T16:00:28+03:00`: Fixed `get_entity(..., related_entities=true)` formatting so related entity ids/names and available relation metadata are visible instead of only a count. Live STDIO smoke passed on realm `000ba00a-00a0-0a00-a000-000a0a0a0aa3`, entity `123e2296-a62a-41bf-936e-1a12da6ce44b`. Next step: commit/PR when requested.
- `2026-05-29T00:00:00+03:00`: Added `add_existing_nodes_to_diagram` over the existing-node representation batch endpoint.
- `2026-05-26T00:00:00+03:00`: Added diagram discovery and context tag MCP tools, including read-modify-write diagram tag add/remove helpers.
- `2026-05-23T00:00:00+03:00`: Added `get_node_chat_messages` and `create_node_chat_message` over object/node chat endpoints.
- `2026-05-08T18:50:00Z`: Recorded repo-level scope constraint: agents in this repo should accept only MCP development, validation, operation, or deployment work.
- `2026-05-08T18:40:00Z`: Updated `search_entities_by_relations` to unwrap the production-ready search envelope, expose pagination/sort options, and pass wrapper tests.
- `2026-04-30T05:50:00Z`: QA for `search_entities_by_relations` passed on real `stdio MCP` against both the local backend fixture and a temporary preprod QA realm created and deleted during the run.
- `2026-04-30T13:30:00+03:00`: Added `search_entities_by_relations` over `POST /realm/{realmId}/entity/search` with local structural validation and wrapper tests.
- `2026-04-23T00:00:00Z`: Added HTTP Onto API key passthrough and removed the blanket session-state startup requirement.
