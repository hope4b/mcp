# Configurable delegated OAuth implementation

## Task

- Objective: implement the approved OAuth MCP contract, preserving existing
  tool arguments, DTOs and operation-specific behavior.
- Task/operation: `8f5978e8-36c6-4e1a-9e33-5441e65e46dc` / `implementation:mcp:0`.
- Scope: this MCP repository, runtime, guidance, local checks and candidate Git commit.
- Out of scope: Core/Web UI, live provider configuration, application data,
  independent QA, publication, PRs, pushes, deployment, merges and governance.

## Context Used

- AGENTS.md, ROLES.md, PROJECT_CONTEXT.md, ARCHITECTURE_MAP.md,
  TEST_STRATEGY.md and TASK_TEMPLATE.md read.
- Native assignment `../authority.json` SHA256 verified:
  `fd55b98e105b96767c82750abed2ad9478d1c5565406e3414cde48e758698d95`.
- Process source `b9984318abb3bdbaabfb7b29817f0ad61b1adaa7`: exact MCP bootstrap,
  FEATURE_PIPELINE_RECEIVER and process AGENTS. All eleven pinned source files'
  lengths/hashes and seven material body references verified. No other process
  receiver or governance reread was used.
- Supplied accepted/current bundle: Constitution
  `b826563c-f1ab-47ec-a994-0dfe86662833`, Registry
  `4b2edeff-fe1c-4419-a607-22843ffe27d6`, Charter
  `656fdd41-a025-4f1e-8e44-b804c0657a0a`; exact resident `mcp-owner`,
  valid/active/execution. Territory is MCP runtime/tools/guidance and HTTP tract.
- Locked anchor: realm `000ba00a-00a0-0a00-a000-000a0a0a0aa3`, feature
  `528303fe-678c-445c-bd76-e96a22aca27a`. No discovery/substitution or INTERNAL call.
- Specification and implementation gates both bind package
  `f1acd520-10d4-4f29-b33f-3c36ee3f80b5` /
  `68e3878b25b6dcaf0eb77e8974cab2c42f861e8da7725ce4c7ae7d6adeff017b`.
  Historical artifact wording grants no additional authority.
- Original base, attempt parent, assigned main and effective base are all
  `4dcb0e5b63521a8a6fefc4afa67ece5af6081b5c`, tree
  `4327c930a8dd0afd0739b8aeb5f4e0d87d350c1c`. No incorporation needed: all
  supplied lineage identities agree and the worktree started clean. No fetch,
  upstream advancement, alternate base or feature-candidate baseline was used.

## Changes

- `oauth.py`: configurable trust, issuer-bound RS256/JWKS verification, strict
  duplicate-free JSON/claim parsing, exact introspection comparison and failure
  classes, fresh protected-call authorization, explicit scope inventory,
  connection-key isolation, subject-preserving exchange and bounded reuse.
- `oauth_http.py`: concurrent key/OAuth transport classification and discovery.
  OAuth stateless FastMCP requests use durable MCP-owned public session IDs;
  key transport sessions retain their existing behavior. Both application
  lifespans are entered/exited; maintenance workers are cancelled on shutdown.
- `oauth_state.py` / `sql/oauth_state.sql`: PostgreSQL ownership, transactional
  helper saves/revisions, cryptographic 32-byte session IDs, fixed first-save
  timestamps/lifetime, unconditional 30-second sweeps, unused-binding purge,
  fail-closed storage/maintenance readiness and inactive-connection removal.
  PostgreSQL DDL/provisioning is delivered, never executed here.
- Existing registration and canonical request boundaries enforce scopes and
  delegated-only Core authentication, including specialized adapters. Workers
  carry request authority and deny sends after cancellation/timeout. Final
  authorization follows exchange/storage waits. No automatic mutation replay.
  Established-call OAuth errors survive adapters that catch dependency errors.
- `oauth_policy.py`: non-secret represented authorization/storage prerequisites,
  with configured Core consent=false, external consent=true, all three stock
  impersonation-note mappings, issuance restrictions and earlier-grant invalidation.
  It is not a live provider validator or an import-ready realm replacement.
- Connector/how-to instructions and write descriptions cover grounded selection,
  clarification, cancellation, save defaults and conversational confirmation.
  No confirmation arguments, pending state, effects compiler or permission store.
- Preserved 70 tools/two resources, 28 read tools and 42 read+write tools;
  existing schemas, DTOs, projections and deterministic success/error envelopes.
