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

#### `search_entities_by_relations(realm_id, searched_meta_ids, predicates=None, include_descendants=True, first=0, offset=100, sort=None)`
- Purpose: searches entities through the live relation-aware structural search endpoint.
- Logic:
- calls Onto `POST /realm/{realmId}/entity/search`
- requires `searched_meta_ids` and maps it to `searchedMetaIds`
- accepts optional flat `predicates`
- accepts `include_descendants` and maps it to `includeDescendants`
- accepts top-level pagination `first` and `offset`
- accepts optional `sort` items with `field` in `name | uuid` and `direction` in `asc | desc`
- maps `relation_type_names` to `relationTypeNames`
- maps `related_meta_ids` to `relatedMetaIds`
- maps `related_entity_ids` to `relatedEntityIds`
- rejects unsupported fields, nested predicates, public `direction`, and explicit boolean operators before the backend call
- unwraps the production backend page envelope `{items, total, first, offset}` while preserving older list responses
- mirrors backend validation limits: at most 20 `searched_meta_ids`, at most 10 predicates, at most 20 values per selector list, and `offset <= 500`
- preserves the accepted `v1` semantics: direct one-hop filtering, `AND` across predicates, `OR` inside list fields, and no business projections
- QA focus:
- verify root-only search
- verify relation type + concrete related entity filtering
- verify relation type + related meta filtering
- verify multiple predicates as `AND`
- verify list fields behave as `OR`
- verify invalid shapes are rejected before any Onto API call

### Agent Memory Tools

#### `search_agent_memory(realm_id, target_kind, target_id, memory_kind="", status="", reality="", author_id="", source_ref="", branch_id="", query="", first=0, offset=100)`
- Purpose: searches dedicated agent-memory records attached to an explicit target in a realm.
- Logic:
- calls only Onto `POST /realm/{realmId}/agent-memory/search`
- requires `realm_id`, `target_kind`, and `target_id`
- allows first-wave target kinds `realm`, `template`, `entity`, and `diagram`
- sends `memory_kind`, `status`, `reality`, `author_id`, `source_ref`, `branch_id`, and `query` only when supplied
- omitting `memory_kind` leaves backend search unconstrained by memory kind
- omitting `status` and `reality` sends no implicit lifecycle or reality filters
- passes backend-supported pagination as top-level `first` and `offset`
- renders compact search data and forces any returned search item `body` field to `null`
- does not call entity, template/meta, relation, diagram, search, or node-chat APIs
- QA focus:
- verify required-field validation before any backend call
- verify omitted optional filters are absent from the request body
- verify explicit filters are passed through using backend snake_case names
- verify mixed `memory_kind`, `status`, and `reality` records can appear when filters are omitted
- verify list/search includes `status` and `reality`
- verify list/search does not expose full `body`
- verify unsupported target kind and invalid UUIDs are rejected without fallback

#### `get_agent_memory_record(realm_id, record_id)`
- Purpose: reads one full canonical agent-memory record by id.
- Logic:
- calls only Onto `GET /realm/{realmId}/agent-memory/{recordId}`
- requires explicit `realm_id` and `record_id`
- returns the backend canonical record, including `body`
- does not call ordinary Onto APIs or object/node chat
- QA focus:
- verify the dedicated read-by-id route is used
- verify full `body` is visible in read-by-id output
- verify invalid or missing ids are rejected before any backend call

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

#### `get_node_chat_messages(realm_id, node_id)`
- Purpose: reads object/node chat messages attached to one node in a realm; this is not assistant chat.
- Logic:
- calls only Onto `GET /realm/{realmId}/chat/{nodeId}`
- rejects empty `realm_id` and `node_id` before any backend call
- formats each message with `id`, `text`, `timeStamp`, `my`, `user.userId`, `user.userName`, and `user.comment`
- returns an explicit empty result message when the backend returns an empty list
- does not call assistant chat endpoints and does not use fallback paths
- QA focus:
- verify exact GET endpoint mapping
- verify sender metadata appears in the output
- verify empty chat behavior

