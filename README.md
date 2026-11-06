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

## Optional delegated OAuth over HTTP

OAuth is disabled by default (`ONTO_OAUTH_ENABLED=false`). API-key HTTP and
`stdio` (`ONTO_API_KEY` -> `X-API-Key`) remain supported. An enabled HTTP server
accepts keys and multiple configured OAuth clients concurrently. OAuth failures
never substitute a configured key, a session-state key, or a service identity.

Enabled OAuth requires these operator-supplied settings:

| Setting | Meaning |
| --- | --- |
| `ONTO_OAUTH_ISSUER` | Exact absolute HTTPS issuer URL |
| `ONTO_OAUTH_RESOURCE` | Absolute HTTPS public resource URL with path `/mcp` |
| `ONTO_OAUTH_AUDIENCE` | Fixed ingress access-token audience; may equal the resource URL |
| `ONTO_OAUTH_ALLOWED_CLIENT_IDS` | JSON array of distinct nonempty external registration IDs |
| `ONTO_OAUTH_EXCHANGE_CLIENT_ID` | Confidential subject-preserving exchange registration, excluded from ingress allowlisting |
| `ONTO_OAUTH_EXCHANGE_CLIENT_SECRET` | Exchange registration secret; keep in the environment secret store |
| `ONTO_OAUTH_CORE_AUDIENCE` | Configured technical Core target client/audience |
| `ONTO_OAUTH_STATE_MONGO_URI` | Secret authenticated MongoDB URI; verified TLS is mandatory |
| `ONTO_OAUTH_STATE_MONGO_DB` | Database name, default `onto_mcp` |
| `ONTO_OAUTH_STATE_MONGO_COLLECTION` | Collection name, default `oauth_sessions` |

Set `ONTO_OAUTH_ENABLED=true` only after the authorization and state owners have
verified the delivery prerequisites. Invalid enabled identity configuration fails
startup with a secret-free error. Discovery at
`/.well-known/oauth-protected-resource/mcp` advertises the configured resource,
issuer, and `onto.mcp.read` / `onto.mcp.write` scopes; request headers cannot
choose these values. Verification permits RS256 signatures from the configured
issuer's discovered same-origin HTTPS JWKS. Provider requests have finite
timeouts and do not follow redirects.

Original access tokens undergo strict signed-claim validation and fresh
introspection on protected calls, resources, helpers and final Core sends.
Read and separately consented write scopes do not replace Core permissions.
Core requests use only a subject-preserving exchanged Bearer token at the
configured Core origin. Tokens with `act`, any selected impersonation marker,
non-Bearer payload types or `offline_access` are denied. Absence of markers is
not proof of human provenance: the represented issuance/mapping prerequisites
remain essential. No external-client refresh token is held by MCP.

The non-secret authorization deliverable is
`onto_mcp.oauth_policy.represented_policy(config)`. It resolves all allowed
external client IDs and the Core target from the supplied configuration rather
than example names. External registrations retain explicit consent, S256,
300-second access tokens, 30-minute idle / eight-hour maximum sessions, no
service accounts/password/implicit flows, no offline grants and no impersonation
or exchange authority. The three nonoptional stock `UserSessionNoteMapper`
mappings preserve `IMPERSONATOR_ID`, `IMPERSONATOR_USERNAME` and
`IMPERSONATOR_CLIENT` in access tokens and introspection. Outstanding grants from
earlier unrestricted configurations must be invalidated before admission.
Each external registration still needs its actual callbacks and authentication.
For the Core target C, set `consentRequired=false`; user consent belongs on the
external registrations. The deliverable is a configuration contract, not a live
provider validator, an import-ready realm replacement or evidence of deployment.

