# Onto MCP Agent Entry Guide

<!-- generated-from: onto_mcp/agent_contract.json -->
<!-- contract-version: 2026-07-22.realm-agent-bootstrap-prefix -->
<!-- contract-tool-count: 63 -->

This guide is the human-readable rendering of the canonical MCP Agent Contract in `onto_mcp/agent_contract.json`.
The runtime-visible operational entrypoint is `how_to_use_onto_mcp(question="", safety_mode="read_only")`.

## Start Here
- If you only have MCP runtime access and only know the MCP tool list, call `how_to_use_onto_mcp` first.
- Put the user's actionable goal and known inputs in `question`.
- Keep `safety_mode` as `read_only` until required IDs and operator intent are explicit.
- Start realm-scoped work with `list_available_realms`.
- Use read-only search/get tools to obtain exact IDs before routing mutations.
- Use `about_onto` for semantic Onto orientation only; it is not the operational sequencing contract.

## Agent Response Envelope
`how_to_use_onto_mcp` returns an agent-shaped routing envelope:
- `answer`: short guidance for the current goal.
- `next_calls`: ordered concrete MCP calls. Each entry has `step`, `tool`, `purpose`, `params`, and `missing_args`.
- `clarifying_question`: present when required information must come from the user/operator.
- `avoid_tools`: tools that are not immediate next calls for the current inputs and safety mode.
- `safety_notes`: safety constraints the caller must preserve.

`missing_args` names only arguments obtainable by another MCP tool, for example `{"arg": "realm_id", "get_with_tool": "list_available_realms"}`.
Information that must come from the user belongs in `clarifying_question`, not `missing_args`.

## Safety Rules
- `read_only` must not put write, destructive, lifecycle, admin-like, or high-risk tools in `next_calls`.
- Search/list tools use canonical pagination `first=0`, `offset=100`: `first` is start/skip and `offset` is page size, not skip.
- Ordinary writes need exact IDs and `write_intent` before they can become immediate mutation calls.
- High-risk MemoryArtifact writes need owner-approved intent before they can become immediate mutation calls.
- Destructive and lifecycle tools require exact named IDs and explicit operator confirmation.
- A single bare UUID does not satisfy distinct required IDs such as `realm_id` and `diagram_id`.
- Unknown, ambiguous, or non-operational prompts stay on safe discovery or clarification only.

