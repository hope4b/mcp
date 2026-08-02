# Owner-Driven Realm Agent Admission — MCP Implementation Result

## Task

- Short objective: implement ordered Slice 2 of approved Change Spec
  `AGENT-ROLE-ADMISSION-001` in `mcp`.
- Scope: exactly one high-risk FastMCP tool,
  `admit_realm_agent(realm_id, candidate)`, with recursively closed public
  models, exact one-POST transport, dedicated safe response parsing,
  transport-ledger semantics, Agent Contract/how-to routing, documentation,
  and regression tests.
- Out of scope: `a4b-core`, `a4b-webui`, `mcp-server`, generic lifecycle
  mutation, admission preflight, confirmation fields or tools, client
  fingerprinting, fallback, compatibility, dual-shape handling, adapters,
  alternate or legacy endpoints, migration, commit, push, PR, deploy, merge,
  QA verdict, and Onto writes.

## Context Used

- Workspace and project `AGENTS.md`, `docs/agents/ROLES.md`,
  `PROJECT_CONTEXT.md`, `ARCHITECTURE_MAP.md`, `TEST_STRATEGY.md`,
  `HANDOFF.md`, latest `WORKLOG.md`, and `TASK_TEMPLATE.md`: read.
- Process source: `onto-docs/origin/main@9c21ce5`.
- Approved contract/review/handoff source:
  `onto-docs@eb9f03ddb663dd389fe7c9ff4a6236a17374c306`, including the approved
  Change Spec, Genesis v2 package, complete review, and implementation
  handoff.
- Ordered Slice 1 input: backend implementation result from
  `a4b-core@ab6a6cbc00d74aebe47ae1cd2ce4f80aa5c1601c`.
- The externally supplied Onto anchor was received, kept locked, and not
  substituted. This developer made no Onto/object-chat write.

## Bootstrap Timing Defect And Revalidation

- Provisional edits began before the corrected Bootstrap Acknowledgement was
  accepted. The Orchestrator stopped implementation immediately when this was
  identified.
- The corrected acknowledgement explicitly named the required project and
  process sources, exact role/scope/output, ordered backend input, and locked
  anchor; the Orchestrator accepted it before implementation resumed.
- After acceptance, every provisional diff was fully re-inspected against the
  approved Change Spec, implementation handoff, backend result, project
  instructions, and forbidden-path list. An unrelated formatter spill in two
  existing large Python files was reverted and only the task-owned hunks were
  reapplied.
- All focused, full, schema/transport, format, compile, JSON, Ruff-baseline,
  and diff checks reported below were run from the corrected post-acceptance
  state. No provisional evidence is used as acceptance evidence.

## Repository Identity

- Repository: `mcp`.
- Worktree: `<platform_root>/.worktrees/mcp-request-new-agent-role`.
- Branch: `feature/request-new-agent-role`.
- Fresh base/HEAD SHA:
  `14ac465f85377617e57c9e812eb0d664a98c7b15`.
- Base/HEAD tree: `b944e3f0a33884a3869776971eb8259862c211e6`.
- Implementation commit:
  `c1f5581d0a9fbc22e625ec251fd1863394e68e6e`.
- Implementation tree: `532f21357e0bc8a781d12d8769a3ab456b819206`.
- Implementation commit patch SHA-256:
  `043d0f730faccbe6aef5659008cda89af96edd635eb032b7c7c1eb6424fb2d6f`.
- The follow-up delivery-evidence commit is intentionally self-referential
  and is reported externally as the final verified remote branch head.
- Shared checkout and unrelated worktrees were not changed.

## Changes

### Runtime Contract

- Added exactly one public high-risk tool:
  `admit_realm_agent(realm_id, candidate)`.
- Added recursively closed strict Pydantic models for the complete ordered
  `RealmAgentAdmissionCandidateV1`, both nested candidate documents, both
  success objects, the stable MCP error envelope, and every closed safe error
  detail object.
- Unknown, missing, null-invalid, or third public arguments are rejected by
  the registered FastMCP schema before tool invocation. Candidate and nested
  schemas advertise `additionalProperties=false`.
- Outer/candidate realm mismatch returns the exact local
  `realm_id_mismatch` envelope with null backend status, both transport flags
  false, and zero header/backend calls.
- A valid invocation sends exactly one `POST` to
  `/realm/{realmId}/agent-population/admissions` with the bare candidate,
  ambient owner credential headers, and no wrapper, `confirm`, fingerprint,
  Steward/Methodologist field, evidence, or generic lifecycle call.
