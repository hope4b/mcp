## Task
- Objective: repair MCP-REVIEW-01, MCP-REVIEW-02 and MCP-REVIEW-03 from implementation_review:mcp:0.
- Scope: implementation:mcp:1, MCP OAuth state recovery, post-lock validity and delegated final-send validity; regression tests and evidence.
- Out of scope: Core/Web UI, provider operations, deployment, publication, independent QA, governance and task ledgers.

## Context Used
- AGENTS.md, ROLES.md, PROJECT_CONTEXT.md, ARCHITECTURE_MAP.md, TEST_STRATEGY.md and TASK_TEMPLATE.md read; no nested AGENTS.md present.
- Native entry: process MCP_OWNER_BOOTSTRAP_TEMPLATE.md, then FEATURE_PIPELINE_RECEIVER.md; other receiver entries inapplicable.
- ../authority.json SHA256: 44c6a50076e11a9051fc310022cac12bc87e67b2282314dfb5a53f1adcb3b2c2. All 13 pinned source lengths/hashes and nine material body hashes verified; process HEAD b9984318abb3bdbaabfb7b29817f0ad61b1adaa7 matched. Role/mode/workspace/operation/permissions, specification and implementation gate references match this bounded native run. Controller owns private capability validation and result persistence.
- Supplied BootstrapBundle accepted/current Constitution b826563c-f1ab-47ec-a994-0dfe86662833, Registry 4b2edeff-fe1c-4419-a607-22843ffe27d6, valid active/execution mcp-owner row/verdict and Charter 656fdd41-a025-4f1e-8e44-b804c0657a0a acknowledged without rereading governance. Territory: MCP runtime/toolset/HTTP/guidance and MCP-scoped evidence. Locked anchor 528303fe-678c-445c-bd76-e96a22aca27a in realm 000ba00a-00a0-0a00-a000-000a0a0a0aa3 retained without INTERNAL access.
- Exact package f1acd520-10d4-4f29-b33f-3c36ee3f80b5@68e3878b25b6dcaf0eb77e8974cab2c42f861e8da7725ce4c7ae7d6adeff017b and repair review 77a3cc7c-d3a2-47e5-96e3-282690c63659@adceea6fb2f0eb53436ce3d672717e65628e077aa6dbe5e29c4246baa308c6fc supplied as evidence.
- Clean starting HEAD/tree: 2518bfe3ccb65a4e8ed3cdaa689ba5f1f664947f / 824b23e6821e7e7ec7f606a9fd9df2ebad67037e. Original/effective/assigned main remains 4dcb0e5b63521a8a6fefc4afa67ece5af6081b5c. No main incorporation needed; prior candidate ancestry retained.

## Changes
- onto_mcp/oauth_state.py retains pending inactive-owner invalidations through deletion failures. Serialized maintenance deletes pending owners transactionally with age cleanup, evicts caches and clears pending work only after success, before readiness recovers.
- Locked session reads return persisted expiry and check fresh time and maintenance readiness after SELECT FOR UPDATE completes, before helper disclosure or update.
- onto_mcp/oauth.py returns the selected delegated credential together with its bounded deadline, including cached selection and current original-token expiry. onto_mcp/api_resources.py checks that deadline after storage waits and final fresh introspection, immediately before its single protected request; expiry fails safely without replay.
- tests/test_oauth_state.py covers failed invalidation, failed recovery, eventual deletion, and barrier-controlled row-lock waits across expiry/maintenance bounds for reads and writes. tests/test_oauth_authorization.py covers both token-expiry and cache-deadline crossings during storage/final-introspection waits, for cached and newly exchanged credentials, with zero mutation sends and one exchange.
- No new public contract, architecture or semantics decision: these repairs enforce the already approved AC-04/AC-08 contract.

## Validation
- Assignment/source/body identity verification: passed.
- python -m pytest -q tests/test_oauth_state.py tests/test_oauth_authorization.py: 239 passed.
- python -m compileall -q onto_mcp: passed.
- python -m ruff check onto_mcp/oauth.py onto_mcp/oauth_state.py tests/test_oauth_state.py tests/test_oauth_authorization.py: passed.
- python -m ruff check --select E9,F63,F7,F82 onto_mcp tests: passed.
- timeout 45s python -m pytest -q: exit 124 at inherited HTTP asynchronous boundary. This matches the prior implementation's documented baseline hang.
- timeout 120s python /tmp/mcp_oauth_repair_pytest.py -q: exit 1, 575 passed, four failed loopback subtests, one warning. Runner is an exact copy of the inspected committed docs/agents/tasks/2026-11-05-oauth-test-runner.txt, adding timer wakeups only; no assertions, selections, failures or exit codes suppressed. Complete output: docs/agents/tasks/2026-11-06-oauth-repair-validation.txt. All four failures are socket.AF_INET creation denied by sandbox at tests/test_http_onto_api_key_passthrough.py:173, retaining the prior baseline diagnosis. No code/test change to hide these restrictions.
- Runtime: Python 3.14.4; Dockerfile declares Python 3.11. Container/runtime-version verification and live provider/PostgreSQL testing were not performed.
- git diff --check: passed. No temporary services started; both bounded test processes exited.

## Commit Description (English)
- Close OAuth maintenance and delegated credential expiry races.

## Handoff
- Next owner: independent implementation reviewer after controller execution of committed technical-check paths. Separate mandatory candidate and PREPROD QA remain pending.
- Keep T1-C Core template authorization and fixed-audience ChatGPT compatibility as accepted, unverified risks. Formal tests establish no live OAuth/provider/Core interoperability, operational storage/backup behavior or catalogue readiness.
- Separately gated authorization configuration, PostgreSQL provisioning, publication and deployment remain delivery obligations. No owner question, permission expansion, agent launch, approval, push, PR, merge or deployment performed.