- Added synthetic auth, concurrency, HTTP transport and transactional-store tests.
  Updated inherited metadata assertions to allow exactly the specified
  scope/safety/guidance additions while keeping the independent golden intact.
  Updated the admission HTTP probe to supply a synthetic transport key.

## Validation

- Runtime available: Python 3.14.4; FastMCP 4.0.10, PyJWT 2.10.1,
  cryptography 50.0.1, psycopg 3.3.8, pytest 9.1.1. Docker declares Python 3.11;
  no container build or Python 3.11 execution was performed.
- `python -m compileall -q onto_mcp`: exit 0.
- Ruff on all eight new Python modules/test sources: exit 0, all configured
  rules pass. Explicit broad exception boundaries intentionally discard
  credential-bearing dependency diagnostics rather than logging them.
- `python -m ruff check --select E9,F63,F7,F82 onto_mcp tests`: exit 0.
- Black sequential API checks on the eight new Python files: exit 0.
  Initial Black multiprocessing was denied by sandbox socket permissions;
  sequential formatting avoided that environmental prerequisite.
- `git diff --check`: exit 0 before candidate commit.
- Final full suite through the recorded timer runner:
  `timeout 180s python /tmp/mcp_pytest_heartbeat.py -q`: exit 1,
  **562 passed, four failing subtests of one loopback-socket test**, one warning.
  All four failures are `PermissionError: [Errno 1] Operation not permitted`
  creating AF_INET sockets in
  `test_fake_core_receives_every_accepted_whitespace_value_byte_exactly`.
  They remain failures; no checks or assertions were skipped to turn them green.
- Earlier ordinary pytest/TestClient and asyncio.to_thread runs hung. The same
  TestClient hang reproduced on the exact original baseline extracted to
  `/tmp/mcp-oauth-baseline`; even a standalone repeated asyncio.to_thread probe
  hung, and socket.socketpair was denied. A timer-only event-loop policy in a
  temporary runner supplies wakeups, also to unchanged Python subprocess probes.
  It changes no test selection, assertions, dependency outcomes or exit statuses.
  Exact runner source is retained in the task-local evidence file below.
- Initial implementation failures included a missing write classification,
  then approved metadata differences against the inherited golden and a missing
  synthetic key in the HTTP probe. Those were diagnosed/repaired; comparison
  also found two unintentional multiline docstring differences, repaired with
  inspect.getdoc. Earlier unadapted full run: 73 failed / 554 passed / four errors;
  intermediate run: six failed / 558 passed. Final source has only the four
  environmental socket subtest failures described above.
- Formal tests include real local FastMCP protocol/metadata/helper/resource
  boundaries with inert provider/storage doubles, not real Onto operations.
  No live OAuth/Core/provider/DB request, token issuance/revocation, deployment,
  HTTP smoke against PREPROD, independent QA or catalogue activity occurred.

## Artifacts

- This task note: `docs/agents/tasks/2026-11-05-configurable-oauth-implementation.md`.
- Full final test output: `docs/agents/tasks/2026-11-05-oauth-validation.txt`.
- Exact local timer runner: `docs/agents/tasks/2026-11-05-oauth-test-runner.txt`.
- Non-secret configuration deliverable: `onto_mcp/oauth_policy.py`.
- Provisioning deliverable: `sql/oauth_state.sql`.
- Exact committed test sources are selected in the implementation result's
  `technical_checks`; the controller runs those separately before review.

## Risks and Handoff

- These are developer checks, not independent QA or a functional OAuth verdict.
- Next owner: independent MCP implementation reviewer, then qa-agent for the
  separately gated candidate and PREPROD formal QA stages. Recheck the exact
  candidate and all reported socket failures in the registered executor.
- T1-C Core template authorization remains unresolved and backend-owned.
  Fixed-audience ChatGPT compatibility remains unverified. Both are accepted
  risks, not repaired conditions or renewed product questions.
- Provider/client compatibility, actual issuance/mapper configuration and prior
  authorization transition, delegated Core acceptance, actual domain permissions,
  PostgreSQL durability/replicas/retention/encryption/backups, real renewal and
  revocation, client adherence/confirmation and catalogue acceptance remain
  unverified. Separately assigned authorization, deployment and publication
  owners retain their delivery prerequisites and gates.
- No owner questions. No temporary service was started. All temporary test
  runners/threads completed or were stopped; failed timeout evidence is retained.

## Commit Description (English)

Commit description (EN): Add configurable delegated OAuth with isolated MCP session state
