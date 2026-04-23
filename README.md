# Onto MCP Server

FastMCP server for Onto platform access via a configured Onto API key.

## Runtime Contract

Required environment variables:
- `ONTO_API_BASE`
- `ONTO_API_KEY`

Optional environment variables:
- `ONTO_API_KEY_HEADER` default: `X-API-Key`
- `ONTO_API_KEY_PASSTHROUGH_HEADER` default: `X-Onto-Api-Key`
- `MCP_TRANSPORT` values: `stdio`, `http`
- `PORT`
- `SESSION_STATE_API_BASE`
- `SESSION_STATE_API_KEY`

The server no longer supports login/password, OAuth code exchange, or manual user token flows.

In HTTP mode, Onto backend authentication can come from either:
- server-side `ONTO_API_KEY`
- incoming request header `X-Onto-Api-Key` (or the value of `ONTO_API_KEY_PASSTHROUGH_HEADER`)

`SESSION_STATE_API_KEY` remains optional unless you use the session-state helper tools.

## Tools

- `list_available_realms()`
- `about_onto(focus="")`
- `search_templates(name_part, realm_id=None, include_children=False, include_parents=False)`
- `search_relation_templates(realm_id, relation_type_name="", meta_ids=None)`
- `search_objects(realm_id=None, name_filter="", template_uuid="", comment_filter="", load_all=False, page_size=20)`
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
- `search_entities(realm_id=None, name_filter="", meta_entity_id="", comment_filter="", include_inherited=False, offset=0, limit=20)`
- `search_entities_with_related_meta(realm_id=None, name_filter="", meta_entity_id="", comment_filter="", include_inherited=False, offset=0, limit=20)`
- `delete_entity(realm_id, entity_ids, name="")`
- `save_entity_fields(realm_id, entity_id, fields)`
- `delete_entity_fields(realm_id, entity_id, field_ids)`
- `save_template_fields(realm_id, template_id, fields)`
- `delete_template_fields(realm_id, template_id, field_ids)`
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

If you use HTTP mode or session-state helpers, also configure `SESSION_STATE_API_KEY`.
