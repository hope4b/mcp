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

---

## Python 3.11 Deployment-Blocker Re-QA — 2026-07-17

### Re-QA Verdict
- `QA PASS`
- Scope accepted: the exact five-file local rework on top of delivered commit `8fcd54d17ef60c809dc23a60056ac719a6bbf8de` resolves the Python 3.11/Pydantic TypedDict startup blocker without changing the accepted schema/how-to behavior.
- The earlier QA verdict remains evidence for the delivered commit identity only; this separated verdict covers the new local rework identity below.
- Delivery wording: rework implemented locally, not committed, not pushed, not redeployed; deployment remains blocked until downstream commit/push/redeploy succeeds.

### Exact Rework Identity
- Worktree: `/home/ubuntu/git/onto/_platform/.worktrees/mcp-bridge-targets-schema-howto`
- Branch: `fix/mcp-bridge-targets-schema-howto`
- HEAD/base for rework delta: `8fcd54d17ef60c809dc23a60056ac719a6bbf8de`
- Pre-Re-QA status: exactly five modified files and no unexpected file:
  - `onto_mcp/api_resources.py`
  - `tests/test_memory_artifact_schema_transport.py`
  - `docs/agents/tasks/2026-07-17-mcp-bridge-array-params-stringified-implementation-result.md`
  - `docs/agents/HANDOFF.md`
  - `docs/agents/WORKLOG.md`
- Pre-Re-QA hashes matched the assigned identity exactly:

```text
8293bb6513950743e936dc5b865c7769ed0a2e51463359ed739bad17cb1b685b  onto_mcp/api_resources.py
d9b7a763427d734f4e662ab292c98d7c2d73d1a7543b8fba71ccbc65d5745866  tests/test_memory_artifact_schema_transport.py
a7f6758739c2a576388dbfbc479f31f19438f055c7355d8e459d2b639aeff4b7  docs/agents/tasks/2026-07-17-mcp-bridge-array-params-stringified-implementation-result.md
cd467b42432066e1fe98eaafb989d7b5f0473040ba80d34d3493bd4566cd7541  docs/agents/HANDOFF.md
18e6be658d7bcf3b9d9f9c139a96167c7f2bf233424552f549adc6eca045adde  docs/agents/WORKLOG.md
```

### Complete Delta And Forbidden-Path Review
- The full delta contains one runtime change: `TypedDict` and `NotRequired` move from `typing` to `typing_extensions`; `Annotated`, `Any`, and `Literal` remain imported from `typing`.
- The only test change adds a static source regression for that import boundary. Remaining changes are implementation evidence and required project-memory updates.
- No dependency file, Dockerfile, tool signature, schema model, normalization, endpoint, payload, response, routing, authorization, lifecycle, or contract-guide file changed.
- No parser, coercion, string/array union, fallback, compatibility adapter, alternate/legacy route, client workaround, or new dependency was introduced.
- `git diff --check` passed before and after the Re-QA evidence updates.

### Deployment And Runtime Evidence
- Repository Dockerfile declares `FROM python:3.11-slim` and installs the unchanged `requirements.txt`.
- GitHub workflow run `29584301303` independently resolved as completed/success at workflow level; its remote runtime remained blocked as recorded in the accepted implementation evidence.
- Root-cause evidence supplied by the deployment contour: Python 3.11 Pydantic rejected `typing.TypedDict` during FastMCP registration and required `typing_extensions.TypedDict`.
- Independent minimal Python 3.11/Pydantic probe confirmed the same boundary:
  - functional `typing.TypedDict` was rejected with a `PydanticUserError` that points to `typing_extensions.TypedDict`;
  - the equivalent `typing_extensions.TypedDict` produced a valid object schema.
- Dependency chain is already effective and unchanged:
  - declared `fastmcp>=2.0` resolved to `fastmcp 3.4.4`;
  - its `fastmcp-slim 3.4.4` runtime requirement explicitly includes `typing-extensions>=4.0.0` and Pydantic;
  - Pydantic `2.13.4` additionally declares `typing-extensions>=4.14.1`;
  - the image resolved `typing_extensions 4.16.0`.
- A QA-owned image was built from the exact dirty source using the repository Dockerfile: Python `3.11.15`, FastMCP `3.4.4`, Pydantic `2.13.4`, and typing_extensions `4.16.0`.
- The image copy of `/app/onto_mcp/api_resources.py` had the exact assigned hash `8293bb6513950743e936dc5b865c7769ed0a2e51463359ed739bad17cb1b685b`.
- Importing `onto_mcp.api_resources` completed on Python 3.11, which exercises FastMCP tool registration and the previously failing schema-generation boundary.

### Python 3.11 Schema And Transport Evidence
- The fresh-process FastMCP probe passed inside the Python 3.11 image.
- Raw schemas for create, update, and supersede retained:
  - array container;
  - `minItems: 1`;
  - explicit object items;
  - required `target_kind` and `target_id`;
  - target-kind enum;
  - default-primary role;
  - required create/supersede and optional update semantics.
- Create, update, and supersede each received lists with dictionary items and emitted two-item array-shaped captured backend payloads.
- Empty arrays remained rejected for all three tools.
- The original independent negative/boundary/how-to probe also remained green in the local FastMCP environment: string, empty, missing, unsupported, malformed, non-object, and duplicate inputs did not reach backend; contextual memory-only and true combined-intent routing remained correct.

### Commands And Results
- Identity/diff: status, HEAD, branch, full five-file diff/stat/name-status, assigned SHA-256 set, Dockerfile/requirements inspection, and `git diff --check` — passed.
- Local focused: `43` tests passed.
- Local full unittest: `83` tests passed.
- Local pytest: `83 passed, 61 subtests passed`.
- Local compileall and Ruff on the touched runtime/test files — passed.
- Local original ephemeral schema/how-to/negative probe — passed.
- Python 3.11 image build from current worktree — passed.
- Python 3.11 import/tool-registration/version probe — passed.
- Python 3.11 fresh FastMCP schema/transport probe — passed.
- Python 3.11 focused suite: `43` tests passed.
- Python 3.11 full unittest: `83` tests passed.
- Python 3.11 pytest: `83` tests passed.
- Python 3.11 compileall and Ruff — passed.
- The first container suite attempt omitted the read-only docs mount and failed only because `docs/AGENT_ENTRY_GUIDE.md` was unavailable to a guide-marker test. Repeating with complete read-only test/docs fixtures passed all checks; this was a QA fixture setup error, not a product failure.

### Skipped And Remaining Gates
- No preprod runtime was changed or restarted by Re-QA; no remote smoke was run against the still-blocked old deployment.
- No Onto, object-chat, classification, MemoryArtifact, commit, push, PR mutation, or deploy action was performed.
- The problematic client remains intentionally untested until the exact Re-QA-passed rework is committed, pushed, and successfully redeployed. If it still yields `input_type=str`, register a separate client/bridge defect; do not add server-side parsing or compatibility behavior.
- This Re-QA permits downstream commit/push/redeploy routing but does not itself mark preprod deployed or the defect Done.

### Re-QA Handoff
- Exact verdict: `QA PASS`.
- Next owner: orchestrator for lifecycle recording and a separately bootstrapped delivery/redeploy role.
- Delivery wording: rework implemented locally, not committed, not pushed, not redeployed; deployment remains blocked pending successful redeploy.

### Re-QA Commit Description (English)
- Short commit description: Record Python 3.11 re-QA for MemoryArtifact target schemas.
