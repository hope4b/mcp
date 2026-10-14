# Onto MCP Server

FastMCP server for Onto platform access via a configured Onto API key.

## Runtime Contract

Required environment variables:
- all transports: `ONTO_API_BASE`
- stdio only: `ONTO_API_KEY`

Optional environment variables:
- `MCP_TRANSPORT` values: `stdio`, `http`
- `PORT`
- `SESSION_STATE_API_BASE`
- `SESSION_STATE_API_KEY`

The server no longer supports login/password, OAuth code exchange, or manual user token flows.

Public HTTP `/mcp` accepts either `X-API-Key` or the retained
`X-Onto-Api-Key`. Header names are ASCII case-insensitive, but values are
compared as untrimmed bytes. One occurrence is accepted. One occurrence of
each name is accepted only when the non-empty values are byte-identical.
Empty or SP/HTAB-only values, repeated fields, values containing a comma,
conflicting dual headers, and an API key combined with any Bearer
`Authorization` occurrence are rejected before MCP dispatch with a generic
response. Bearer-only authorization has no API-key semantics; OAuth remains a
separate contract.

An accepted HTTP credential is projected to Core as exactly one
`X-API-Key`. HTTP never falls back to server-side `ONTO_API_KEY`, and neither
`X-Onto-Api-Key` nor `Authorization` is projected as Core API-key
authentication. Stdio continues to require `ONTO_API_KEY` and projects it as
one `X-API-Key`. Header-name configuration does not alter this contract.
Credential values must not appear in responses, errors, logs, traces, or
metrics. This authentication bridge does not change MCP tool names, schemas,
protocol metadata, or result envelopes.

`SESSION_STATE_API_KEY` remains optional unless you use the session-state helper tools.

## Tools

- `how_to_use_onto_mcp(question="", safety_mode="read_only")`
- `list_available_realms()`
- `list_realm_agents(realm_id)`
- `get_realm_agent(realm_id, slug)`
- `preflight_realm_agent_governance_proposal(realm_id, proposal_artifact_id)`
- `admit_realm_agent(realm_id, candidate)`
- `about_onto(focus="")`
- `search_templates(name_part, realm_id=None, include_children=False, include_parents=False)`
- `search_relation_templates(realm_id, relation_type_name="", meta_ids=None)`
- `search_entities_by_relations(realm_id, searched_meta_ids, predicates=None, include_descendants=True, first=0, offset=100, sort=None)`
- `search_agent_memory(realm_id, target_kind, target_id, memory_kind="", status="", reality="", author_id="", source_ref="", branch_id="", query="", first=0, offset=100)`
- `get_agent_memory_record(realm_id, record_id)`
- `create_memory_artifact_draft(realm_id, artifact_path, artifact_kind, write_mode, body, summary, source_ref, source_context=None, review_destination=None, agent_principal="", targets=None)`
- `get_memory_artifact(realm_id, artifact_id)`
- `get_memory_artifact_by_path(realm_id, artifact_path)`
- `get_own_memory_artifact_draft_by_path(realm_id, artifact_path, agent_principal)`
- `search_memory_artifacts(realm_id, artifact_kind="", write_mode="", artifact_path="", review_destination="", target_kind="", target_id="", query="", first=0, offset=100)`
- `update_memory_artifact_draft(realm_id, artifact_id, body=None, summary=None, review_destination=None, agent_principal="", targets=None)`
- `append_memory_artifact(realm_id, artifact_id, body, source_ref, summary="", source_context=None, agent_principal="")`
- `submit_memory_artifact(realm_id, artifact_id)`
- `accept_memory_artifact(realm_id, artifact_id)`
- `revoke_memory_artifact(realm_id, artifact_id)`
- `supersede_memory_artifact(realm_id, artifact_id, artifact_path, artifact_kind, write_mode, body, summary, source_ref, source_context=None, review_destination=None, agent_principal="", targets=None)`
- `search_objects(realm_id=None, name_filter="", template_uuid="", comment_filter="", load_all=False, first=0, offset=100)`
- `create_realm(name, comment="")`
- `update_realm(realm_id, name, comment="")`
- `delete_realm(realm_id)`
- `save_template(realm_id, name, comment="", template_id="")`
- `create_template(realm_id, name, comment="")`
- `get_template(realm_id, template_id, include_children=False, include_parents=False, name="")`
- `delete_template(realm_id, template_id)`
- `link_template_to_parents(realm_id, child_template_id, parent_template_ids)`
- `unlink_template_from_parents(realm_id, child_template_id, parent_template_ids)`
- `save_entity(realm_id, name, comment="", entity_id="", meta_entity_id="")`
- `save_entities_batch(realm_id, entities)`
- `create_entities_batch(realm_id, entities)`
- `get_entity(realm_id, entity_id, related_diagrams=False, related_entities=False, with_empty_stickers=False, name="")`
- `get_node_chat_messages(realm_id, node_id)`
- `create_node_chat_message(realm_id, node_id, text)`
- `search_entities(realm_id=None, name_filter="", meta_entity_id="", comment_filter="", include_inherited=False, first=0, offset=100)`
- `search_entities_by_fields(realm_id, field_filters, meta_entity_id="", name_filter="", comment_filter="", first=0, offset=100)`
- `search_entities_with_related_meta(realm_id=None, name_filter="", meta_entity_id="", comment_filter="", include_inherited=False, first=0, offset=100)`
- `delete_entity(realm_id, entity_ids, name="")`
- `save_entity_fields(realm_id, entity_id, fields)`
- `delete_entity_fields(realm_id, entity_id, field_ids)`
- `save_template_fields(realm_id, template_id, fields)`
- `delete_template_fields(realm_id, template_id, field_ids)`
- `search_diagrams(realm_id, name_part="", tag_ids=None, first=0, offset=100)`
- `search_context_tags(realm_id, name_part="", first=0, offset=100)`
- `create_context_tag_from_object(realm_id, entity_id)`
- `add_diagram_tag(realm_id, diagram_id, tag_id)`
- `remove_diagram_tag(realm_id, diagram_id, tag_id)`
- `add_existing_nodes_to_diagram(realm_id, diagram_id, nodes)`
- `create_diagram(realm_id, name, comment="")`
- `get_diagram(realm_id, diagram_id)`
- `update_diagram(realm_id, diagram_id, name="", comment="", tag_ids=None)`
- `delete_diagram(realm_id, diagram_id)`
- `create_relation(realm_id, start_entity_id, end_entity_id, relation_type_name, start_role="", end_role="", additional_properties=None)`
- `update_relation(realm_id, start_entity_id, end_entity_id, relation_type_name, start_role="", end_role="", additional_properties=None)`
- `delete_relation(realm_id, start_entity_id, end_entity_id, relation_type_name, name="")`
- `create_meta_relation(realm_id, start_meta_id, end_meta_id, relation_type_name, start_min=0, start_max=1, end_min=0, end_max=1, equal=False)`
- `update_meta_relation(realm_id, start_meta_id, end_meta_id, relation_type_name, start_min=0, start_max=1, end_min=0, end_max=1, equal=False)`
- `delete_meta_relation(realm_id, start_meta_id, end_meta_id, relation_type_name)`
- `saveOntoAIThreadID(thread_external_id, ctx)`
- `getOntoAIThreadID(ctx)`

