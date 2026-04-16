# Onto MCP QA Tool Catalog

## Purpose
- This document is the detachable QA-facing description of the current MCP tool surface.
- It describes the logic that is implemented now, not the target future matrix.
- It is intended for smoke testing, regression testing, and semantic review.

## Runtime Rules
- Access model: config-driven `ONTO_API_KEY`.
- The server does not use login/password flows.
- Base mutation tools do not perform hidden preflight search or deduplication.
- `save_*` tools are direct wrappers over Onto upsert-style operations where the API already behaves that way.
- Compatibility wrappers may still exist for older names such as `create_template` and `create_entities_batch`, but the canonical mutation surface is the `save_*` layer.

## Global QA Notes
- All tools return human-readable summaries, not raw API payloads.
- Error handling is normalized into plain-text failures derived from HTTP status and response snippets.
- No mutation tool currently guarantees business-level idempotency beyond the underlying Onto API behavior.
- `save_entity` and `save_entities_batch` treat `meta_entity_id` as explicit caller input:
- if provided, Onto receives it as the desired classification
- if omitted, Onto may remove the current classification
- relation tools map directly onto Onto relation payloads; they do not add semantic safety checks beyond required parameter validation

## Tool Groups

### Documentation And Session Helpers

#### `about_onto(focus="")`
- Purpose: returns a packaged explanation of Onto in the style of the editorial `about.md`.
- Logic:
- without `focus`, returns the full text
- with supported `focus`, returns a narrowed text block
- with unsupported `focus`, returns a help message with allowed values
- QA focus:
- verify supported `focus` values return stable text
- verify unsupported values do not crash and return guidance

#### `saveOntoAIThreadID(thread_external_id, ctx)`
- Purpose: stores a thread identifier in session-state storage for the current MCP context.
- Logic:
- requires session-state configuration
- merges `threadExternalId` into existing session payload
- returns `contextId`, stored `threadExternalId`, and `createdAt`
- QA focus:
- verify configured and unconfigured behavior
- verify same context can overwrite stored value

#### `getOntoAIThreadID(ctx)`
- Purpose: returns the stored thread identifier for the current MCP context.
- Logic:
- requires session-state configuration
- reads session-state by MCP context id
- returns stored `threadExternalId` or a “not found” style message
- QA focus:
- verify retrieval after `saveOntoAIThreadID`
- verify empty-state behavior

### Discovery Tools

#### `list_available_realms()`
- Purpose: lists realms visible to the configured API key.
- Logic:
- reads current user data from Onto
- extracts `userRealmsRoles`
- formats realm name and realm id into a numbered list
- QA focus:
- verify all visible realms appear
- verify graceful failure when Onto user lookup fails

#### `search_templates(name_part, realm_id=None, include_children=False, include_parents=False)`
- Purpose: searches template/meta entities by partial name.
- Logic:
- resolves default realm when `realm_id` is omitted
- calls Onto `meta/find`
- formats matched items with name, id, and optional comment
- QA focus:
- verify default realm fallback
- verify empty results
- verify `include_children` and `include_parents` are passed through

#### `search_objects(realm_id=None, name_filter="", template_uuid="", comment_filter="", load_all=False, page_size=20)`
- Purpose: searches knowledge-base entities through the related-meta search endpoint.
- Logic:
- resolves default realm when `realm_id` is omitted
- calls Onto `entity/find/v2`
- uses Onto pagination semantics `first = start position`, `offset = page size`
- flattens nested `entities` blocks from the v2 response
- supports repeated pagination when `load_all=True`
- formats up to 50 results in the final summary
- QA focus:
- verify pagination behavior
- verify template filter by `template_uuid`
- verify response flattening on v2 payloads

### Realm Tools

#### `create_realm(name, comment="")`
- Purpose: creates a new realm.
- Logic:
- direct POST to Onto create realm endpoint
- no pre-check for duplicate names
- QA focus:
- verify successful creation
- verify API-side validation errors propagate cleanly

#### `update_realm(realm_id, name, comment="")`
- Purpose: updates an existing realm.
- Logic:
- direct PUT to Onto update realm endpoint
- returns normalized status/message summary
- QA focus:
- verify name/comment update
- verify invalid realm id handling

#### `delete_realm(realm_id)`
- Purpose: deletes a realm by id.
- Logic:
- direct DELETE to Onto delete realm endpoint
- returns normalized status/message summary
- QA focus:
- verify successful deletion path
- verify behavior for nonexistent realm ids

### Template Tools