- The dedicated parser accepts only the exact ordered closed `admitted` and
  `already_admitted_exact` results or one stable closed backend error. Invalid
  response objects become `invalid_backend_response`; no raw backend body,
  snippet, credential, charter prose, exception text, or stack detail is
  retained.
- Post-dispatch request exceptions and the outer MCP timeout return exact
  `outcome_unknown` with `request_sent=true`, `response_received=false`, and
  recovery `retry_exact_admission`. The tool never claims cancellation or
  success for an ambiguous sent request.

### Agent Routing And Guidance

- Advanced the canonical Agent Contract to
  `2026-08-02.realm-agent-admission`, increased inventory from `64` to `65`,
  and added the tool exactly once in its dedicated high-risk family.
- Explicit RU `проверь и зарегистрируй` and EN admission intent routes in
  `write_intent` to exactly this one tool. `read_only` keeps it out of
  `next_calls`; routing never introduces a preflight, second confirmation,
  generic MemoryArtifact chain, alternate endpoint, or compatibility path.
- Updated the generated guide markers, README, setup instructions, and QA
  inventory with the exact one-tool/one-POST contract and exact-retry rule.

## Changed Files

- Runtime: `onto_mcp/realm_agent_admission.py`,
  `onto_mcp/api_resources.py`.
- Agent contract: `onto_mcp/agent_contract.json`,
  `onto_mcp/agent_contract.py`, `docs/AGENT_ENTRY_GUIDE.md`.
- Public/operator guidance: `README.md`, `MCP_SETUP.md`,
  `docs/income/QA_MCP_TOOL_CATALOG.md`.
- Tests: `tests/test_realm_agent_admission.py`,
  `tests/_realm_agent_admission_schema_transport_probe.py`,
  `tests/test_realm_agent_admission_schema_transport.py`,
  `tests/test_agent_contract.py`.
- Coordination: this result, `docs/agents/WORKLOG.md`,
  `docs/agents/HANDOFF.md`, and `docs/agents/DECISIONS.md`.

## Validation

- Focused admission/schema/Agent Contract unittest: `60` passed.
- Full unittest discovery with repository root on `PYTHONPATH`: `172` passed.
- Full pytest with repository root on `PYTHONPATH`: `172` passed.
- Real FastMCP in-process client probe: `65` tools, one admission
  registration, exactly two required public arguments, recursively closed
  candidate schemas, advertised output schema, protocol invalid-param
  rejection, one exact bare-body POST, and mismatch zero-call behavior all
  passed.
- Dedicated unit matrix passed for exact local mismatch, both success shapes,
  all `13` backend error codes, invalid received responses, request exception,
  raw-snippet absence, and outer timeout ambiguity/exact retry guidance.
- `python -m compileall -q onto_mcp tests`: passed.
- `python -m json.tool onto_mcp/agent_contract.json`: passed.
- Ruff on every new task-owned Python file: passed with zero findings.
- Black check on every new task-owned Python file: passed.
- Full Ruff `0.16.1`: current `77` findings and base `77` findings are the same
  pre-existing repository debt; no new finding was introduced by this slice.
- `git diff --check`: passed.
- The first full-suite invocation without `PYTHONPATH` reproduced an existing
  child-process import-path limitation in
  `_memory_artifact_schema_transport_probe.py`; rerunning with the repository
  root explicitly on `PYTHONPATH` passed all `172` tests. No existing probe or
  product behavior was changed for this environment-only issue.
- No live backend mutation, QA environment, deploy, remote push, PR, merge,
  or Onto write was run.

## Risk And Delivery State

- Residual risk is the exact combined runtime boundary with the ordered
  uncommitted backend slice: ambient OWNER authorization, lost-response exact
  retry, and backend atomicity/concurrency/rollback require independent
  backend/API QA against an approved environment containing the exact eventual
  `a4b-core` and `mcp` identities.
- No fallback, backward compatibility, dual-shape handling, transitional
  adapter, alternate endpoint, legacy route, new tool, or new solution path
  was introduced.
- Implementation status: `committed` at
  `c1f5581d0a9fbc22e625ec251fd1863394e68e6e`.
- Delivery status at this evidence update: push and draft-PR creation are the
  remaining authorized Git persistence steps; their final immutable evidence
  is reported externally after the self-referential evidence commit is pushed.
