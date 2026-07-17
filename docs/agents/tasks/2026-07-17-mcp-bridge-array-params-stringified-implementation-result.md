# MCP Bridge Array Parameters Stringified — Implementation Result

## Task
- Objective: expose the accepted structured MemoryArtifact `targets` contract in generated MCP schemas and correct the approved contextual memory-only how-to routing/guidance defect.
- Scope: isolated `mcp` runtime worktree; create/update/supersede target schemas and transport regression; `how_to_use_onto_mcp`, agent contract, Agent Entry Guide, and focused tests.
- Out of scope: backend changes, server-side string parsing/coercion, dual shape, compatibility/fallback, generic schema refactor, external bridge implementation, Onto writes, QA verdict, commit, push, PR, and deploy.
- Status: `implemented_locally`.

## Bootstrap, Anchor, And Approval
- MCP developer bootstrap acknowledgement: accepted by the orchestrator.
- Canonical process source: `onto-docs/main` at `aa3f6ec50abc8a1d0289294c539b3bd401c1677f`.
- Owner implementation approval: yes, `2026-07-17T12:44:02Z`.
- Initial approval evidence: `Согласовано, начать реализацию`.
- Reproduction-gate decision: owner wrote `Исправляем schema и how-to; затем проверяем на проблемном клиенте. Если строкификация останется — регистрируем отдельный client/bridge defect`.
- Decision effect: implement only the independently confirmed schema/how-to defects; do not claim the original client is fixed; retain problematic-client verification and separate client/bridge-defect routing.
- Locked Onto anchor: realm `000ba00a-00a0-0a00-a000-000a0a0a0aa3`, object `716c7ad4-df50-4baf-ac3f-d002709a5564`; substitution is forbidden.
- Onto writes performed: no.

## Clean Worktree
- Shared checkout preserved: yes; `/home/ubuntu/git/onto/_platform/mcp` was not modified, stashed, reset, cleaned, or used for implementation.
- Worktree: `/home/ubuntu/git/onto/_platform/.worktrees/mcp-bridge-targets-schema-howto`.
- Branch: `fix/mcp-bridge-targets-schema-howto`.
- Base: `origin/main` at `6ee86107d7047cb2c946362ea8fbbc2a23ca4808`.
- Initial status: clean; branch tracked `origin/main` with no changed or untracked files.

## Runtime Identity
- Repository package: `onto-mcp-server` `0.1.0` from `pyproject.toml`; source checkout used through `PYTHONPATH=.`.
- Python: `3.14.4`.
- FastMCP: `3.4.4`.
- MCP Python SDK: `1.28.1`.
- Client/transport: `fastmcp.Client` with FastMCP's in-memory MCP protocol transport.
- Backend boundary: `_request_json` captured locally and replaced with a fake artifact response; no network or Onto mutation occurred.
- Original problematic bridge identity/version/configuration: not supplied.

## Pre-Fix Reproduction Evidence

### Raw `tools/list`
Create, update, and supersede exposed the same underspecified target item:

```json
{
  "anyOf": [
    {
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "type": "array"
    },
    {"type": "null"}
  ],
  "default": null
}
```

The item did not expose `target_kind`, `target_id`, or `role`.

### Transport
For two-target create, update, and supersede calls through the official FastMCP client:
- tool-boundary type: `list` with `dict` items;
- captured backend JSON type: `list` with `dict` items;
- no protocol error.

The reported stringification did not reproduce on this client. This remains explicit evidence, not a claim about the unavailable problematic bridge.

### How-to
- Explicit MemoryArtifact work with workspace/realm used only as context returned `ambiguous_task` behavior between `memory` and `workspace_setup`.
- A genuine combined workspace-management plus MemoryArtifact request returned the same ambiguity; that combined result was already correct.

## Changes

### Explicit target schema
- Added a typed MCP target item with:
  - required `target_kind`, limited to `realm`, `template`, `entity`, or `diagram`;
  - required string `target_id`, still validated as UUID by the existing runtime normalizer;
  - optional string `role`, defaulting to `primary`.
- Added `minItems: 1` to the array schema.
- Made `targets` schema-required for `create_memory_artifact_draft` and `supersede_memory_artifact`, matching their existing runtime requirement.
- Kept `targets` optional for `update_memory_artifact_draft`; when supplied, FastMCP and the existing runtime both require a non-empty structured array.
- Preserved existing normalization, duplicate detection, UUID validation, target kinds, role normalization, routes, payload names, response formatting, lifecycle, and backend authorization delegation.

### Narrow how-to routing
- When `memory` and `workspace_setup` keywords both match, workspace/realm words are treated as memory context unless the request independently asks to create, update, rename, delete, remove, or manage a workspace/realm.
- Explicit memory-only intent with contextual workspace/realm wording now selects the memory route.
- A true independent workspace-management plus memory request remains ambiguous and safe-discovery-only.
- No global memory priority, semantic classifier, state, new syntax, or response-envelope change was added.