#### `save_template(realm_id, name, comment="", template_id="")`
- Purpose: canonical template mutation tool.
- Logic:
- wraps Onto `saveMetaEntity`
- if `template_id` is omitted, caller intent is “create-like”
- if `template_id` is provided, caller intent is “update-like”
- no duplicate search is performed before save
- the confirmed template UUID is extracted from the backend `message` text because this is the current Onto API contract
- QA focus:
- verify create-like path without `template_id`
- verify update-like path with `template_id`
- verify no hidden dedup/reuse occurs

#### `create_template(realm_id, name, comment="")`
- Purpose: compatibility alias over `save_template`.
- Logic:
- simply calls `save_template` without `template_id`
- does not perform older pre-search logic anymore
- QA focus:
- verify it behaves exactly like `save_template(..., template_id="")`

#### `get_template(realm_id, template_id, include_children=False, include_parents=False, name="")`
- Purpose: reads one template/meta entity.
- Logic:
- calls Onto `getMetaEntity`
- passes `children`, `parents`, and optional `name`
- summarizes id, name, comment, describer-field count, and field count
- QA focus:
- verify child/parent flags are respected
- verify counts match raw Onto payload

#### `delete_template(realm_id, template_id)`
- Purpose: deletes a template/meta entity by id.
- Logic:
- calls Onto delete meta endpoint with `id` as query parameter
- returns normalized status/message summary
- QA focus:
- verify deletion works for existing template
- verify invalid id handling

#### `link_template_to_parents(realm_id, child_template_id, parent_template_ids)`
- Purpose: links one child template to one or more parent templates.
- Logic:
- passes `parentsUuids` as repeated query values
- no lookup or validation beyond non-empty ids
- QA focus:
- verify single-parent and multi-parent linking
- verify query serialization for multiple parents

#### `unlink_template_from_parents(realm_id, child_template_id, parent_template_ids)`
- Purpose: unlinks one child template from one or more parent templates.
- Logic:
- passes `parentsUuids` as repeated query values to the unlink endpoint
- no lookup or validation beyond non-empty ids
- QA focus:
- verify single-parent and multi-parent unlinking
- verify query serialization for multiple parents

### Entity Tools

#### `save_entity(realm_id, name, comment="", entity_id="", meta_entity_id="")`
- Purpose: canonical entity mutation tool.
- Logic:
- wraps Onto `saveEntity`
- if `entity_id` is omitted, caller intent is “create-like”
- if `entity_id` is provided, caller intent is “update-like”
- if `meta_entity_id` is provided, entity is saved with that classification
- if `meta_entity_id` is omitted, Onto may remove the current classification
- the confirmed entity UUID is extracted from the backend `message` text because this is the current Onto API contract
- this tool is the intended surface for ordinary update, declassification, and reclassification
- QA focus:
- verify create-like save
- verify update-like save
- verify reclassification when `meta_entity_id` changes
- verify declassification when `meta_entity_id` is omitted

#### `save_entities_batch(realm_id, entities)`
- Purpose: canonical batch entity mutation tool.
- Logic:
- wraps Onto `saveEntityBatch`
- each entity requires `name`
- canonical optional per-item fields: `id`, `comment`, `meta_entity_id`
- legacy alias `metaEntityId` is still accepted for backward compatibility
- if both `meta_entity_id` and `metaEntityId` are provided with different values, MCP rejects the item before the API call
- no pre-search or dedup
- current summary uses the API `createdEntities` response slot for all returned items
- QA focus:
- verify batch create
- verify batch update
- verify mixed batch create/update behavior
- verify `meta_entity_id` works as the canonical batch classification input
- verify response shape if Onto distinguishes created and updated entities separately

#### `create_entities_batch(realm_id, entities)`
- Purpose: compatibility alias over `save_entities_batch`.
- Logic:
- directly calls `save_entities_batch`
- QA focus:
- verify parity with canonical batch save behavior

#### `get_entity(realm_id, entity_id, related_diagrams=False, related_entities=False, with_empty_stickers=False, name="")`
- Purpose: reads one entity.
- Logic:
- calls Onto `getEntity`
- unwraps the entity object from top-level `result`
- supports optional related-diagram and related-entity expansion flags
- reads related payloads from Onto `related_diagrams` and `related_entities`
- summarizes id, name, comment, template, and field count
- QA focus:
- verify expansion flags affect returned data
- verify field count and relation counts

