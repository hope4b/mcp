# Task: correct the post-batch admission inventory regression

## Task
- Short objective: resolve QA-CANDIDATE-MCP-STALE-TOOL-INVENTORY for BR-012-candidate, operation implementation:mcp:3.
- Scope: admission transport test inventory expectation and local regression evidence.
- Out of scope: runtime/public-contract changes, independent QA, publication, deployment, merge and governance mutations.

## Context Used
- AGENTS.md, ROLES.md, PROJECT_CONTEXT.md, ARCHITECTURE_MAP.md and TEST_STRATEGY.md read: yes.
- Verified ../authority.json SHA256 940b40aedbf5aadf903ff225ffef92761c8d3fb47ad729bf137043167c81f89a; all 12 pinned source files and eight artifact body hashes matched.
- Read the native receiver and MCP Owner bootstrap from the pinned process source. Supplied accepted/current BootstrapBundle identifies active/execution mcp-owner; locked anchor 9529e47d-064c-44bd-a039-08b4f552eb52 remains unchanged.
- Current specification package 356a8f13-e6c9-4a8a-bf45-be8479ae6ab5 and supplied technical revision retain the original specification/start decision scope. Repair evidence: 3c3cf172-8e8b-4d78-9085-6c1a86c095aa.
- Attempt parent: 4ffb872a90e2d128ccd9d1ff0486caca5cb62f58; tree cd73f5e1bcbd29a36991aa120ae7e5b3f658add8. Assigned main/original/effective baseline 50d57adbd99d4f67f2ef8c2a52b6470c21a7a1a6 is already an ancestor; no incorporation needed.

## Changes
- tests/test_realm_agent_admission_schema_transport.py: expect 70 live tools, accounting for the approved create_relations_batch addition to the 69-tool pre-batch inventory.
- Preserve exactly-once admission registration, the closed two-argument schema, recursive closure, protocol validation and exact POST assertions.
- Preserve the unchanged live-inventory probe and independent pre-batch golden comparison in tests/test_server_runtime.py. The golden still has 69 tools and requires create_relations_batch as the sole addition with every pre-existing tool record unchanged.
- Behavioral impact: test expectation only; no production behavior or MCP semantics changed.
- Risks: local transport execution may stall; no local PASS is inferred from timeouts or earlier controller observations.

## Validation
- Python 3.12.14 from /tmp/mcp-batch-16158580-py312/bin/python; declared requirements inspected.
- Assignment/source integrity and assigned-main ancestor checks passed.
- compileall of the changed test and git diff --check passed.
- Focused command: timeout 30 /tmp/mcp-batch-16158580-py312/bin/python -m pytest tests/test_realm_agent_admission_schema_transport.py -q.
- Focused result: exit 124 after collecting five tests, before any test outcome; evidence /tmp/mcp-inventory-admission-regression.log. This is an execution limitation, not PASS.
- Full command: timeout 180 /tmp/mcp-batch-16158580-py312/bin/python -m pytest -q.
- Full result: exit 124 after collecting 329 tests; output stalled in tests/test_http_onto_api_key_passthrough.py after earlier tests passed. Evidence: /tmp/mcp-inventory-full-regression.log. No full-suite PASS, timer workaround or suppression was applied.
- These are developer checks only; candidate/PREPROD functional QA remains separate.

## Commit Description (English)
- Correct admission tool inventory after relation batch addition.

## Handoff
- Register admission schema, admission HTTP/wrapper, public runtime contract, relation batch, guidance and HTTP passthrough test-source files for controller technical execution. Full registered regression remains requested by the finding.
- Remaining work: controller technical execution, independent review, fresh candidate QA and mandatory PREPROD QA against the resulting exact candidate/composition.
- Recommended next owner: independent MCP reviewer, then qa-agent through the native controller.
- No push, PR, deployment or merge. Both temporary test runs exited under timeout; no temporary server was started.