Agent operational guidance is defined by the canonical machine-readable contract
in `onto_mcp/agent_contract.json`, exposed at runtime through
`how_to_use_onto_mcp`, and summarized for humans in `docs/AGENT_ENTRY_GUIDE.md`.

Realm-agent Constitution, charter, and registry proposals use the read-only preflight twice:
after submit and before any approval sheet or position, then again immediately
before accept. The proposal must carry the submit-time registry id in
`source_context.realm_agent_governance_submit`. A pass validates structure,
exact body bytes, predecessor and frozen-electorate evidence only; it does not
count votes or authorize acceptance.

Owner-driven v2 resident admission uses exactly one high-risk tool:
`admit_realm_agent(realm_id, candidate)`. It sends the bare recursively closed
candidate to `POST /realm/{realmId}/agent-population/admissions` with the
ambient owner credential. The tool has no admission preflight, `confirm`
argument, client-supplied fingerprint, generic MemoryArtifact lifecycle chain,
or alternate route. If a sent request has no valid received response, the tool
returns `outcome_unknown`; recovery is the same exact admission call with the
same candidate.

## Resources

- `onto://spaces`
- `onto://user/info`

## Configuration Example

```json
{
  "mcpServers": {
    "onto-mcp-server": {
      "command": "python",
      "args": ["-m", "onto_mcp.server"],
      "cwd": "/path/to/repo",
      "env": {
        "ONTO_API_BASE": "https://app.ontonet.ru/api/v2/core",
        "ONTO_API_KEY": "replace-with-onto-api-key"
      }
    }
  }
}
```

## Running

```bash
python -m pip install -r requirements.txt
python -m onto_mcp.server
```

HTTP mode:

```bash
MCP_TRANSPORT=http PORT=8080 python -m onto_mcp.server
```

HTTP clients must send either `X-API-Key` or `X-Onto-Api-Key` on `/mcp`.
`SESSION_STATE_API_KEY` is required only when session-state helpers are used.

Before an owner manual Claude PREPROD check, `qa-agent` must verify through
the unchanged `mcp-server` contour: forwarding and normalization for both API
key headers and `Authorization`; duplicate/comma fail-closed behavior;
credential redaction in ingress, runtime, traces, and metrics; legacy-header
compatibility and the negative credential matrix; and exact correspondence
between the eventual owner-approved candidate source, built image digest,
deployed digest, FastMCP version, and target. Revision
`636577f6375bf4aa3c910ff821bb4083e5c71857` is only the pre-change
tool-contract comparison baseline. Automated evidence and verdict belong in
the QA MemoryArtifact. Only after a positive verdict may the owner run the
manual Claude check, recorded separately only as `проверка прошла` or
`проверка не прошла`.
