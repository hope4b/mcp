# Decisions Log

## 2026-04-16 - Exclude Deprecated /meta/filtered From Public MCP Surface
- Status: Accepted
- Decision: Remove `list_templates` from the public MCP runtime because it depends on deprecated `/meta/filtered`.
- Reason: The template surface should not expose deprecated backend endpoints when equivalent active workflows already exist through search, read, save, link, and unlink operations.
- Consequences:
  - Template discovery stays centered on `search_templates`.
  - QA and future agents should not expect class-based template listing through deprecated filtered meta endpoints.

## 2026-04-16 - Use Onto Pagination Semantics For Entity Search
- Status: Accepted
- Decision: Entity search tools must treat Onto pagination as `first = start position` and `offset = page size`.
- Reason: Preprod validation provided a working payload shape `{\"pagination\":{\"first\":0,\"offset\":100}}` for fetching the first 100 entities, which is the inverse of the more common offset/limit interpretation.
- Consequences:
  - `search_entities`, `search_entities_with_related_meta`, and paginated object search must serialize pagination in Onto-native order.
  - QA should validate positive search paths against this contract before treating search as broken.

## 2026-04-16 - Treat saveMetaEntity Success Message As The Template ID Source
- Status: Accepted
- Decision: For the current Onto API contract, `saveMetaEntity` confirmation must be interpreted through the UUID embedded in the backend `message`, not through top-level `id/uuid` fields.
- Reason: Preprod validation showed the API returns `status/message` with the persisted UUID in `message`, and this is the intended backend shape for now.
- Consequences:
  - `save_template` extracts the confirmed template UUID from `message`.
  - QA and future agents should not expect a top-level `id` or `uuid` in the create response for template saves.

## 2026-04-16 - Treat saveEntity Success Message As The Entity ID Source
- Status: Accepted
- Decision: For the current Onto API contract, `saveEntity` confirmation must be interpreted through the UUID embedded in the backend `message`, not through top-level `id/uuid` fields.
- Reason: Preprod validation showed the API returns `status/message` with the persisted entity UUID in `message`, and downstream lifecycle steps depend on that identifier.
- Consequences:
  - `save_entity` extracts the confirmed entity UUID from `message`.
  - QA and future agents should not expect a top-level `id` or `uuid` in the create response for entity saves.

## 2026-04-16 - Treat saveEntity As The Canonical Entity Mutation Surface
- Status: Accepted
- Decision: Use `saveEntity` as the canonical MCP mutation surface for entity create/update, declassification, and reclassification instead of inventing a separate `changeMetaEntity` tool.
- Reason: In Onto, `saveEntity` already carries `metaEntityId` semantics, and changing or omitting that value is the real operational mechanism behind reclassification behavior.
- Consequences:
  - The runtime exposes `save_entity` and `save_entities_batch` rather than a separate classification-change tool.
  - Any agent updating an entity must treat `meta_entity_id` as an explicit part of the mutation contract.

## 2026-04-16 - Keep Base MCP Operations Explicit And Non-Idempotent By Search
- Status: Accepted
- Decision: Base-layer MCP mutation tools must not perform hidden preflight search or deduplication to simulate idempotent create semantics.
- Reason: Search-before-create is not atomic, introduces race conditions, and blurs the operational contract of Onto upsert endpoints such as `saveEntity` and `saveMetaEntity`.
- Consequences:
  - `save_template` and future `save_entity` remain direct wrappers over Onto upsert behavior.
  - Compatibility wrappers such as `create_template` should stay thin and must not add hidden reuse logic.

## 2026-04-16 - Use Onto API Key As Runtime Access Mechanism
- Status: Accepted
- Decision: The active MCP server runtime must access Onto API through a configured `ONTO_API_KEY`, not through interactive login/password or token exchange flows.
- Reason: The product requirement is configuration-driven service access, and user-auth flows are unnecessary for this server mode.
- Consequences:
  - Runtime MCP tools no longer include login/password auth helpers.
  - Legacy Keycloak modules are removed from the repository and no longer compete with the active runtime path.

## 2026-04-16 - Expose Static Onto Overview As MCP Tool
- Status: Accepted
- Decision: Add `about_onto` as a static MCP tool returning a canonical editorial description of Onto with optional focused variants.
- Reason: Agents need a stable and explicit way to explain Onto semantics without reconstructing them from scattered docs on each request.
- Consequences:
  - The runtime now includes a documentation-oriented tool alongside operational tools.
  - Editorial text changes require manual synchronization with the packaged content module.

