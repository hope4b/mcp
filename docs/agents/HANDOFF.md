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
4. Keep `docs/income/QA_MCP_TOOL_CATALOG.md` synchronized with the runtime tool surface if more optional diagram endpoints are added.

## Last Completed
- `2026-04-17T00:28:00Z`: Added the diagram MCP surface for create/read/update/delete.