#### `search_entities(realm_id=None, name_filter="", meta_entity_id="", comment_filter="", include_inherited=False, offset=0, limit=20)`
- Purpose: searches entities through the plain entity search endpoint.
- Logic:
- resolves default realm if omitted
- calls Onto `entity/find`
- uses Onto pagination semantics `first = start position`, `offset = page size`
- formats matched entities with basic metadata
- QA focus:
- verify default realm fallback
- verify pagination values
- verify `include_inherited` pass-through

#### `search_entities_with_related_meta(realm_id=None, name_filter="", meta_entity_id="", comment_filter="", include_inherited=False, offset=0, limit=20)`
- Purpose: searches entities through the v2 endpoint with related-meta payload expansion.
- Logic:
- resolves default realm if omitted
- calls Onto `entity/find/v2`
- uses Onto pagination semantics `first = start position`, `offset = page size`
- flattens nested `entities`
- reports related field-map count when available
- QA focus:
- verify v2 result flattening
- verify field-map reporting

#### `delete_entity(realm_id, entity_ids, name="")`
- Purpose: deletes one or more entities.
- Logic:
- sends `ids` as repeated query parameters
- optional `name` is passed through when provided
- returns normalized status/message summary
- QA focus:
- verify single-id and multi-id deletion
- verify query serialization for repeated ids

### Field Tools

#### `save_entity_fields(realm_id, entity_id, fields)`
- Purpose: saves fields on an entity through the confirmed entity fields endpoint.
- Logic:
- wraps Onto `PATCH /entity/{entityId}/fields`
- each field requires `name`
- `metaFieldUuid` is optional and marks the field as template-derived
- the same tool covers ordinary entity fields and template-derived entity fields
- sends a raw list payload, not `{"fields": ...}`
- if `id` is omitted, MCP generates a client-side UUID before sending the request
- MCP injects `fieldTypeName="T_STRING"` internally, so callers do not need to provide it
- if a caller still provides `fieldTypeName`, only `T_STRING` is accepted
- QA focus:
- verify create/update for a plain entity field
- verify create/update for a field with `metaFieldUuid`
- verify backend acceptance of generated `id`, `value`, `comment`, and MCP-injected `T_STRING`

#### `delete_entity_fields(realm_id, entity_id, field_ids)`
- Purpose: deletes one or more fields from an entity.
- Logic:
- wraps Onto `DELETE /entity/{entityId}/fields`
- sends `fieldsUuids` as repeated query parameters
- QA focus:
- verify single-id and multi-id deletion
- verify query serialization for repeated `fieldsUuids`

#### `save_template_fields(realm_id, template_id, fields)`
- Purpose: saves fields on a template/meta entity through the v2 meta fields endpoint.
- Logic:
- wraps Onto `PATCH /meta/{templateId}/fields`
- each field requires `name`
- optional `uuid` is passed through for update-like saves
- optional `usableAsReference` is passed through as a boolean
- if `uuid` is omitted, MCP generates a client-side UUID before sending the request
- MCP injects `fieldTypeName="T_STRING"` internally, so callers do not need to provide it
- if a caller still provides `fieldTypeName`, only `T_STRING` is accepted
- QA focus:
- verify create/update for template fields
- verify backend acceptance of generated `uuid`, `comment`, `usableAsReference`, and MCP-injected `T_STRING`

#### `delete_template_fields(realm_id, template_id, field_ids)`
- Purpose: deletes one or more fields from a template/meta entity.
- Logic:
- wraps Onto `DELETE /meta/{templateId}/fields`
- sends `fieldsIds` as repeated query parameters
- QA focus:
- verify single-id and multi-id deletion
- verify query serialization for repeated `fieldsIds`

### Diagram Tools

#### `create_diagram(realm_id, name, comment="")`
- Purpose: creates a diagram in a realm.
- Logic:
- wraps Onto `POST /diagram/v2`
- uses query parameters `name` and `comment`
- returns a `DiagramInfo`-shaped summary with id, name, summary, and tag count when present
- QA focus:
- verify create succeeds with required `name`
- verify returned diagram id is usable for subsequent get/update/delete

#### `get_diagram(realm_id, diagram_id)`
- Purpose: loads a single diagram.
- Logic:
- wraps Onto `GET /diagram/v2/{diagramId}`
- summarizes top-level `diagram` metadata plus representation/link counts
- QA focus:
- verify id/name are preserved
- verify representation and link counts match the raw response

#### `update_diagram(realm_id, diagram_id, name="", comment="", tag_ids=None)`
- Purpose: updates diagram metadata.
- Logic:
- wraps Onto `PUT /diagram/v2/{diagramId}`
- accepts any non-empty subset of `name`, `comment`, `tag_ids`
- returns normalized status/message summary
- QA focus:
- verify name/comment update
- verify tag update when real tag ids are available
- verify empty update payload is rejected by MCP before the API call

