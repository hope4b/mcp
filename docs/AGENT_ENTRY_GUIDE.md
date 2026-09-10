# Onto MCP Agent Entry Guide

<!-- generated-from: onto_mcp/agent_contract.json -->
<!-- contract-version: 2026-09-10.existing-link-unordered-pair -->
<!-- contract-tool-count: 66 -->

This guide is the human-readable rendering of the canonical MCP Agent Contract in `onto_mcp/agent_contract.json`.
The runtime-visible operational entrypoint is `how_to_use_onto_mcp(question="", safety_mode="read_only")`.

## Start Here
- If you only have MCP runtime access and only know the MCP tool list, call `how_to_use_onto_mcp` first.
- Put the user's actionable goal and known inputs in `question`.
- Keep `safety_mode` as `read_only` until required IDs and operator intent are explicit.
- Start realm-scoped work with `list_available_realms`.
- Use read-only search/get tools to obtain exact IDs before routing mutations.
- Use `about_onto` for the global Onto explanation. Use `about_realm(realm_id)` for one concrete realm's exact accepted/current declaration. Neither is the operational sequencing contract.

## Agent Response Envelope
`how_to_use_onto_mcp` returns an agent-shaped routing envelope:
- `answer`: short guidance for the current goal.
- `next_calls`: ordered concrete MCP calls. Each entry has `step`, `tool`, `purpose`, `params`, and `missing_args`.
- `clarifying_question`: present when required information must come from the user/operator.
- `avoid_tools`: tools that are not immediate next calls for the current inputs and safety mode.
- `safety_notes`: safety constraints the caller must preserve.

`missing_args` names arguments obtained from a registered MCP tool or a documented stable non-callable dependency source, for example `{"arg": "realm_id", "get_with_tool": "list_available_realms"}`.
Information that must come from the user belongs in `clarifying_question`, not `missing_args`.

## Safety Rules
- `read_only` must not put write, destructive, lifecycle, admin-like, or high-risk tools in `next_calls`.
- Search/list tools use canonical pagination `first=0`, `offset=100`: `first` is start/skip and `offset` is page size, not skip.
- Ordinary writes need exact IDs and `write_intent` before they can become immediate mutation calls.
- High-risk tools need owner-approved intent before they can become immediate mutation calls.
- Destructive and lifecycle tools require exact named IDs and explicit operator confirmation.
- A single bare UUID does not satisfy distinct required IDs such as `realm_id` and `diagram_id`.
- Unknown, ambiguous, or non-operational prompts stay on safe discovery or clarification only.

