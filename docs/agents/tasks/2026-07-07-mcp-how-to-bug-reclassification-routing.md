# MCP how-to bug reclassification routing

## Task
- Short objective: Fix `how_to_use_onto_mcp` guidance for owner-approved single-object bug lifecycle/state reclassification and safe defect creation under an existing bug template.
- Scope: Runtime-visible agent guidance only, using existing `save_entity` / `save_entities_batch` semantics and existing read-back tools.
- Out of scope: New endpoints/tools, backend changes, deploy repo changes, fallback/compatibility/dual-shape/transitional adapter/alternate endpoint/legacy path, production deploy, unrelated cleanup, destructive or mass changes.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes
- Additional process files read: MCP owner bootstrap template, Onto object anchor contract, development-after-approval flow, MCP role/test/handoff/worklog files.

## Decision
- Change Spec not needed because this is a guidance-only correction to existing `how_to_use_onto_mcp` routing using already accepted `save_entity` / `save_entities_batch` semantics.
- The fix stays in the MCP agent contract/routing layer and does not change MCP tool signatures or backend API contracts.

## Changes
- Files changed:
  - `onto_mcp/agent_contract.py`
  - `onto_mcp/agent_contract.json`
  - `docs/AGENT_ENTRY_GUIDE.md`
  - `tests/test_agent_contract.py`
  - `docs/agents/WORKLOG.md`
  - `docs/agents/tasks/2026-07-07-mcp-how-to-bug-reclassification-routing.md`
- Behavioral impact:
  - Owner-approved bug lifecycle/state reclassification with exact `realm_id`, `entity_id`, target `template_id`/`meta_entity_id`, and lifecycle approval now routes `get_entity -> save_entity -> get_entity`.
  - Owner-approved safe defect creation under an existing bug template with exact `realm_id`, target `template_id`/`meta_entity_id`, name, comment, and write approval now routes `get_template -> save_entity -> get_entity`.
  - Equivalent prompts in `read_only` mode keep mutation tools out of `next_calls`.
  - Ambiguous multi-route questioning is avoided for these exact bug/defect guidance cases.
- Risks:
  - Guidance extraction depends on named inputs in the prompt, matching the existing `how_to_use_onto_mcp` contract style.
  - No live Onto mutation was performed; this is a local contract/test change only.

## Validation
- Commands run:
  - `python -m unittest tests.test_agent_contract`
  - `python3 -m unittest tests.test_agent_contract`
  - `python3 -m unittest discover -s tests -p "test_*.py"`
  - `python3 -m compileall onto_mcp`
  - `git diff --check`
- Result:
  - `python` command unavailable in this shell: `/bin/bash: line 1: python: command not found`.
  - Focused contract tests passed with `python3`: 23 tests.
  - Full unittest discovery passed with `python3`: 77 tests.
  - `compileall` passed.
  - `git diff --check` passed.
- Not run (and why):
  - `pytest` was not requested as required route and was not attempted.
  - Live MCP/Onto write smoke was not run because the approved scope is guidance-only and local validation.

## Onto Milestone
- Milestone target: locked external `onto_anchor` for `MCP-how-to-reclassification-defect`.
- Dedupe read: recent object chat was read before writing; no prior `milestone: implementation_reported` entry existed for this phase.
- Status: `implementation_reported` milestone written to the locked object chat.

## Handoff
- Remaining work: Orchestrator/owner delivery gate: review local implementation report, then route QA/commit/push/deploy gates if desired. Current status is implemented locally, not committed, not pushed, not deployed.
- Recommended next owner (area): MCP QA/Reviewer for local contract QA, then orchestrator delivery gate.

## Commit Description (English)
- Short commit description: Fix MCP how-to bug reclassification routing
