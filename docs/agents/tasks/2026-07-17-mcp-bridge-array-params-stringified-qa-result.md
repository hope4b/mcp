# MCP Bridge Array Parameters Stringified — QA Result

## Verdict
- `QA PASS`
- Scope accepted: the exact local MCP schema/how-to implementation satisfies the assigned server contract.
- Delivery wording: implemented locally, not committed, not pushed, not deployed.
- This verdict does not claim that the unavailable problematic client is fixed, remotely testable, deployed, or Done.

## Identity And Environment
- Worktree: `/home/ubuntu/git/onto/_platform/.worktrees/mcp-bridge-targets-schema-howto`
- Branch: `fix/mcp-bridge-targets-schema-howto`
- HEAD/base: `6ee86107d7047cb2c946362ea8fbbc2a23ca4808`
- Merge base with `origin/main`: `6ee86107d7047cb2c946362ea8fbbc2a23ca4808`
- Implementation identity: uncommitted dirty implementation over that base; pre-QA status matched the QA handoff exactly.
- Environment label: `local`.
- Service manager: `QA` for QA-owned, terminating in-process test subprocesses only.
- Network service/base URL/health URL: not applicable.
- Process ownership: QA started no long-running process, touched no occupied port, and stopped or reconfigured no existing process.
- Runtime: Python `3.14.4`; FastMCP `3.4.4`; MCP Python SDK `1.28.1`; Ruff `0.15.22`; pytest `9.1.1`.
- Interpreter: `/tmp/mcp-targets-schema-venv/bin/python`; source checkout supplied as `PYTHONPATH=.`. The system `python` alias is absent.

## Verified Content Hashes
All hashes matched the QA handoff before testing:

```text
c6b0d034951d2922fbf720133becdceb4a5a2244f9a8773ec94f1c303a2b1017  onto_mcp/api_resources.py
243e50cf70c9d0e1a7578568d3b609d16a6bea8a8e5d53ff1f80223a9ebf65e2  onto_mcp/agent_contract.py
bae178983523a84f3d5c39f840322d3da4ee22c2c0edf09525aeb35796eed36f  onto_mcp/agent_contract.json
6dd867d7e4437f721d63deafe14353f12b32bbf0b0e91f8122a362e346306581  docs/AGENT_ENTRY_GUIDE.md
b987fe992e8d95c123650f62c1b8ed78762b8b2e4faeec3b70eeba01c2d89968  tests/test_agent_contract.py
26a23229c80baa480069797b52756c7f581872fba888a95484b4c334bb982b57  tests/test_memory_artifact_schema_transport.py
6486ab93cb73dcf3deed6f81abdb713b4e447125a249a5c57bcf651da9f0f995  tests/_memory_artifact_schema_transport_probe.py
fe86bd745a483ca4970152dd0017ee59eb8a06ab7c65f5dcc11539a598ec3822  docs/agents/tasks/2026-07-17-mcp-bridge-array-params-stringified-implementation-result.md
```

## Independent Diff Review
- Reviewed the complete application, contract, guide, test, implementation-result, HANDOFF, and WORKLOG changes from the exact base, including both untracked schema/transport test files.
- Application changes are narrow: one typed target item/array declaration, signature schema changes for the three existing MemoryArtifact tools, one contextual workspace-management discriminator, and one target-shape safety note.
- Existing tool names and dedicated backend routes remain unchanged.
- Create and supersede remain dedicated writes with required targets; update remains the existing dedicated draft route with optional targets.
- The how-to response retains the established top-level fields. No response-envelope redesign was found.
- Contract tool count remains `61`; contract and guide markers both match version `2026-07-17.memory-target-shape-routing`.
- No authorization, lifecycle, realm-isolation, persistence, ordinary Onto surface, or backend implementation change was introduced.

## Forbidden-Path Review
- Searched added runtime lines and inspected the full diff for `json.loads`, string-to-array parsing, string/list unions, tolerant coercion, compatibility/fallback/legacy/alternate routes, global memory priority, semantic/LLM classification, stateful routing, new tool/namespace/profile, and response-envelope changes.
- None of those runtime paths were introduced.
- Added mentions of JSON strings are rejection guidance/tests only; the server does not accept or parse that form.
- No new `@mcp.tool` registration and no new or changed `/agent-memory/` endpoint were introduced.

## Schema Evidence
Raw `tools/list` inspection independently confirmed for `create_memory_artifact_draft`, `update_memory_artifact_draft`, and `supersede_memory_artifact`:
- supplied `targets` container is `type: array` with `minItems: 1`;
- item is `type: object` with only `target_kind`, `target_id`, and `role` properties;
- required item fields are `target_kind` and `target_id`;
- `target_kind` enum is `realm`, `template`, `entity`, `diagram`;
- `target_id` is a string and continues through existing UUID runtime validation;
- `role` is a string with default `primary`;
- create and supersede list `targets` as required;
- update exposes the same array branch plus null/default-null and does not list `targets` as required.

## Positive And Boundary Evidence
Independent ephemeral FastMCP protocol probes used a captured fake `_request_json`; no network or Onto write occurred.
- Create with exactly one realm target and omitted role succeeded; captured backend `targets` was a list and role normalized to `primary`.
- Update with targets omitted and another changed field succeeded; captured backend payload omitted `targets` entirely.
- Update with exactly one diagram target and explicit `role=context` succeeded and preserved the role.
- Supersede with two target kinds succeeded; captured backend payload preserved a two-item list of dictionaries.
- Developer-authored real-protocol regression additionally passed create, update, and supersede with two targets and observed list/dict shapes at both the tool and backend boundaries.
- Zero-target behavior failed for every tool; one-target behavior succeeded for create, update, and supersede.