### Contract and guide
- Runtime memory safety notes now state that `targets` is a non-empty array of objects with `target_kind`, `target_id`, and optional `role`, and prohibit a JSON string form.
- `onto_mcp/agent_contract.json` and `docs/AGENT_ENTRY_GUIDE.md` document the same shape and create/update/supersede requiredness.
- Contract version changed from `2026-07-07.bug-lifecycle-routing` to `2026-07-17.memory-target-shape-routing`. This follows the repository's established contract/guide marker consistency check for a runtime routing and guidance contract change; no top-level response semantics changed.

## Post-Fix Evidence

### Create and supersede `targets`

```json
{
  "description": "Non-empty array of structured MemoryArtifact target objects.",
  "items": {
    "properties": {
      "target_kind": {
        "enum": ["realm", "template", "entity", "diagram"],
        "type": "string"
      },
      "target_id": {"type": "string"},
      "role": {"default": "primary", "type": "string"}
    },
    "required": ["target_kind", "target_id"],
    "type": "object"
  },
  "minItems": 1,
  "type": "array"
}
```

`targets` is present in the enclosing tool schema's `required` list.

### Update `targets`
- The same array/object/minimum item schema appears as the non-null branch.
- The field remains nullable/omittable with default `null` and is not in the enclosing `required` list.

### Transport
- Create, update, and supersede each received `list` at the tool boundary.
- Each captured backend payload contained a two-item JSON array of objects.
- Empty arrays were rejected through the real protocol for all three tools.
- No string request shape was introduced or accepted.

### How-to before/after
- Before: contextual memory-only request returned ambiguity between `memory` and `workspace_setup`.
- After: it routes to MemoryArtifact guidance and, with complete approved write inputs, includes `create_memory_artifact_draft`; it also emits the explicit array-of-objects guidance.
- Before and after: a genuine request to create a workspace and also create a MemoryArtifact remains ambiguous, returns only `list_available_realms`, and keeps mutation tools blocked.

## Files Changed
- `onto_mcp/api_resources.py` — explicit target item/array schema and create/update/supersede requiredness.
- `onto_mcp/agent_contract.py` — narrow contextual-memory routing and runtime target-shape note.
- `onto_mcp/agent_contract.json` — canonical target guidance and contract version.
- `docs/AGENT_ENTRY_GUIDE.md` — matching human-readable target example and rules.
- `tests/test_agent_contract.py` — contextual memory-only and true multi-goal routing regressions.
- `tests/test_memory_artifact_schema_transport.py` — schema, transport, and empty-array regression assertions.
- `tests/_memory_artifact_schema_transport_probe.py` — fresh-process real FastMCP protocol/fake-backend probe, isolated from legacy unit-test stubs.
- `docs/agents/tasks/2026-07-17-mcp-bridge-array-params-stringified-implementation-result.md` — implementation evidence.
- `docs/agents/WORKLOG.md` and `docs/agents/HANDOFF.md` — required project-memory updates.

## Validation
- Focused: `python -m unittest tests.test_memory_artifact_tools tests.test_memory_artifact_schema_transport tests.test_agent_contract` — `42` passed.
- Full unittest: `python -m unittest discover -s tests -p 'test_*.py'` — `82` passed.
- Full pytest: `python -m pytest tests` — `82 passed, 61 subtests passed`.
- Compile: `python -m compileall onto_mcp` with `/tmp` pycache prefix — passed.
- Ruff on touched Python files — passed.
- Whitespace: `git diff --check` — passed after final report/memory updates.
- Network/live Onto write smoke: not run; local fake backend was required before QA and no write authorization/environment was assigned to this developer.
- Problematic client verification: not run because its identity/configuration was not supplied and the change is not deployed.

## Forbidden-Path Confirmation
- No `json.loads`, tolerant string parser, string/array union, server-side coercion, fallback, compatibility adapter, alternate/legacy endpoint, backend change, broad schema refactor, global memory priority, semantic/LLM classifier, router state, new tool/namespace/profile, or response-envelope redesign was introduced.
- Ordinary Onto surfaces, MemoryArtifact lifecycle/authorization/storage, and backend routes were not changed.
- No secrets, API keys, credentials, or real artifact bodies were printed or committed.
- No Onto, PR, deploy, review, or QA action was performed.

## Risks And Remaining Verification
- The exact reported bridge stringification was not reproduced; this patch fixes the confirmed underspecified schema and how-to defect only.
- After deployment, the exact problematic client must be checked and its tool-boundary `input_type` recorded.
- If that client still produces `input_type=str`, register a separate client/bridge defect. Do not add server-side parsing, dual shape, or compatibility behavior under this change.
- Independent MCP QA against the exact implementation remains mandatory before preprod deploy.

## Delivery Status
- Implementation: complete locally.
- Commit: not performed.
- Push: not performed.
- PR: not opened.
- Deploy: not performed.
- Verification environment: local only.
- Required wording: implemented locally, not committed, not pushed, not deployed.

## Handoff
- Next owner: orchestrator for implementation review, exact-implementation QA environment/handoff, and later delivery gates.
- Post-deploy owner: problematic-client verifier; create a separate client/bridge defect if stringification persists.

## Commit Description (English)
- Short commit description: Define MemoryArtifact target schemas and contextual memory routing.