## 2026-04-16 - Validate Runtime Settings At Server Start
- Status: Accepted
- Decision: Stop validating required environment variables at module import time and validate them when the server starts instead.
- Reason: Import-time failure prevents basic inspection, testing, and packaging workflows and makes the server feel broken before runtime even begins.
- Consequences:
  - `onto_mcp.server` can now be imported without env variables.
  - Startup still fails fast with a clear error when required runtime settings are missing.

## 2026-04-16 - Expose Implemented Auth Flows As MCP Tools
- Status: Accepted
- Decision: Register `login_via_token`, `get_keycloak_auth_url`, and `exchange_auth_code` as MCP tools because the underlying logic already exists in `keycloak_auth.py`.
- Reason: Documentation and code were out of sync, and these flows are part of the intended auth surface.
- Consequences:
  - The MCP contract now matches the implemented auth capabilities more closely.
  - `setup_auth_interactive` remains undocumented/deprecated until it actually exists.

## 2026-04-16 - Adopt Repository-Local Agent Context Files
- Status: Accepted
- Decision: Keep shared agent coordination state in versioned files under `docs/agents/` with a root `AGENTS.md` entrypoint.
- Reason: The repository currently lacks a durable handoff protocol, and future agent work needs a predictable read/update contract.
- Consequences:
  - Future tasks should update worklog and handoff metadata consistently.
  - Project-specific context must be maintained alongside code as the architecture evolves.
## 2026-04-16 - Use One Entity-Fields Surface With metaFieldUuid As The Template-Derived Signal
- Status: Accepted
- Decision: Expose a single `save_entity_fields` / `delete_entity_fields` surface for entity field mutations and use `metaFieldUuid` inside each field payload to distinguish template-derived fields.
- Reason: Onto uses the same entity fields endpoint and payload shape for ordinary entity fields and template-derived entity fields, with `metaFieldUuid` as the only semantic differentiator.
- Consequences:
  - The MCP runtime does not add separate wrapper tools for template-derived entity fields.
  - Template field mutations remain a separate surface through `save_template_fields` / `delete_template_fields`.
## 2026-04-17 - Prefer Confirmed Preprod Contract Over Stale OpenAPI For Template Field Saves
- Status: Accepted
- Decision: Use `PATCH /meta/{templateId}/fields` with a raw list payload for template field saves and treat `T_STRING` as the only confirmed `fieldTypeName`.
- Reason: Live preprod evidence showed the generated OpenAPI contract for template field saves was stale and did not match the accepted endpoint or payload semantics.
- Consequences:
  - `save_template_fields` no longer uses the `v2` meta fields endpoint or the wrapped `{"fields": ...}` payload.
  - QA should treat any other `fieldTypeName` as unsupported unless the backend contract is explicitly updated.

## 2026-04-17 - Prefer Confirmed Preprod Contract Over Stale OpenAPI For Entity Field Saves
- Status: Accepted
- Decision: Use `PATCH /entity/{entityId}/fields` with a raw list payload for entity field saves instead of the stale `v2` contract from OpenAPI.
- Reason: Live preprod evidence showed entity field saves are accepted on `/fields` with a raw list payload and return a status/message response.
- Consequences:
  - `save_entity_fields` no longer uses the `v2` entity fields endpoint or the wrapped `{"fields": ...}` payload.
  - QA should validate entity fields against the confirmed `/fields` path before treating any OpenAPI `v2` shape as authoritative.

## 2026-04-17 - Hardcode T_STRING As The Only Exposed MCP Field Type For Now
- Status: Accepted
- Decision: Treat `T_STRING` as the only supported `fieldTypeName` in both entity and template field save tools until Onto confirms additional field types.
- Reason: Live preprod evidence only confirms `T_STRING`, and exposing a broader field-type surface in MCP would advertise unsupported behavior.
- Consequences:
  - MCP field tools inject `fieldTypeName=T_STRING` even when the caller omits it.
  - Any other incoming `fieldTypeName` is rejected at the MCP layer as unsupported.

## 2026-04-17 - Generate Field UUIDs Client-Side When Save Payload Omits Them
- Status: Accepted
- Decision: Generate field identifiers in MCP for both entity fields and template fields when the caller omits `id` or `uuid`.
- Reason: Preprod evidence suggests the backend does not implicitly generate field ids for create requests, and field lifecycle operations depend on those identifiers existing from the start.
- Consequences:
  - `save_entity_fields` injects `id` when absent.
  - `save_template_fields` injects `uuid` when absent.
