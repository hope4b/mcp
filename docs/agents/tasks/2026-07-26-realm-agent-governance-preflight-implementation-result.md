# MCP Realm-Agent Governance Preflight Implementation Result

## Task

- Change: `MCP-REALM-GOVERNANCE-PREFLIGHT-001`
- Role: MCP Application Developer
- Objective: implement the owner-approved read-only realm-agent charter and
  registry proposal preflight.
- Scope: the `mcp` repository only, from pinned baseline
  `13e1b7eea4066305cbd407fcb118c90df298c344` on isolated branch
  `feature/mcp-realm-agent-governance-preflight`.
- Out of scope: backend/frontend/gateway/server changes, governance writes,
  consensus, acceptance, Constitution preflight, live realm repair, QA,
  deployment and production/preprod verification.

## Context Used

- Workspace and project `AGENTS.md`: read.
- `docs/agents/ROLES.md`, `PROJECT_CONTEXT.md`, `ARCHITECTURE_MAP.md`,
  `TEST_STRATEGY.md`, `HANDOFF.md` and latest `WORKLOG.md`: read.
- Approved Change Spec, final review and implementation handoff: read in full
  from `onto-docs` baseline
  `b99f02afbb68408c11085d710ef0f19f0dd818eb`.
- Owner implementation approval: exact message `Ок, согласовано`.
- Primary Onto anchor: none supplied; no milestone or realm write was
  attempted.

## Changes

- Added one public FastMCP tool:
  `preflight_realm_agent_governance_proposal(realm_id,
  proposal_artifact_id) -> str`.
- Added a private typed exact-id MemoryArtifact reader and a private
  accepted/current path reader with closed `404`, auth, timeout, network,
  invalid-response and backend-error projections.
- Implemented realm-first input validation, strict proposal/envelope/source
  capture validation, exact server-UTC timestamp grammar and interval proof,
  exact UTF-8 body SHA-256, strict constitution/registry/charter validation,
  candidate/repair/resident/registry classification, exact predecessor rules,
  frozen submit-time electorate behavior, registry drift handling, call
  cancellation and bounded fail-closed framing.
- Reused the existing strict realm-agent registry and charter parser seams;
  existing `list_realm_agents` and `get_realm_agent` contracts were not
  tightened.
- Added the tool to the Agent Contract exactly once, moved the contract to
  version `2026-07-26.realm-agent-governance-preflight`, increased the tool
  count from `63` to `64`, and added exclusive explicit-preflight routing.
- Updated entry/setup/README/QA guidance to require the structural preflight
  after submit before sheet/positions and again immediately before accept.

## Changed Files

- `onto_mcp/realm_agents.py`
- `onto_mcp/api_resources.py`
- `onto_mcp/agent_contract.json`
- `onto_mcp/agent_contract.py`
- `tests/test_realm_agent_governance_preflight.py`
- `tests/test_realm_agent_tools.py`
- `tests/test_agent_contract.py`
- `docs/AGENT_ENTRY_GUIDE.md`
- `README.md`
- `MCP_SETUP.md`
- `docs/income/QA_MCP_TOOL_CATALOG.md`
- `docs/agents/tasks/2026-07-26-realm-agent-governance-preflight-implementation-result.md`
- `docs/agents/WORKLOG.md`
- `docs/agents/HANDOFF.md`
- `docs/agents/DECISIONS.md`

## Acceptance-Criteria Traceability

- `AC-001..005`, `AC-036`, `AC-043`: registered schema, strict realm-first
  validation, exact proposal read/identity, envelope, status, path and
  proposal timestamp failures are covered by the focused suite and real
  registered FastMCP stdio probe.
- `AC-006..009`, `AC-013..014`, `AC-040`: initial candidate,
  candidate-repair and resident successor classification, strict charter
  metadata, exact predecessor objects and every predecessor failure class are
  covered by focused fixtures.
