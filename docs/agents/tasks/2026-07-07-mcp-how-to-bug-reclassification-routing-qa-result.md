# MCP how-to bug reclassification routing QA result

## Task
- Short objective: Validate the local MCP runtime guidance patch for owner-approved bug reclassification and safe defect creation routing.
- Scope: `how_to_use_onto_mcp(question, safety_mode)` contract guidance only.
- Out of scope: New endpoint/tool, backend change, fallback/compatibility/dual-shape/transitional adapter/alternate endpoint/legacy path/new architecture, commit, push, deploy, and live Onto mutation.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes
- Additional process files read: `onto-docs/AGENTS.md`, `ONTO_OBJECT_ANCHOR_CONTRACT.md`, `DEVELOPMENT_AFTER_APPROVAL_FLOW.md`, `QA_CONTRACT_HANDOFF_TEMPLATE.md`, `mcp/docs/agents/ROLES.md`, `TEST_STRATEGY.md`, `HANDOFF.md`, latest `WORKLOG.md`, and implementation result `docs/agents/tasks/2026-07-07-mcp-how-to-bug-reclassification-routing.md`.

## Onto Anchor
- Received: yes
- Object code: `MCP-how-to-reclassification-defect`
- Locked: yes
- Substitution allowed: no
- Milestone status: `qa_passed` written to locked object chat after dedupe read.

## Verdict
- `QA PASS`
- Environment: local workspace.
- Status: qa_passed locally; not committed, not pushed, not deployed.

## Diff Review
- Reviewed changed implementation scope:
  - `onto_mcp/agent_contract.py`
  - `onto_mcp/agent_contract.json`
  - `docs/AGENT_ENTRY_GUIDE.md`
  - `tests/test_agent_contract.py`
  - implementation/task docs
- Confirmed the code routes exact owner-approved single-object bug lifecycle/state reclassification through `get_entity -> save_entity -> get_entity` when required named inputs and lifecycle approval are present.
- Confirmed the code routes exact owner-approved safe defect creation under an existing bug template through `get_template -> save_entity -> get_entity` when required named inputs and write approval are present.
- Confirmed `read_only` mode keeps mutation tools out of `next_calls` for the covered bug lifecycle and defect creation prompts.
- Confirmed no new MCP endpoint/tool, backend path, fallback, compatibility/dual-shape handling, transitional adapter, alternate endpoint, legacy path, or new architecture was introduced in the reviewed diff.

## Validation
- Commands run:
  - `python3 -m unittest tests.test_agent_contract`
  - `python3 -m unittest discover -s tests -p "test_*.py"`
  - `python3 -m compileall onto_mcp`
  - `git diff --check`
- Result:
  - Focused contract tests passed: 23 tests.
  - Full unittest discovery passed: 77 tests.
  - `compileall` passed.
  - `git diff --check` passed.
- Not run (and why):
  - Live MCP/Onto write smoke was not run because QA scope is local guidance-only contract validation and no live mutation was requested.
  - Commit, push, and deploy were not run by instruction.

## Risks
- The guidance path depends on named input extraction from the prompt, matching the existing `how_to_use_onto_mcp` contract style.
- No remote/preprod runtime verification was performed; this verdict covers local contract behavior only.

## Handoff
- Remaining work: Orchestrator delivery gate for commit/push/deploy decisions if desired.
- Recommended next owner (area): Orchestrator / MCP owner.

## Commit Description (English)
- Short commit description: QA MCP how-to bug reclassification routing