## Common Routes
- Realm-agent list: RU `Покажи список агентов пространства realm_id=<uuid>` or EN `List realm agents in realm_id=<uuid>` routes only to `list_realm_agents(realm_id)`.
- Realm-agent identity decision: RU `Проверь, может ли агент со slug=analyst загрузиться в realm_id=<uuid>` or EN `Can realm agent slug=analyst boot in realm_id=<uuid>?` routes only to `get_realm_agent(realm_id, slug)`.
- Realm-agent identity and charter: RU `Проверь slug=analyst и прочитай его чартер в realm_id=<uuid>` or the equivalent EN request routes to `get_realm_agent` and then a conditional accepted/current `get_memory_artifact_by_path(..., "realm/agents/analyst/charter")`.
- Realm-agent bootstrap prefix: a constitutional seed with exact `realm_id` and `my_slug`, or an equivalent RU/EN constitution + registry + identity + charter request, routes in order to accepted/current `realm/agents/constitution`, accepted/current `realm/agents/registry`, `get_realm_agent`, and the conditional exact charter read. `my_slug` maps to the existing `slug` tool argument; it is not an alias or fuzzy lookup.
- The charter read is conditional: continue only when `get_realm_agent` returns exactly `valid_active_resident` with `boot_allowed=true`. Every other result stops the identity-and-charter/bootstrap-prefix plan and is reported as a blocker.
- The four fixed calls yield only `bootstrap_prefix_complete`. After the accepted/current charter is read, follow its recovery list in order and restore working state from the role's own zone. If a required source is unavailable, forbidden, malformed, or conflicts with accepted/current governance, stop and report the blocker without substituting another source.
- `how_to_use_onto_mcp` does not inspect the charter, expand or execute its recovery list, restore working state, assemble an F-02 verified boot package, launch an F-03 executor, or grant authorization.
- Missing realm/slug values stay in `missing_args`; a selected realm-agent route does not add `list_available_realms` as another call. Malformed realm or slug and conflicting `my_slug`/`slug` fail closed with explicit input-error guidance and never produce an exact-agent or derived-charter claim.
- Do not substitute generic MemoryArtifact search or AgentMemory tools for realm-agent list/identity decisions. A lone explicit governance or charter `artifact_path` read remains a generic MemoryArtifact route rather than selecting realm-agent bootstrap guidance.
- Template management: `list_available_realms` -> `search_templates` -> `get_template`; avoid template writes/deletes until intent and IDs are explicit.
- Object search by name: `list_available_realms` -> `search_objects` and/or `search_entities`.
- Object search by field value such as INN/OGRN: `list_available_realms` -> `search_templates` -> `get_template` to obtain `field_id` -> `search_entities_by_fields` with `field_filters=[{"field_id":"<id from get_template>","value":"<exact value>"}]`, `first=0`, `offset=100`. `offset` is page size, not skip.
- Diagram update by name: `list_available_realms` -> `search_diagrams` -> `get_diagram`; avoid `update_diagram` until exact IDs and `write_intent`.
- Template deletion by name: `list_available_realms` -> `search_templates` -> `get_template`; avoid `delete_template` until exact IDs and explicit confirmation.
- MemoryArtifact read: `search_memory_artifacts` -> `get_memory_artifact` or `get_memory_artifact_by_path`; do not use `search_agent_memory` or `get_agent_memory_record` for MemoryArtifact records.
- MemoryArtifact path read: use `get_memory_artifact_by_path` for the current accepted artifact at a known path.
- MemoryArtifact target search: use `search_memory_artifacts`; for object/node ids use `target_kind=entity` with the object id as `target_id`.
- AgentMemory record read: use `search_agent_memory` -> `get_agent_memory_record` only for canonical agent-memory records, not MemoryArtifacts.
- MemoryArtifact owner-approved write/lifecycle: `create_memory_artifact_draft` -> `get_memory_artifact` -> `submit_memory_artifact` -> `accept_memory_artifact` -> `get_memory_artifact_by_path` or `search_memory_artifacts`.
- MemoryArtifact reviewable replace-mode successor: read the current accepted predecessor, then pass its exact UUID as optional `supersedes_artifact_id` to `create_memory_artifact_draft`; continue `create_memory_artifact_draft` -> `get_memory_artifact` -> `submit_memory_artifact` -> `accept_memory_artifact` -> accepted `get_memory_artifact_by_path` or `search_memory_artifacts` readback. Never substitute `supersede_memory_artifact`, which remains the distinct direct-to-accepted operation. Omit `supersedes_artifact_id` for an ordinary draft.
- MemoryArtifact `targets` input: pass a non-empty JSON array of objects, for example `[{"target_kind":"realm","target_id":"<realm UUID>","role":"primary"}]`. Allowed `target_kind` values are `realm`, `template`, `entity`, and `diagram`; `role` is optional and defaults to `primary`. Never pass the array as a JSON string. `targets` is required for create/supersede and optional for update, but an update that supplies it must use a non-empty array.
- Owner-approved single-object bug lifecycle/state reclassification: `get_entity` -> `save_entity` with the same `entity_id` and target `meta_entity_id`/`template_id` -> `get_entity`; do not ask for a different route when exact `realm_id`, `entity_id`, target classification id, and owner approval are known.
- Owner-approved safe defect creation under an existing bug template: `get_template` -> `save_entity` with `name`, `comment`, and `meta_entity_id`/`template_id` -> `get_entity`; do not create a new tool, endpoint, template, fallback, or compatibility path.

## Scope Guard
This tool routes Onto MCP work. It is not a glossary or general ontology Q&A tool.
For glossary prompts such as `what is ontology?` or an equivalent non-English wording, it should ask for an actionable MCP goal and should not provide an encyclopedia answer.

## Contract Coverage
Every registered MCP tool must have exactly one entry in `tool_contract`.
Tests compare `onto_mcp/api_resources.py` tool decorators, the JSON contract, and this guide's markers to prevent drift.