- `AC-010..012`, `AC-024`, `AC-039`: registry successor, row validation,
  resident preservation, exact accepted/current charter requirements,
  addition gating and captured-electorate/current-registry drift are covered
  by ordered call-ledger fixtures.
- `AC-015..022`, `AC-037`: current-governance absence/invalidity, closed
  dependency mapping, secret omission, dedicated timeout/cancellation,
  one-label/one-JSON framing, exact-body hash variants, bounded overflow,
  caching and no-fallback/no-write ledgers are covered.
- `AC-023`, `AC-025`: Agent Contract, entry guide, README, setup guide, QA
  catalog, existing realm-agent and generic MemoryArtifact regressions, full
  unittest/pytest and real registered FastMCP schema/call all pass.
- `AC-038`, `AC-041..044`: captured source shape and exact-id identity,
  lifecycle field typing, complete strict timestamp grammar, equality
  boundaries, exact preserved timestamps and repeat-call stability are
  covered.
- `AC-026..035` are explicitly post-deploy governance repair, finding and
  independent-QA criteria. This MCP implementation supplies the required
  gate but does not claim those later process outcomes.

## Validation

- Focused new unittest: `22` passed.
- Focused plus existing realm-agent, generic MemoryArtifact and Agent Contract
  regressions: `92` passed.
- Full unittest discovery: `137` passed.
- Full pytest: `137` passed.
- `python3 -m compileall -q onto_mcp`: passed with cache redirected to
  `/tmp`.
- `python3 -m json.tool onto_mcp/agent_contract.json`: passed.
- Ruff `F`-class static scan of touched Python files: passed.
- `git diff --check`: passed.
- Real FastMCP stdio subprocess: passed; `64` registered tools, exact two
  required string fields, `additionalProperties=false`, and a registered
  invalid-input call returned the dedicated preflight JSON with
  `realm_id_invalid`.
- No live backend, realm mutation, object chat, deployment or independent QA
  was run.

## QA-FAIL-001 Scoped Fix

- Persisted QA result:
  `onto-docs/docs/agents/tasks/2026-07-26-realm-agent-governance-preflight-qa-result.md`
  at process source
  `79d8c7cd14f9c22f78a7f4affa7ef850bf338436`.
- Scope: remove only the three new task-owned Ruff `0.16.0` findings:
  `UP034` in `onto_mcp/agent_contract.py`, plus `I001` and `FLY002` in
  `tests/test_realm_agent_governance_preflight.py`.
- Fix commit:
  `88247ad4433b3313620b3292df3c4a7ff25d7d7a`.
- Fix commit patch SHA-256:
  `3cb8d605013f1aaba67981fd0af28f9f39c9a47d7cf0f12e1bfec589047edc4a`.
- The fix only removes redundant parentheses/blank-line formatting and
  rewrites one literal string join as an equivalent f-string. Runtime
  behavior, public contract, test assertions and fixtures are unchanged.
- Smallest Ruff reproducers now pass with zero findings.
- The mandatory unrestricted Ruff command now reports exactly the existing
  `33` baseline findings, down from QA's `36`; none of the three
  task-owned findings remains. Its exit stays `1` because changing or
  suppressing baseline Ruff debt was explicitly outside this fix scope.
- Revalidation passed: focused unittest `22`; focused plus existing
  regressions `92`; full unittest `137`; full pytest `137`; compileall;
  Agent Contract JSON; `git diff --check`; real FastMCP in-process and stdio
  schema/call probes.
- No Ruff ignore/config change, unrelated baseline cleanup, fallback,
  compatibility, endpoint, contract or behavior change was made.
- No developer-issued QA verdict is claimed; independent re-QA remains
  required.

## Delivery And Status

- Implementation commit:
  `47de6119d46cb5036446dda9ea4ee04b103676c1`.
- Implementation commit patch SHA-256:
  `e03d613d47f2b59b083cbda84671b3de2f4497bca5582db0a54b6b22f8b8956d`.