#### `create_node_chat_message(realm_id, node_id, text)`
- Purpose: appends a normal object/node chat message to one node in a realm; this is not assistant chat.
- Logic:
- calls only Onto `POST /realm/{realmId}/chat/{nodeId}`
- sends JSON body `{ "text": "<trimmed text>" }`
- rejects empty `realm_id`, `node_id`, and trimmed `text` before any backend call
- returns normalized backend status/message summary when present
- does not call assistant chat endpoints and does not use fallback paths
- QA focus:
- verify exact POST endpoint mapping and body
- verify a later `get_node_chat_messages` call can see the appended message
- verify empty text validation

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

#### `search_diagrams(realm_id, name_part="", tag_ids=None, page=1, size=20)`
- Purpose: lists, searches, and filters diagrams in a realm.
- Logic:
- wraps Onto `POST /diagram/v2/page/{page}/size/{size}`
- sends body `namePart` and `tags`
- requires positive 1-based `page` and positive `size`
- returns one requested page only; it does not auto-fetch all pages
- preserves page metadata and raw page data in the output
- tag filters use backend semantics, currently diagrams containing all requested tag ids
- QA focus:
- verify empty filters return a diagram page
- verify name filtering narrows results
- verify tag filtering uses exact backend endpoint/body
- verify invalid pagination and empty tag ids are rejected before the API call

#### `search_context_tags(realm_id, name_part="", page=1, size=20)`
- Purpose: lists and searches realm context tags assignable to diagrams.
- Logic:
- wraps Onto `GET /entity/tags/name/{namePart}/page/{page}/size/{size}`
- maps empty `name_part` to `*`
- URL-encodes non-empty name fragments for path safety
- requires positive 1-based `page` and positive `size`
- preserves page metadata and raw page data in the output
- QA focus:
- verify empty search sends `*`
- verify name search returns matching context tags
- verify invalid pagination is rejected before the API call

#### `create_context_tag_from_object(realm_id, entity_id)`
- Purpose: marks an existing object/entity as a realm context tag without creating a duplicate object.
- Logic:
- loads the existing entity through `GET /entity/{entityId}`
- reuses the existing entity id, name, comment, and template id
- calls `POST /entity` with `isTag=true`
- stops with an explicit error if name or template id cannot be loaded safely
- QA focus:
- verify the tool performs GET before POST
- verify POST body contains the same entity id and `isTag=true`
- verify no duplicate object is created

#### `add_diagram_tag(realm_id, diagram_id, tag_id)`
- Purpose: assigns a context tag to a diagram.
- Logic:
- uses read-modify-write over the full-replacement diagram update endpoint
- first loads the diagram through `GET /diagram/v2/{diagramId}`
- extracts existing tag ids from the returned diagram payload
- no-ops if the tag is already assigned
- otherwise calls `PUT /diagram/v2/{diagramId}` with existing name, existing summary/comment, and the full final tag id list
- QA focus:
- verify existing tags are preserved
- verify existing name/summary are preserved
- verify repeated add is idempotent

#### `remove_diagram_tag(realm_id, diagram_id, tag_id)`
- Purpose: removes a context tag from a diagram.
- Logic:
- uses read-modify-write over the full-replacement diagram update endpoint
- first loads the diagram through `GET /diagram/v2/{diagramId}`
- extracts existing tag ids from the returned diagram payload
- no-ops if the tag is absent
- otherwise calls `PUT /diagram/v2/{diagramId}` with existing name, existing summary/comment, and the full remaining tag id list
- QA focus:
- verify unrelated tags are preserved
- verify existing name/summary are preserved
- verify repeated remove is idempotent

