# OAuth remaining formal-oracle completion

## Task
- Complete QA-CANDIDATE-13 (AC-01) and QA-CANDIDATE-14 (AC-02) for implementation:mcp:4.
- Scope: MCP isolated tests and this task-local evidence. Runtime, provider configuration, approved requirements and all prior regressions remain unchanged.
- Out of scope: live OAuth/Core/database operations, independent QA/review, publication, deployment, governance and task ledgers.

## Context Used
- AGENTS.md, ROLES.md, PROJECT_CONTEXT.md, ARCHITECTURE_MAP.md, TEST_STRATEGY.md and TASK_TEMPLATE.md read.
- Exact native assignment ../authority.json matched SHA256 2739132f0791945c013da77e408ec00d06da86684bb33ad304670f2aa4d9d349.
- All 14 pinned source sizes/hashes and ten material body hashes verified; process HEAD b9984318abb3bdbaabfb7b29817f0ad61b1adaa7 matched. Exact FEATURE_PIPELINE_RECEIVER.md read before hydration; other receiver entries inapplicable.
- Supplied accepted/current Constitution b826563c-f1ab-47ec-a994-0dfe86662833, Registry 4b2edeff-fe1c-4419-a607-22843ffe27d6, valid active/execution mcp-owner row/verdict, and charter 656fdd41-a025-4f1e-8e44-b804c0657a0a acknowledged without governance rereads.
- Locked realm/anchor 000ba00a-00a0-0a00-a000-000a0a0a0aa3 / 528303fe-678c-445c-bd76-e96a22aca27a retained.
- Specification/start gates bind f1acd520-10d4-4f29-b33f-3c36ee3f80b5@68e3878b25b6dcaf0eb77e8974cab2c42f861e8da7725ce4c7ae7d6adeff017b. Repair findings: a84b08f1-8b1d-4a4b-94a0-97918ee6180b@8806e31e1223685236959e4a93a75f6293f9ef348a0747108f96e96a474af26a.
- Starting candidate/tree: 00adc39b51c9c9f72766321f0a29a9100daa94ae / 37d6376cca393414a878d45b11fd8b7922d30dbc.
- Assigned main/original/effective base: 4dcb0e5b63521a8a6fefc4afa67ece5af6081b5c; already an ancestor, no incorporation needed. Prior candidate ancestry preserved.

## Changes
- tests/test_oauth_authorization.py asserts authorization-code enablement, exact 300/1800/28800-second represented lifetimes for both allowed external clients, and independent read/separately consented nondefault write with literal expected values.
- Four independently signed original-token policy faults use matching introspection fixtures: unknown client with valid session, wrong issuer, absent ingress audience and offline_access. Each requires exact 401 invalid_token, zero introspection/exchange/protected sends and empty exchange cache.
- Active introspection numeric-date range/type and malformed scope vectors run through authenticate with a valid original token, require exact 503 dependency_unavailable and exactly one introspection with no exchange.
- Replacement configuration, A=R, hostile inputs, concurrent clients, signed duplicate-member, identity/session-alias and provider-status regressions retained.
- No runtime semantics or canonical decisions changed.

## Validation
- Evidence: docs/agents/tasks/2026-11-06-oauth-final-completion-validation.txt.
- Python 3.14.4 available; Dockerfile declares Python 3.11, not exercised here.
- Initial ruff check passed; format check found wrapping only. Applied ruff formatter.
- Focused isolated tests and final static results recorded below after completion.
- Existing timer-wakeup runner preserves test assertions/selection/exit status; no provider transport, HTTP listener or database started.

## Commit Description (English)
- Complete OAuth represented-policy and ingress rejection test coverage.

## Handoff
- Next owner: independent implementation reviewer, then qa-agent for fresh candidate QA. Separate PREPROD QA remains mandatory.
- Controller technical checks use exact committed relative test-source paths; no independent QA or runtime OAuth PASS claimed.
- T1-C remains unresolved and backend-owned; fixed-audience ChatGPT compatibility, live OAuth/Core behavior and operational storage/backup behavior remain unverified.
- Provider configuration, state provisioning, publication and deployment remain separately gated. No new owner questions.

## Observed final results
- `timeout 90s python docs/agents/tasks/2026-11-05-oauth-test-runner.txt -q tests/test_oauth_authorization.py tests/test_oauth_http.py tests/test_oauth_formal_contracts.py tests/test_oauth_state.py tests/test_server_runtime.py`: exit 0, 434 passed, one warning, 5.78s. No failures or skips. Only formatting changed after that run.
- `python -m ruff check tests/test_oauth_authorization.py`: exit 0.
- `python -m ruff format --check tests/test_oauth_authorization.py`: initial exit 1 for wrapping/blank-line formatting; corrected with ruff format, final exit 0.
- `python -m ruff check --select E9,F63,F7,F82 onto_mcp tests`: exit 0.
- `python -m compileall -q onto_mcp tests`: exit 0.
- `git diff --check`: exit 0.
- Prior socket-restricted API-key transport subcases were not rerun: test-only completion does not change that path. Their prior failure diagnosis remains in inherited evidence. Retain the inherited eleven-source technical-check selection for controller reassessment of the full cumulative implementation.
- All started test processes completed; no temporary service remains.