## Common Routes
- Global Onto description: RU `Расскажи об Онто` or EN `Tell me about Onto` routes only to `about_onto`.
- Concrete realm description with a known id: RU `Расскажи о пространстве realm_id=<uuid>` or EN `Tell me about this realm realm_id=<uuid>` routes only to `about_realm(realm_id)`. Without `realm_id`, route exactly `list_available_realms` -> `about_realm`, with the selected id as the second call's explicit dependency. Do not broaden either sequence into template, entity, diagram, memory, workspace, or global Onto exploration.
- If `about_realm` returns `declaration_not_found`, report that the realm has no published declaration and stop. This outcome is terminal: do not call `about_onto`, search another path, inspect generic memory, create/submit/accept/revoke a probe artifact, update the realm comment, or infer a fallback.
- Explicit initial publication of `realm/declaration` selects publication guidance. The exact eight-call skeleton is emitted atomically only with `safety_mode=lifecycle_intent`, exactly one canonical lowercase hyphenated `realm_id`, and observed `about_realm -> declaration_not_found` initial-state evidence: (1) `create_memory_artifact_draft`; (2) `get_memory_artifact` for the same id and require `draft` plus exact fields/body and expected body SHA; (3) `submit_memory_artifact` for that id; (4) `get_memory_artifact` and require `proposed` plus unchanged fields/body/SHA; (5) `accept_memory_artifact` for that id; (6) `get_memory_artifact` and require `accepted` plus unchanged fields/body/SHA; (7) `get_memory_artifact_by_path(realm/declaration)` and require the same accepted/current artifact id and exact body/SHA; (8) `about_realm(same realm_id)` and require `accepted_current` with the exact body/body SHA. A missing or conflicting eligibility condition yields zero calls, no partial prefix, and an exact clarification while keeping the publication route selected.
- Step 1 places only known/fixed `realm_id`, `artifact_path=realm/declaration`, `artifact_kind=decision`, and `write_mode=replace` in `params`. Its exact ordered `missing_args` are `body`, `summary`, `source_ref`, `review_destination`, and `targets`, each with `get_with_tool=approved_constitutional_steward_package`. That label is a stable non-callable dependency source, not an MCP tool. Steps 2–6 source `artifact_id` from `create_memory_artifact_draft`. Initial publication omits `supersedes_artifact_id`.
- The approved Constitutional Steward package and authority are prerequisites for execution, not textual conditions for receiving guidance. `how_to_use_onto_mcp` never extracts, parses, transports, reconstructs, canonicalizes, hashes, or validates declaration JSON or business payload fields from `question`; embedded payload, envelope, or approval assertions neither affect eligibility nor satisfy the five package dependencies. The authorized executor supplies those values directly to step 1, where the create route/backend enforces the declaration contract.
- The declaration draft must use `realm_id=<canonical lowercase hyphenated UUID>`, `artifact_path=realm/declaration`, `artifact_kind=decision`, `write_mode=replace`, `body=<JSON string value containing the canonical payload below>`, nonempty `summary` and `source_ref`, `review_destination=<exact destination from the approved package>`, and exactly one real array target (not a JSON-encoded string): `[{"target_kind":"realm","target_id":"<same realm_id>","role":"primary"}]`.
- The decoded `body` top-level object is closed and has exactly the required keys `declaration_contract_id`, `declaration_contract_version`, `realm_id`, `purpose`, `boundaries`, and `routes`. The id is exactly string `realm_declaration`; the version is integer `1`, never string `"1"`; embedded `realm_id` is the same canonical lowercase hyphenated UUID as the outer call and sole target; `purpose` is a nonempty string; `boundaries` is a nonempty ordered array of unique nonempty strings; and `routes` is a nonempty ordered array of closed objects.
- Every route has exactly required nonempty strings `need`, `tool_entry_point`, `authoritative_result`, and `stop_condition`, plus optional nonempty string `next_discovery_step`; omit that optional key rather than setting it to null. Undeclared fields and duplicate JSON keys are forbidden.
- Build `body` as a structured object such as `{"declaration_contract_id":"realm_declaration","declaration_contract_version":1,"realm_id":"<same realm_id>","purpose":"<nonempty>","boundaries":["<nonempty unique boundary>"],"routes":[{"need":"<nonempty>","tool_entry_point":"<nonempty>","authoritative_result":"<nonempty>","stop_condition":"<nonempty>"}]}`, serialize/canonicalize it once with RFC 8785 JSON Canonicalization Scheme, encode that exact result as UTF-8 without BOM or trailing LF, require at most 65,536 exact bytes inclusive, hash those exact bytes, and pass the exact resulting JSON text as the tool's `body` string. Do not hand-compose or normalize it after hashing.
- Initial publication omits `supersedes_artifact_id`. A successor supplies the exact accepted/current predecessor as `supersedes_artifact_id` only to `create_memory_artifact_draft`. Any failed or ambiguous read-back stops without replay, fallback, or a second candidate; recovery remains package-bound. Never use `update_realm` or an arbitrary/probe MemoryArtifact as a substitute.
- `about_realm` resolves only exact accepted/current `realm/declaration`; it does not interpret or execute routes, select or boot residents, authorize calls, or create/enforce runs. Local agent configuration and local files do not change this capability.
- Realm-agent list: RU `Покажи список агентов пространства realm_id=<uuid>` or EN `List realm agents in realm_id=<uuid>` routes only to `list_realm_agents(realm_id)`.
- Realm-agent identity decision: RU `Проверь, может ли агент со slug=analyst загрузиться в realm_id=<uuid>` or EN `Can realm agent slug=analyst boot in realm_id=<uuid>?` routes only to `get_realm_agent(realm_id, slug)`.
- Realm-agent identity and charter: RU `Проверь slug=analyst и прочитай его чартер в realm_id=<uuid>` or the equivalent EN request routes to `get_realm_agent` and then a conditional accepted/current `get_memory_artifact_by_path(..., "realm/agents/analyst/charter")`.
- Realm-agent bootstrap prefix: a constitutional seed with exact `realm_id` and `my_slug`, or an equivalent RU/EN constitution + registry + identity + charter request, routes in order to accepted/current `realm/agents/constitution`, accepted/current `realm/agents/registry`, `get_realm_agent`, and the conditional exact charter read. `my_slug` maps to the existing `slug` tool argument; it is not an alias or fuzzy lookup.
- The charter read is conditional: continue only when `get_realm_agent` returns exactly `valid_active_resident` with `boot_allowed=true`. Every other result stops the identity-and-charter/bootstrap-prefix plan and is reported as a blocker.
- The four fixed calls yield only `bootstrap_prefix_complete`. After the accepted/current charter is read, follow its recovery list in order and restore working state from the role's own zone. If a required source is unavailable, forbidden, malformed, or conflicts with accepted/current governance, stop and report the blocker without substituting another source.
- `how_to_use_onto_mcp` does not inspect the charter, expand or execute its recovery list, restore working state, assemble an F-02 verified boot package, launch an F-03 executor, or grant authorization.
- Missing realm/slug values stay in `missing_args`; a selected realm-agent route does not add `list_available_realms` as another call. Malformed realm or slug and conflicting `my_slug`/`slug` fail closed with explicit input-error guidance and never produce an exact-agent or derived-charter claim.
- Do not substitute generic MemoryArtifact search or AgentMemory tools for realm-agent list/identity decisions. A lone explicit governance or charter `artifact_path` read remains a generic MemoryArtifact route rather than selecting realm-agent bootstrap guidance.
- Realm-agent governance proposal preflight: after submitting an exact Constitution, charter, or registry proposal, call `preflight_realm_agent_governance_proposal(realm_id, proposal_artifact_id)` before creating its approval sheet or collecting positions; repeat the same call immediately before accept and compare the exact proposal id, path, body hash, predecessor and submit-time electorate evidence with the sheet. A pass is structural only: it does not count votes, certify consensus or authorize acceptance.
- Owner-driven realm-agent admission: an explicit owner instruction such as RU `проверь и зарегистрируй` or EN `admit this realm agent` routes in `write_intent` to exactly one high-risk call, `admit_realm_agent(realm_id, candidate)`. Pass the complete recursively closed candidate with matching inner/outer `realm_id`. Do not add an admission preflight, `confirm`, client fingerprint, generic lifecycle chain, compatibility path, or second tool. On `outcome_unknown`, retry only the same exact candidate as directed by `retry_exact_admission`.
- Template management: `list_available_realms` -> `search_templates` -> `get_template`; avoid template writes/deletes until intent and IDs are explicit.
- Object search by name: `list_available_realms` -> `search_objects` and/or `search_entities`.
- Object search by field value such as INN/OGRN: `list_available_realms` -> `search_templates` -> `get_template` to obtain `field_id` -> `search_entities_by_fields` with `field_filters=[{"field_id":"<id from get_template>","value":"<exact value>"}]`, `first=0`, `offset=100`. `offset` is page size, not skip.
- Diagram update by name: `list_available_realms` -> `search_diagrams` -> `get_diagram`; avoid `update_diagram` until exact IDs and `write_intent`.
- Existing-link representation: with exact `realm_id`, `diagram_id`, `start_representation_id`, `end_representation_id`, and `onto_nodes_link_type_name`, use `create_existing_link_representation` in `write_intent`. It makes one POST to the canonical diagram endpoint, and the backend may create the subject relation when it is absent.
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