#### `add_existing_nodes_to_diagram(realm_id, diagram_id, nodes)`
- Purpose: places existing Onto nodes on an existing diagram as visual representations with coordinates.
- Logic:
- wraps Onto `POST /diagram/v2/{diagramId}/representation/create/existing_nodes/batch`
- does not create new Onto objects and does not update diagram metadata, tags, or links
- accepts up to 20 nodes per backend batch
- maps each item from `existing_node_id`, `x`, `y`, and optional `type` to backend `existingNodeId`, `representation.type`, and `representation.coordinates`
- defaults omitted `type` to `ENTITY`
- supports v1 representation types `ENTITY`, `CLASS`, `TEMPLATE`, `TEMPLATE_ENTITY`, `NOTE`, and `IMAGE`
- preserves backend partial-success details in the output
- QA focus:
- verify payload mapping is camelCase and uses the existing-nodes batch endpoint
- verify successful and failed result details are visible
- verify empty realm/diagram ids, empty nodes, more than 20 nodes, missing node ids, non-numeric coordinates, and unsupported types are rejected before the API call
- verify `get_diagram` shows the expected representation count after placement

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

#### `search_relation_templates(realm_id, relation_type_name="", meta_ids=None)`
- Purpose: discovers relation templates through the read-only Onto discovery contract.
- Logic:
- calls `POST /realm/{realmId}/meta/relation/find`
- accepts three valid request shapes:
- `relation_type_name` only
- `relation_type_name` + `meta_ids` with one or two ids
- `meta_ids` only with one or two ids
- rejects requests with no filters
- rejects `meta_ids` lengths other than `1` or `2` before any backend call
- public semantics stay direction-agnostic and do not expose `start/end`
- QA focus:
- verify success for name-only discovery
- verify success for name + single meta id
- verify success for name + pair meta ids
- verify success for pair-only and single-meta-only discovery
- verify no-filter and `meta_ids > 2` validation paths
- verify output does not require caller-visible `start/end` reasoning

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
- diagrams search/create/read/update/delete and existing-node representation placement
- context tags search/create-from-object and diagram tag add/remove
- entity relation create/update/delete
- meta relation search/read-only discovery
- meta relation create/update/delete
- session-state helpers
- documentation helper
- Not covered yet:
- no remaining matrix gaps in the base release surface

## Suggested QA Order
1. Read-only smoke: `list_available_realms`, `search_templates`, `search_entities`, `search_entities_with_related_meta`, `search_entities_by_relations`
2. Template lifecycle: `save_template`, `get_template`, `link_template_to_parents`, `delete_template`
3. Entity lifecycle: `save_entity`, `get_entity`, `save_entities_batch`, `delete_entity`
4. Node chat lifecycle: `get_node_chat_messages`, `create_node_chat_message`, then `get_node_chat_messages` again for the same node
5. Reclassification path: `save_entity` with changed `meta_entity_id`
6. Declassification path: `save_entity` without `meta_entity_id`
7. Field lifecycle: `save_entity_fields`, `delete_entity_fields`, `save_template_fields`, `delete_template_fields`
8. Diagram search/tag lifecycle: `search_diagrams`, `search_context_tags`, `create_context_tag_from_object`, `add_diagram_tag`, `remove_diagram_tag`
9. Diagram representation placement: `add_existing_nodes_to_diagram`, then `get_diagram`
10. Diagram CRUD lifecycle: `create_diagram`, `get_diagram`, `update_diagram`, `delete_diagram`
11. Relation lifecycle: `create_relation`, `update_relation`, `delete_relation`
12. Meta-relation discovery and lifecycle: `search_relation_templates`, `create_meta_relation`, `update_meta_relation`, `delete_meta_relation`

## Known Open Questions For QA
- Does Onto return mixed create/update batch results only in `createdEntities`, or are there separate fields not yet handled in summaries?
- Does entity relation `additionalProperties` require stricter normalization than a plain object passthrough?
- Does live Onto discovery return any additional relation-template fields worth surfacing in the MCP summary beyond id, type name, comment, and participant ids?
- Should any read tool expose more raw payload detail for QA, or is the current summary layer sufficient?