- Remote branch:
  `origin/feature/mcp-realm-agent-governance-preflight`; exact remote ref was
  verified equal to fix commit
  `88247ad4433b3313620b3292df3c4a7ff25d7d7a` after the scoped fix push.
- Delivery evidence commit: this field is intentionally self-referential and
  is reported externally as the final pushed branch head.
- Current lifecycle state: `implementation_reported`.
- Delivery state: `committed`, `pushed`, `backend_qa_pending`; not deployed.
- Previous QA verdict: `QA FAIL` only for `QA-FAIL-001`; scoped fix is pushed
  and independent re-QA is pending. Developer checks are not a QA verdict.
- Deploy: not authorized and not performed.

## Current Main Integration

- Owner authorization:
  `Согласовано, интегрируй current main в PR #18 и повтори QA.`
- Process source:
  `onto-docs/main` at
  `51a2e72c6ab1db839693abf2d7dbefc13cc0e9ab`.
- Integration input:
  governance-preflight branch head
  `942ee82c0a60ba586673fed2e3b2444c6c1afb15` and fetched
  `origin/main` `e20699e54cb5e9fad0caea9e56ec23416aef4d2e`.
- Normal merge commit:
  `2dc394e0a5a529c21d54ccc2faab8ecef73d4367`, with parents
  `942ee82c0a60ba586673fed2e3b2444c6c1afb15` and
  `e20699e54cb5e9fad0caea9e56ec23416aef4d2e`.
- Preservation:
  current-main realm-agent listing, exact-slug identity, conditional charter
  and bootstrap-prefix guidance remain; governance-preflight keeps its
  dedicated tool, contract, exclusive intent and structural-only semantics.
  Explicit preflight intent takes precedence, while ordinary MemoryArtifact
  path reads retain generic MemoryArtifact routing.
- Integrated validation:
  Agent Contract `44`, governance preflight `22`, realm-agent runtime `23`,
  generic MemoryArtifact `16`, full unittest `150`, full pytest `150`,
  compileall, JSON and diff checks passed.
- Ruff `0.16.0` current-main comparison:
  `35` findings in common touched files before integration and `35` after,
  with an exactly equal normalized multiset; the added preflight test has
  zero findings. No new Ruff debt was introduced.
- Real FastMCP `3.4.4`:
  in-process and stdio both exposed `64` tools; both preserved the
  four-step bootstrap-prefix route and exclusive preflight route; the
  preflight schema retained exactly two required string fields with
  `additionalProperties=false`; an invalid registered call returned
  `input_error` with `realm_id_invalid`.
- Remote delivery:
  merge commit `2dc394e0a5a529c21d54ccc2faab8ecef73d4367` was pushed to
  `origin/feature/mcp-realm-agent-governance-preflight`. Draft PR `#18`
  then reported `OPEN`, `CLEAN`, and `MERGEABLE` against `main`.
- Status:
  `committed`, `pushed`, `backend_qa_pending`; independent re-QA is required.
  No PR merge, deployment, live backend call, realm mutation or Onto write
  was performed.
- The final evidence-only branch head is intentionally reported externally
  after its push.

## Risks

- Independent QA must re-check the exact pushed identity in an approved QA
  environment before any deployment decision.
- The post-deploy Constitutional Steward successor/repair and finding closure
  remain separate owner-governed work and must not be inferred from a
  structural preflight pass.
- No fallback, backward compatibility, dual-shape handling, transitional
  adapter, alternate endpoint or legacy path was introduced.

## Commit Description (English)

- Add read-only realm-agent governance proposal preflight

## Handoff

- Orchestrator: record the exact pushed branch head and route an independent
  QA Contract Handoff.
- Backend QA: validate the exact pushed identity with isolated fixtures,
  before/after read-only ledgers and no mutation.
- Owner: any deploy or later live governance repair remains a separate
  explicit gate.
