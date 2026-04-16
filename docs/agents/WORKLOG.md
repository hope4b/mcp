# Worklog

Append-only log. Newest entries on top.

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
