# OAuth formal-oracle repair

## Task
- Complete QA-CANDIDATE-03 through QA-CANDIDATE-12 for implementation:mcp:3.
- Scope: isolated tests in mcp only; preserve runtime, approved package and prior regressions.
- Out of scope: provider/Core operations, independent review/QA, deployment, publication and governance.

## Context Used
- AGENTS.md, ROLES.md, PROJECT_CONTEXT.md, ARCHITECTURE_MAP.md, TEST_STRATEGY.md and TASK_TEMPLATE.md read.
- Native ../authority.json SHA256: 33cbb89a9548ce1317baac233da7c11e3c33322017201ea302f66868605c8d11.
- All 14 pinned source lengths/hashes and ten material body hashes verified; process source b9984318abb3bdbaabfb7b29817f0ad61b1adaa7 verified.
- Supplied accepted Constitution, Registry, valid active/execution mcp-owner row and charter 656fdd41-a025-4f1e-8e44-b804c0657a0a used without rereading governance.
- Locked anchor 528303fe-678c-445c-bd76-e96a22aca27a retained. Specification and implementation-start references bind package f1acd520-10d4-4f29-b33f-3c36ee3f80b5@68e3878b25b6dcaf0eb77e8974cab2c42f861e8da7725ce4c7ae7d6adeff017b.
- Starting HEAD/tree: 7140a4641ff5a896ba815c7c335d3460f32d2d5e / 37f6fa2625f3fef74025fa78520e73518a9fdb46.
- Assigned main/original/effective base: 4dcb0e5b63521a8a6fefc4afa67ece5af6081b5c. Already an ancestor; incorporation unnecessary. Prior candidate ancestry preserved.

## Changes
- tests/test_oauth_authorization.py: correctly signed duplicate JSON fixture, independent signature verification, non-200 provider errors, signed/provider whitespace/control identities and malformed-present aliases, exchange signature/envelope faults with zero sends/cache retention, synthetic prior-grant/acknowledgement/active truth table.
- tests/test_oauth_http.py: one dual-auth app overlaps key and both OAuth clients at request and worker barriers; intercepted outbound authentication remains isolated. Repeat after replacing issuer/resource/audience/both clients/exchange/Core identities, parsing settings and checking discovery/trusted destinations, including A=R and hostile headers/arguments/session IDs. Validation/introspection/exchange faults cannot use available configured or stale ambient request/session keys.
- tests/test_oauth_formal_contracts.py: independent exact mapper/issuance and storage-policy inspection with adverse comparison samples; complete selection/confirmation/revocation passage oracles across connector/how-to/descriptions; misleading server-consent/pending-outcome comparison samples; actual current-user/realm projections; template/entity/batch mapping/default/omission/native-projection and DELETE request regressions with inert downstream responses; controlled no-traffic scheduler/shutdown test.
- docs/agents/tasks/2026-11-06-oauth-oracle-validation.txt: actual failed and passing outputs retained.
- Runtime and MCP semantics unchanged; no DECISIONS update required.

## Validation
- Initial targeted timer-runner execution: 368 passed, four failures. The new discovery oracle incorrectly required bearer_methods_supported, which the approved contract does not require. Removed that invented expectation; did not change runtime.
- Expanded timer-runner execution: 567 passed, four inherited socket subcase failures, one warning. tests/test_http_onto_api_key_passthrough.py::CanonicalProjectionTests::test_fake_core_receives_every_accepted_whitespace_value_byte_exactly fails at socket.socket with PermissionError (sandbox restriction), before transport assertions. No skip or suppression added. Retain the same source in technical_checks for controller reassessment.
- Final focused timer-runner execution: 400 passed, one warning. Selected tests/test_oauth_authorization.py, tests/test_oauth_http.py, tests/test_oauth_formal_contracts.py, tests/test_oauth_state.py and tests/test_server_runtime.py.
- Expanded run additionally selected tests/test_get_template_fields.py, tests/test_get_entity_related_entities.py, tests/test_clone_object_to_realm.py, tests/test_relation_batch.py, tests/test_agent_contract.py and tests/test_http_onto_api_key_passthrough.py.
- Runner: timeout 90s python docs/agents/tasks/2026-11-05-oauth-test-runner.txt -q followed by the exact sources above. Existing documented timer-only asyncio wakeup workaround; preserves assertions and exit status. All processes completed, none remain.
- python -m ruff check tests/test_oauth_authorization.py tests/test_oauth_http.py tests/test_oauth_formal_contracts.py: passed after automatic import cleanup.
- python -m ruff check --select E9,F63,F7,F82 onto_mcp tests: passed.
- python -m compileall -q onto_mcp tests: passed on Python 3.14.4; declared Python 3.11 Docker runtime not exercised.
- git diff --check: passed.
- No live provider, database, HTTP listener or external service was started. Formal checks establish neither live OAuth interoperability nor operational storage behavior.

## Commit Description (English)
- Complete isolated OAuth authorization and guidance regression oracles.

## Handoff
- Next owner: independent implementation reviewer, then qa-agent for fresh candidate QA; separate PREPROD QA remains mandatory.
- Reassess the socket-denied inherited checks in the controller executor. They are failure evidence, not PASS.
- T1-C remains unresolved and backend-owned; fixed-audience ChatGPT compatibility remains unverified. No new owner question.
- Provider configuration, state provisioning/encryption/backup retention, publication and deployment remain separately gated obligations. No push, PR, merge, deployment or independent QA performed.
- Artifacts: this note, docs/agents/tasks/2026-11-06-oauth-oracle-validation.txt, and the three edited/new test sources.