The separately authorized database owner provisions one MongoDB collection and
its strict validator and indexes before OAuth startup. Runtime never creates or
modifies collections, indexes, users or roles. Required document fields are `_id`
(43-character base64url session ID), `owner_key` (64-character SHA-256 hex),
`initialized_at`, `expires_at`, `purge_at` (BSON dates), `thread_external_id`
(string/null), `created_at` (date/null) and `revision` (nonnegative integer).
Reject additional fields. Provision `_id_`, `oauth_sessions_owner` on
`{owner_key: 1}`, and `oauth_sessions_purge_ttl` on `{purge_at: 1}` with
`expireAfterSeconds: 0`; startup checks these indexes using read-only metadata.
The collection validator is an operator prerequisite; runtime does not require
permission to inspect or modify it.

The runtime principal needs only `find`, `insert`, `update`, `remove` and
`listIndexes` on that collection. Use authenticated SCRAM credentials in the
secret URI, with the correct `authSource`. Runtime enforces verified TLS, primary
reads and acknowledged journaled writes (`w=1`, `j=true`), disables retryable
writes for standalone MongoDB, and bounds selection/connect/socket waits to
10 seconds. No replica set or multi-document transaction is required. A private
CA can be supplied using the URI's `tlsCAFile` path and a read-only mounted CA.
Insecure TLS options, plaintext connections and the former PostgreSQL DSN are
not supported. Require encrypted storage, restricted access, encrypted backups
and backup retention <=604800 seconds. Local tests cannot establish these
operational properties. PREPROD still needs runtime credentials/secret binding,
verified TLS and confirmation of the new database's backup coverage before
activation; this code does not grant IAM rights or configure infrastructure.

OAuth helpers never use `SESSION_STATE_API_KEY`. Bindings use 256 unpredictable
bits and complete issuer/user/client/provider-session ownership; a new token jti
alone does not change ownership. First-save timestamps and initialization-based
expiry are fixed. A single atomic MongoDB update serializes helper saves and
increments their revision without upsert. Unknown, foreign and expired IDs
cannot recreate or inherit bindings. `purge_at` is fixed at initialization plus
23h59m. MongoDB TTL is asynchronous; the unconditional runtime sweep additionally
removes overdue rows and evicts exchange caches, including owners whose rows
were already removed by TTL. Failed connection invalidation remains pending and
keeps state unavailable until a successful retry during maintenance.

OAuth uses a stateless MCP transport behind durable, MCP-owned session headers;
API-key transport sessions retain their existing behavior. OAuth initialization
returns a new `mcp-session-id`, which the client must send on later requests.
A 30-second unconditional maintenance task purges bindings aged >=23h59m and
their exchange cache entries, including unused bindings. Session lifetime never
exceeds 24h and activity/renewal does not extend it. Storage or maintenance
failure denies protected state access; complete overdue cleanup precedes
readiness recovery. `/healthz` reports 503 while OAuth state maintenance is not
ready. Restoring a database does not reset expiry or replace fresh authorization.

Connector instructions and tool descriptions require grounded realm/target
selection, clarification and conversational confirmation before deletion,
clearing or data-losing replacement (including save defaults/helper replacement).
Ordinary explicitly instructed editing requires no extra confirmation. MCP
cannot attest that a person saw or supplied confirmation or that a client obeyed.
No confirmation argument, pending-state protocol or universal write compiler is
introduced. First use may provision an Onto user/personal realm even with
read-only consent; deployed behavior remains unverified.

For revocation, identify the configured external client's consent entry in the
configured issuer's Keycloak Account Console and remove access. The authorized
client/provider may instead call its issuer's revoke endpoint with its own
configured authentication, refresh token and `token_type_hint=refresh_token`.
HTTP 200 proves neither prior grant existence nor effective denial. Provider
action followed by fresh introspection of an outstanding original token with
`active=false` is the denial oracle. Already dispatched work may finish;
ChatGPT Disconnect behavior remains unverified.

Local synthetic checks establish controlled code properties only. The unresolved
Core template-authorization risk (T1-C) and fixed-audience ChatGPT compatibility
risk remain explicitly accepted and unverified. Actual login, consent, exchange,
renewal/revocation, Core authorization, MongoDB durability/TLS/backup
deletion and catalogue acceptance remain unverified. Authorization configuration,
public deployment and catalogue publication need their separately assigned
owners and gates. Independent review, candidate QA and PREPROD QA remain separate.
