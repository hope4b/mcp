# Task: cover mixed relation batch results through the MCP protocol

## Task
- Operation: `implementation:mcp:2`, resident `mcp-owner`, runtime mode.
- Repair `QA-CANDIDATE-BR010-MIXED-PROTOCOL`, case `BR-010-candidate`.
- Scope: MCP protocol test only; no runtime, product or environment change.
- Locked anchor: realm `000ba00a-00a0-0a00-a000-000a0a0a0aa3`, Feature
  `9529e47d-064c-44bd-a039-08b4f552eb52`; no anchor discovery/substitution.
- No push, PR, merge, deployment, task-ledger change or functional QA.

## Context Used
- Required project guidance read in order: AGENTS.md, ROLES.md,
  PROJECT_CONTEXT.md, ARCHITECTURE_MAP.md, TEST_STRATEGY.md; task template,
  assigned artifacts, existing protocol fixture and adapter source.
- BootstrapBundle acknowledges accepted/current Constitution
  `b826563c-f1ab-47ec-a994-0dfe86662833`, Registry
  `4b2edeff-fe1c-4419-a607-22843ffe27d6`, valid active/execution mcp-owner
  row/verdict and Charter `656fdd41-a025-4f1e-8e44-b804c0657a0a`.
  These governance documents were not reread.
- `../authority.json` matched SHA256
  `fcdc8537f4f4e0e576b0f8008c1a007a19d63ac7261862ec5196b8c1248c5ad6`.
  Inspected exact role, mode, operation, scope, gates, output and lineage.
- Verified all 12 pinned source sizes/hashes and eight artifact body hashes.
  Native receiver and MCP Owner bootstrap read at supplied process source
  `a2f197c8c8ccbb72969c42e2d4b30f117612802a`. The controller owns private
  capability validation and result persistence.
- Current package `356a8f13-e6c9-4a8a-bf45-be8479ae6ab5` and revision
  `593b2ccd-b893-49d9-9b55-df6a5c3128a3` retain original specification/start
  gates; this test repair adds no permission or requirement.
- Clean attempt parent `0fe4cc9f834b0c6b8ef176a3947cb3b30e030b9f`, tree
  `807edec435b153d455cb8fc8e75f91160cc88c53`. Assigned main/original/effective
  base `50d57adbd99d4f67f2ef8c2a52b6470c21a7a1a6` is already an ancestor;
  incorporation is unnecessary and prior candidate ancestry is preserved.

## Changes
- Extend the existing FastMCP Client fixture with an ordered array containing
  two valid relation DTOs around an invalid item, and SUCCESS/ERROR/SUCCESS
  Core output. Check tools/list, exact structuredContent and isError:false.
- Assert exactly one canonical POST with the complete unchanged envelope,
  credential headers, redirect policy and timeouts. Snapshot expected input
  before invocation to catch mutation; retain whitespace, roles, property
  overrides and endpoint order. Retain the all-ERROR and protocol validation
  controls. Register `tests/test_relation_batch.py` for controller execution.
- No runtime semantics or architecture changed; no DECISIONS update needed.

## Validation and artifacts
- `python3 -m compileall -q tests/test_relation_batch.py`: passed.
- `git diff --check`: passed.
- Unassisted suite: `timeout 25 /tmp/mcp-batch-16158580-py312/bin/python -m pytest tests/test_relation_batch.py -q`
  returned 124 after recording failures; log
  `/tmp/mcp-br010-protocol-unassisted.log`.
- Focused unassisted new test: `timeout 18 /tmp/mcp-batch-16158580-py312/bin/python -m pytest tests/test_relation_batch.py::test_real_mcp_mixed_results_preserve_valid_relations_and_one_post -q`
  returned 1: MCPError, Request 'tools/call' timed out; one failed test in
  6.93 seconds. Log: `/tmp/mcp-br010-mixed-unassisted.log`.
- Timer-assisted final source: `PYTHONPATH=/tmp:. timeout 40 /tmp/mcp-batch-16158580-py312/bin/python -m pytest -p mcp_batch_local_wakeup tests/test_relation_batch.py -q`
  returned 0: 50 passed, one warning in 2.49 seconds. Log:
  `/tmp/mcp-br010-protocol-assisted.log`. The inherited local-only plugin
  `/tmp/mcp_batch_local_wakeup.py` adds periodic asyncio timer wakeups. It does
  not change assertions or transport collaborators and is not committed.
  This matches the prior local worker-wakeup diagnosis, but is no unassisted
  PASS or independent QA verdict. Failed observations remain review evidence.
- All temporary test processes completed or were stopped by bounded timeout;
  no live environment or credentials were used, and task data was preserved.

## Handoff
- Next owner: controller technical-check executor, then independent MCP
  reviewer; QA-agent owns fresh candidate and mandatory PREPROD functional QA.
- Reassess the exact new candidate; prior review is historical evidence.
- No new owner questions. Local unassisted protocol execution remains a
  limitation requiring independent executor assessment.

## Commit Description (English)
Commit description (EN): Cover mixed relation batch results through MCP.
