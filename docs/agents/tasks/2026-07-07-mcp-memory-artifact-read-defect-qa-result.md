# MCP MemoryArtifact Read Defect - QA Result

## Verdict
QA PASS

## Environment
- Checked environment: local workspace only.
- Target project: `/home/ubuntu/git/onto/_platform/mcp`.
- QA mode: `post_implementation_contract_qa`.
- Local service started by owner: not applicable.
- Live HTTP MCP smoke: out of scope.
- Delivery state checked: implemented locally, not committed, not pushed, not deployed.

## Scope
- Validated the implemented MCP MemoryArtifact guidance/routing change against the QA handoff.
- Confirmed MemoryArtifact read/search guidance routes to dedicated MemoryArtifact tools:
  - `search_memory_artifacts`
  - `get_memory_artifact_by_path`
  - `get_memory_artifact`
- Confirmed canonical AgentMemory tools are not recommended as MemoryArtifact read tools:
  - `search_agent_memory`
  - `get_agent_memory_record`
- Confirmed object/node-scoped MemoryArtifact target search guidance uses supported `target_kind=entity`, not unsupported `target_kind=node`.

## Files And Diff Inspected
- `onto_mcp/agent_contract.py`
- `onto_mcp/agent_contract.json`
- `docs/AGENT_ENTRY_GUIDE.md`
- `docs/income/QA_MCP_TOOL_CATALOG.md`
- `tests/test_agent_contract.py`
- `docs/agents/tasks/2026-07-07-mcp-memory-artifact-read-defect-implementation-result.md`
- `docs/agents/HANDOFF.md`
- `docs/agents/WORKLOG.md`

Unrelated/unreviewed working tree items observed and not treated as part of this QA verdict:
- `docs/agents/tasks/2026-07-06-get-diagram-representation-details-qa-gate-1.md`
- `docs/agents/tasks/2026-07-06-get-diagram-representation-details-qa-gate-2.md`

## Evidence
- `python3 -m unittest tests.test_agent_contract`
  - Result: PASS
  - Evidence: ran 20 tests, OK.
- `python3 -m unittest discover -s tests -p "test_*.py"`
  - Result: PASS
  - Evidence: ran 74 tests, OK.
- `python3 -m compileall onto_mcp`
  - Result: PASS
  - Evidence: compileall completed successfully.
- `git diff --check`
  - Result: PASS
  - Evidence: no whitespace errors reported.

The shell emitted `/home/ubuntu/.profile: line 28: nexport: command not found` before commands. This did not affect command exit status.

## Skipped Checks
- Live HTTP MCP smoke: skipped because the QA handoff states it is out of scope.
- Deploy/preprod/prod checks: skipped because this QA gate is local-only and deploy is forbidden.
- Onto milestone write: skipped because the QA handoff states QA agent must not write Onto milestones; orchestrator owns any later milestone routing.
- Onto memory reads: not run because dedicated Onto MCP/memory tools are unavailable in the active tool list.

## Findings
- No blocking findings.
- No fallback, compatibility parser, dual-shape handling, alternate endpoint, legacy path, or backend route change was found in the inspected implementation diff.

## Delivery Reminder
- Status: `qa_passed` for local post-implementation contract QA.
- Code remains local only: implemented locally, not committed, not pushed, not deployed.
- Do not present a preprod/prod verification URL until the matching commit, push, deploy, and delivery gates are complete.
