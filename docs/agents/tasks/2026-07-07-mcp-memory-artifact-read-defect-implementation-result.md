# MCP MemoryArtifact Read Defect - Implementation Result

## Task
- Short objective: tighten MCP MemoryArtifact-vs-AgentMemory runtime/tool guidance under the existing contract.
- Scope: runtime how-to guidance, canonical agent contract text, human guidance docs, QA catalog wording, and regression tests.
- Out of scope: backend changes, new endpoints, fallback, compatibility parsing, alternate endpoints, legacy paths, deploy, PR, push, QA verdict, done closure, and Onto milestone writes.

## Bootstrap Acknowledgement Summary
- Role: MCP runtime developer / MCP Owner implementation role.
- Process source: `onto-docs/main`.
- Runtime repo: `/home/ubuntu/git/onto/_platform/mcp`.
- Deploy repo: `/home/ubuntu/git/onto/_platform/mcp-server`.
- Implementation handoff: `/home/ubuntu/git/onto/_platform/onto-docs/docs/agents/tasks/2026-07-07-mcp-memory-artifact-read-defect-implementation-handoff.md`.
- Gate status: Change Spec not required for the narrow fix; owner implementation approval received; runtime implementation only; deploy not applicable.
- Onto anchor received and locked:
  - role: `primary_change_object`
  - realm_id: `000ba00a-00a0-0a00-a000-000a0a0a0aa3`
  - object_id: `a221776b-193e-4827-827f-ceaa6e6527ca`
  - object_code: `MCP MemoryArtifact read defect`
  - substitution allowed: no

## Context Used
- `AGENTS.md` read: yes.
- `docs/agents/ROLES.md` read: yes.
- `docs/agents/PROJECT_CONTEXT.md` read: yes.
- `docs/agents/ARCHITECTURE_MAP.md` read: yes.
- `docs/agents/TEST_STRATEGY.md` read: yes.
- `docs/agents/HANDOFF.md` read: yes.
- `docs/agents/WORKLOG.md` latest entries read: yes.
- Required process and handoff files in `onto-docs` read before implementation: yes.

## Changes
- Files changed:
  - `onto_mcp/agent_contract.py`
  - `onto_mcp/agent_contract.json`
  - `docs/AGENT_ENTRY_GUIDE.md`
  - `docs/income/QA_MCP_TOOL_CATALOG.md`
  - `tests/test_agent_contract.py`
  - `docs/agents/tasks/2026-07-07-mcp-memory-artifact-read-defect-implementation-result.md`
  - `docs/agents/WORKLOG.md`
  - `docs/agents/HANDOFF.md`
- Behavioral impact:
  - `how_to_use_onto_mcp` now explicitly routes MemoryArtifact reads through `search_memory_artifacts`, `get_memory_artifact_by_path`, and `get_memory_artifact`.
  - Runtime guidance now explicitly says `search_agent_memory` and `get_agent_memory_record` are for canonical AgentMemory records, not MemoryArtifacts.
  - MemoryArtifact target search guidance no longer propagates unsupported `target_kind=node`; object/node-scoped MemoryArtifact searches are guided to `target_kind=entity` with the object id as `target_id`.
  - Path-based accepted-current lookup is called out as `get_memory_artifact_by_path`.
  - Added regression tests for MemoryArtifact id read, path read, and node/object target wording.
- Risks:
  - This is guidance/routing coverage only. No live backend or deployed HTTP MCP smoke was performed.
  - The shell prints `/home/ubuntu/.profile: line 28: nexport: command not found` before commands; it did not affect command exit status.
  - The `python` executable is unavailable in this environment, so equivalent checks were run with `python3`.

## Validation
- Commands run:
  - `python -m unittest tests.test_agent_contract`
  - `python3 --version`
  - `python3 -m unittest tests.test_agent_contract`
  - `python3 -m unittest discover -s tests -p "test_*.py"`
  - `python3 -m compileall onto_mcp`
  - `git diff --check`
- Result:
  - `python -m unittest tests.test_agent_contract`: blocked because `/bin/bash: line 1: python: command not found`.
  - `python3 --version`: `Python 3.14.4`.
  - `python3 -m unittest tests.test_agent_contract`: passed, 20 tests.
  - `python3 -m unittest discover -s tests -p "test_*.py"`: passed, 74 tests.
  - `python3 -m compileall onto_mcp`: passed.
  - `git diff --check`: passed.
- Not run and why:
  - Live stdio or HTTP MCP smoke was not run because the handoff requested local runtime/tool-guidance checks only and deploy/live QA were out of scope.
  - Onto milestone write was not run because the handoff forbids writing Onto milestones unless explicitly assigned after implementation is reported.

## Delivery Status
- Status: `implemented_locally`.
- Commit status: not committed.
- Push status: not pushed.
- Deploy status: not deployed.
- QA verdict: not written.
- Done status: not closed.

## Commit Description (English)
- Short commit description: Clarify MemoryArtifact read routing guidance.

## Handoff
- Remaining work:
  - Owner/orchestrator may review the local diff and decide whether to commit, push, route QA, or deploy in a later gate.
  - Live MemoryArtifact smoke with a backend-accepted key remains outside this implementation result.
- Recommended next owner (area): MCP Owner / QA routing after owner approval.