## Negative And Validation Evidence
Every independent rejection below had `backend_delta=0`:
- JSON-string representation of an array for create, update, and supersede: MCP validation error `list_type`, `input_type=str`.
- Empty list for create, update, and supersede: MCP validation error `too_short`.
- Missing targets for create and supersede: MCP validation error `missing_argument`.
- Unsupported `target_kind=node`: MCP validation error `literal_error`.
- Missing `target_id`: MCP validation error `missing`.
- Non-object array item: MCP validation error `dict_type`.
- Malformed UUID: existing runtime validation returned `Parameter 'targets[1].target_id' must be a UUID.` without a backend call.
- Duplicate target reference: existing runtime validation returned `Parameter 'targets' contains duplicate target references.` without a backend call.

The malformed-UUID and duplicate cases preserve the established tool-visible validation-message behavior rather than becoming protocol-level Pydantic errors; this is not a new response path.

## How-To And Guidance Evidence
- Explicit MemoryArtifact-only intent containing contextual workspace/realm wording selected MemoryArtifact guidance, exposed `create_memory_artifact_draft` only after complete write inputs, did not ask route clarification, and emitted the non-empty array-of-objects/no-JSON-string note.
- A true independent request to create a workspace and create a MemoryArtifact remained ambiguous, returned only `list_available_realms`, asked `Which route should be used: memory, workspace_setup?`, and blocked both workspace and memory mutation tools.
- Runtime notes, `onto_mcp/agent_contract.json`, and `docs/AGENT_ENTRY_GUIDE.md` agree that targets are a non-empty array of objects with `target_kind`, `target_id`, optional/default-primary `role`, and never a JSON string.
- Full regression covered known-family, unknown/unclear, read-only, missing-ID, destructive/lifecycle, bug routing, canonical AgentMemory versus MemoryArtifact, and guide/contract consistency tests.

## Commands And Results
- Preflight: `git status --short --branch`, `git rev-parse HEAD`, branch/merge-base checks, `git diff --check`, full diff/stat review, and the assigned `sha256sum` set — passed and matched.
- Initial literal focused command using the venv interpreter without `PYTHONPATH=.` — stopped in the fresh child probe because the source checkout package was not importable. This was an environment invocation issue (`ModuleNotFoundError: onto_mcp`), not a product assertion failure.
- Focused with documented source-checkout mode: `PYTHONPATH=. /tmp/mcp-targets-schema-venv/bin/python -m unittest tests.test_memory_artifact_tools tests.test_memory_artifact_schema_transport tests.test_agent_contract` — `42` passed.
- Full unittest: `PYTHONPATH=. /tmp/mcp-targets-schema-venv/bin/python -m unittest discover -s tests -p 'test_*.py'` — `82` passed.
- Full pytest: `PYTHONPATH=. /tmp/mcp-targets-schema-venv/bin/python -m pytest tests` — `82 passed, 61 subtests passed`.
- Compile: `PYTHONPATH=. PYTHONPYCACHEPREFIX=/tmp/mcp-bridge-targets-schema-howto-qa-pycache /tmp/mcp-targets-schema-venv/bin/python -m compileall onto_mcp` — passed.
- Ruff: `PYTHONPATH=. /tmp/mcp-targets-schema-venv/bin/python -m ruff check onto_mcp/api_resources.py onto_mcp/agent_contract.py tests/test_agent_contract.py tests/test_memory_artifact_schema_transport.py tests/_memory_artifact_schema_transport_probe.py` — passed.
- Independent ephemeral probe: `PYTHONPATH=. /tmp/mcp-targets-schema-venv/bin/python /tmp/mcp_bridge_targets_qa_probe.py` — passed all positive/negative/boundary observations listed above.
- Final `git diff --check` before QA-file updates — passed.

## Skipped Checks And Remaining Gate
- No real Onto/network write, authorization fixture, or realm-isolation smoke was run: the handoff assigns a local in-process fake-backend contract gate and introduces no authorization/isolation behavior.
- The problematic external client was not tested: its exact identity/configuration is unavailable and the implementation is not deployed. This check remains mandatory after the exact accepted implementation is deployed to preprod.
- If that client still produces `input_type=str` or stringified targets, the follow-up owner is the orchestrator/client-bridge owner to register a separate client/bridge defect with client identity, version, transport, raw schema, and redacted input-shape evidence. Do not add server parsing, coercion, dual shape, or fallback under this defect.

## Anchor And Delivery
- Locked Onto anchor was received and not substituted.
- QA performed no Onto read/write, object-chat milestone, classification, MemoryArtifact, commit, push, PR, or deploy action.
- The orchestrator owns the `qa_passed` milestone and downstream commit/push/PR/deploy routing.
- Valid verification environment at this point: local only.
- Delivery wording: implemented locally, not committed, not pushed, not deployed.

## Handoff
- Verdict owner: independent MCP QA/Reviewer Agent.
- Next owner: orchestrator for `qa_passed` lifecycle recording and separately bootstrapped delivery routing.
- Post-deploy owner: problematic-client verifier; if stringification remains, register the separate client/bridge defect.

## Commit Description (English)
- Short commit description: Record QA pass for MemoryArtifact target schema and how-to routing.
