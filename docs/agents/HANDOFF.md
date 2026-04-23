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
1. Re-run the batch classification scenario with `meta_entity_id` inside batch items to confirm the contract-consistency fix.
2. Validate HTTP transport session-state helpers with a real `SESSION_STATE_API_KEY`.
3. Verify whether any relation `additional_properties` normalization is still required for the release surface.
4. Run a real MCP HTTP client probe for `X-Onto-Api-Key` passthrough and confirm the client preserves both custom headers and MCP session id across `initialize` and `tools/call`.
5. Re-run the live stdio smoke for `search_relation_templates` and confirm that top-level backend `name` now renders correctly in multi-result output.
6. Keep `docs/income/QA_MCP_TOOL_CATALOG.md` synchronized with the runtime tool surface if more optional endpoints are added.

## Last Completed
- `2026-04-23T00:00:00Z`: Added HTTP Onto API key passthrough and removed the blanket session-state startup requirement.