#### `delete_diagram(realm_id, diagram_id)`
- Purpose: deletes a diagram by id.
- Logic:
- wraps Onto `DELETE /diagram/v2/{diagramId}`
- returns normalized status/message summary
- QA focus:
- verify delete succeeds for an existing diagram
- verify deleted diagram is no longer retrievable through the normal read path

### Relation Tools

#### `create_relation(realm_id, start_entity_id, end_entity_id, relation_type_name, start_role="", end_role="", additional_properties=None)`
- Purpose: creates a relation between two entities.
- Logic:
- builds Onto `EntityRelationDefinition`
- passes `startRelatedEntity`, `endRelatedEntity`, `type`
- optional `additional_properties` is forwarded as `additionalProperties`
- QA focus:
- verify basic relation creation
- verify create succeeds for the exact start/end/type triple
- verify whether `additional_properties` is accepted as implemented when relevant

#### `update_relation(realm_id, start_entity_id, end_entity_id, relation_type_name, start_role="", end_role="", additional_properties=None)`
- Purpose: updates an existing relation between two entities.
- Logic:
- same payload model as `create_relation`
- uses Onto update relation endpoint
- QA focus:
- verify update succeeds for the same start/end/type triple
- verify updates against an existing relation of the same type

#### `delete_relation(realm_id, start_entity_id, end_entity_id, relation_type_name, name="")`
- Purpose: deletes a relation between two entities.
- Logic:
- calls Onto delete relation endpoint via query parameters
- optional `name` is passed through
- QA focus:
- verify delete by exact start/end/type triple
- verify optional `name` behavior if Onto uses it

### Meta-Relation Tools

#### `create_meta_relation(realm_id, start_meta_id, end_meta_id, relation_type_name, start_min=0, start_max=1, end_min=0, end_max=1, equal=False)`
- Purpose: creates a relation between two template/meta nodes.
- Logic:
- builds Onto `MetaRelationDefinition`
- passes start/end cardinalities and relation type equality flag
- QA focus:
- verify create succeeds for the exact start/end/type triple

#### `update_meta_relation(realm_id, start_meta_id, end_meta_id, relation_type_name, start_min=0, start_max=1, end_min=0, end_max=1, equal=False)`
- Purpose: updates a relation between two template/meta nodes.
- Logic:
- same payload model as `create_meta_relation`
- uses Onto update meta relation endpoint
- QA focus:
- verify update succeeds for the same start/end/type triple

#### `delete_meta_relation(realm_id, start_meta_id, end_meta_id, relation_type_name)`
- Purpose: deletes a relation between two template/meta nodes.
- Logic:
- deletes by exact start meta, end meta, and relation type
- QA focus:
- verify delete by exact triple

## Current Matrix Coverage Status
- Covered now:
- realm create/update/delete
- template save/read/delete/link/unlink
- entity save/read/search/delete
- entity fields save/delete
- template fields save/delete
- diagrams create/read/update/delete
- entity relation create/update/delete
- meta relation create/update/delete
- session-state helpers
- documentation helper
- Not covered yet:
- no remaining matrix gaps in the base release surface

## Suggested QA Order
1. Read-only smoke: `list_available_realms`, `search_templates`, `search_entities`, `search_entities_with_related_meta`
2. Template lifecycle: `save_template`, `get_template`, `link_template_to_parents`, `delete_template`
3. Entity lifecycle: `save_entity`, `get_entity`, `save_entities_batch`, `delete_entity`
4. Reclassification path: `save_entity` with changed `meta_entity_id`
5. Declassification path: `save_entity` without `meta_entity_id`
6. Field lifecycle: `save_entity_fields`, `delete_entity_fields`, `save_template_fields`, `delete_template_fields`
7. Diagram lifecycle: `create_diagram`, `get_diagram`, `update_diagram`, `delete_diagram`
8. Relation lifecycle: `create_relation`, `update_relation`, `delete_relation`
9. Meta-relation lifecycle: `create_meta_relation`, `update_meta_relation`, `delete_meta_relation`

## Known Open Questions For QA
- Does Onto return mixed create/update batch results only in `createdEntities`, or are there separate fields not yet handled in summaries?
- Does entity relation `additionalProperties` require stricter normalization than a plain object passthrough?
- Should any read tool expose more raw payload detail for QA, or is the current summary layer sufficient?