- Deploy status: `not_started`; no deployment is authorized.
- Lifecycle: `qa_environment_pending` / `backend_qa_pending`.
- Authorized draft PR title: `Запрос новой агентной роли`.

## Commit Description (English)

- Short commit description: `Implement owner-driven realm agent admission`.

## Handoff

- The Orchestrator should pin the implementation commit/tree above and the
  externally reported final delivery-evidence branch head.
- After both slices have immutable committed identities, prepare the required
  QA Contract Handoff and run independent backend/API QA in an approved
  exact-identity environment before any deploy decision.
- No deploy, merge, QA verdict, or Onto milestone write was performed by this
  MCP implementer.

## QA Correction — `QA-FAIL-MCP-INVALID-PARAMS-001`

### Authority And Scope

- The owner returned the observed preprod failure for correction without
  changing the approved one-tool contract.
- Correction base is the exact prior remote/head
  `be99986c8dda3c28efd2f8279519729dcd235ea7`, tree
  `310e4808ed2adf0d83b0586450256b6a209e3398`, on the existing
  `feature/request-new-agent-role` branch and PR `#20`.
- Scope is only the observable HTTP MCP invalid-parameter contract for
  `admit_realm_agent`; no backend, frontend, infrastructure, deploy, merge,
  Onto write, tool, endpoint, fallback, compatibility or alternate path is
  authorized or introduced.

### Root Cause And Correction

- FastMCP `3.4.5` with MCP SDK `1.29.0` turns both SDK JSON-schema and
  Pydantic argument-validation failures into HTTP `200`
  `CallToolResult(isError=true)`. Enabling FastMCP strict input validation does
  not change that wire taxonomy to JSON-RPC `-32602`.
- The existing `/mcp` HTTP app now has one admission-only ASGI response
  boundary. It validates the exact same closed two-argument model, forwards the
  request through ordinary FastMCP session and tool-dispatch validation, and
  rewrites only the resulting validation `isError` for an invalid
  `admit_realm_agent` call to exact JSON-RPC
  `{"code":-32602,"message":"Invalid params"}`.
- Valid admission calls bypass the correction unchanged. Every other MCP tool,
  malformed non-admission call, non-HTTP transport, health route and non-MCP
  request bypasses it unchanged. There is no framework-global behavior change.

### Real HTTP Regression Evidence

- Added a real production-ASGI `/mcp` transport probe using FastMCP initialize,
  session id, initialized notification and raw HTTP `tools/call` messages.
- The four preprod failures are pinned independently: extra
  `candidate.confirm`, missing `candidate.slug`, null
  `candidate.charter_document`, and extra public `confirm`.
- Each returns HTTP `200` with exact JSON-RPC error code `-32602` and message
  `Invalid params`, without a `result` or Pydantic validation prose.
- Instrumented counters prove all four together perform zero admission
  tool-body calls and zero backend calls.
- Transparency probes prove an invalid non-admission tool retains FastMCP
  `result.isError`, while one valid admission still invokes exactly one tool
  body and exactly one backend POST.

### Correction Validation

- Focused admission/schema/real-HTTP unittest: `18` passed.
- Full unittest discovery: `176` passed.
- Full pytest: `176` passed plus `228` subtests.
- `python -m compileall -q onto_mcp tests`: passed.
- Agent Contract JSON validation: passed; its content and `65`-tool inventory
  are unchanged.
- Ruff on all correction-touched Python files: passed with zero findings.
- Black on both new correction test files: passed.
- Full Ruff: `76` pre-existing findings versus the prior recorded `77`; the
  correction adds no finding and removes the old `server.py` import finding.
- `git diff --check`: passed.

### Correction Delivery State

- Correction implementation commit:
  `83218d785516c8f289f41b0e46c2e353f75d4145`.
- Correction implementation tree:
  `46a247f9de51be11becfe4cd35c677f8cf1cbec4`.
- Correction patch SHA-256:
  `d6b430b75e94ee3ebb7ad7e39f954c25557519de913df5d70c5337849df74b19`.
- The follow-up delivery-evidence commit is self-referential and its final
  pushed SHA/tree will be reported externally.
- Existing PR remains `#20`, title `Запрос новой агентной роли`.
- Status: `committed`; evidence update and push pending, not deployed;
  independent Re-QA remains required after a separately authorized exact-ref
  redeploy.

Commit description (EN): Fix admission invalid-params JSON-RPC handling
