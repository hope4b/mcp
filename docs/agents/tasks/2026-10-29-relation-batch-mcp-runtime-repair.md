# Task: repair the relation batch runtime contract regression

## Task
- Operation: `implementation:mcp:1`; resident `mcp-owner`, runtime mode.
- Repair `MCP-REVIEW-000-1` / `BR-012` in this MCP repository only.
- Locked anchor: realm `000ba00a-00a0-0a00-a000-000a0a0a0aa3`, Feature
  `9529e47d-064c-44bd-a039-08b4f552eb52`.
- No publication, deployment, merge, task-ledger change or functional QA.

## Context Used
- Required project files read in order: AGENTS.md, ROLES.md,
  PROJECT_CONTEXT.md, ARCHITECTURE_MAP.md, TEST_STRATEGY.md; task template,
  inherited implementation note, runtime tests and assigned artifacts.
- Supplied accepted/current Constitution `b826563c-f1ab-47ec-a994-0dfe86662833`,
  Registry `4b2edeff-fe1c-4419-a607-22843ffe27d6`, exact valid active/execution
  mcp-owner row/verdict, Charter `656fdd41-a025-4f1e-8e44-b804c0657a0a`.
  Governance was acknowledged from the bundle and not reread.
- `../authority.json` SHA256 matched
  `a96215ac019caf42571b00e89b7dd96710161c8cc7ea892648c61f5a03a67ffc`.
  Exact role, mode, operation, scope, source snapshots, gates/output inspected.
- All 11 supplied source-file sizes/hashes and all seven artifact body hashes
  verified. Native receiver and MCP Owner bootstrap read from supplied process
  source `63033a506e389f8c6b35d74c68339a7b244d4276`. The controller owns
  private active-capability validation and output persistence.
- Current package `356a8f13-e6c9-4a8a-bf45-be8479ae6ab5` preserves the original
  specification/start decisions through revision
  `593b2ccd-b893-49d9-9b55-df6a5c3128a3`; no new product/environment gate.
- Attempt parent `5407b07fb705dd2176f916cb11ce7bdb40f4dd19`, starting tree
  `5d167a70999f3efa6d3ba48af71c8abb01169620`, clean at entry. Assigned main,
  original/effective base `50d57adbd99d4f67f2ef8c2a52b6470c21a7a1a6` already
  an ancestor: no incorporation needed; prior candidate ancestry preserved.

## Changes
- `tests/test_server_runtime.py`: expect the approved 70-tool inventory; replace
  missing `GENERIC_QA_BASELINE_ROOT` with a committed independent 69-tool golden.
  Permit exactly `create_relations_batch`; retain exact comparisons of all
  existing metadata, input/output schemas, success/error envelopes and protocol
  fields. No checks skipped; candidate is never its own baseline.
- `tests/fixtures/public_tool_contract.json` and `.md`: complete golden and
  provenance/capture procedure from original pre-batch source. Capture runtime
  versions remain provenance, not a Python-patch compatibility gate. Actual
  changes to dependency-generated tool fields/envelopes still fail.
- No runtime semantics or architecture changed; DECISIONS.md needs no update.

## Validation and artifacts
- Controller review evidence already established the inherited adapter checks
  passed and identified two runtime failures: obsolete inventory count and
  missing baseline environment. Those failures are retained here as diagnosis.
- `python3 -m compileall -q tests/test_server_runtime.py`: passed.
- `git diff --check`: passed before commit.
- Independent baseline capture without timer: timed out after 45 seconds with
  subprocess.TimeoutExpired. This reproduces the inherited local worker-wakeup
  limitation, not a functional FAIL.
- Independent capture with local periodic timer: completed, 69 records,
  FastMCP 4.0.10 / Python 3.12.14; exact golden SHA256 and procedure in
  `tests/fixtures/public_tool_contract.md`. Raw capture evidence:
  `/tmp/mcp-runtime-repair-baseline-assisted.log`.
- Unassisted bounded runtime suite command:
  `timeout 55 /tmp/mcp-batch-16158580-py312/bin/python -m pytest tests/test_server_runtime.py -q`
  timed out (124) with no completed case, consistent with that local limitation.
  Evidence: `/tmp/mcp-runtime-repair-unassisted.log`.
- Timer-assisted local command:
  `PYTHONPATH=/tmp:. timeout 55 /tmp/mcp-batch-16158580-py312/bin/python -m pytest -p mcp_runtime_repair_wakeup tests/test_server_runtime.py -q`
  passed all 19 tests, one warning. Evidence:
  `/tmp/mcp-runtime-repair-assisted.log`. Local plugin
  `/tmp/mcp_runtime_repair_wakeup.py` imports the inherited timer fixture and
  adds the same timer to the subprocess probe. It changes no production code,
  request, result, metadata or comparison. It is not committed; controller runs
  the exact committed test source independently. No unassisted PASS is claimed.

## Handoff
- Register `tests/test_server_runtime.py`, retaining the inherited adapter,
  guidance and HTTP credential regression files in controller technical checks.
- Next owner: independent MCP implementation reviewer after controller checks;
  QA-agent owns separate candidate/PREPROD functional QA; Orchestrator routes.
- Local timer-assisted execution is not independent review, QA PASS or deployed
  evidence. No credential availability, PREPROD readiness or persistence claim.
- Temporary commands bounded by timeout and stopped; evidence/data preserved.

## Commit Description (English)
Commit description (EN): Repair the relation batch runtime contract baseline.
