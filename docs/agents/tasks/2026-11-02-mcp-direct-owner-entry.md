# MCP direct-owner entry alignment

## Task
- Objective: accept ordinary direct human questions/assignments without asking
  for an Orchestrator manifest or another ownership message.
- Scope: project `AGENTS.md` aligned with MCP Direct Entry in onto-docs/main;
  this task note and the project process decision record.
- Out of scope: runtime/tool code, public HTTP/auth/pagination semantics,
  deployment workflows, credentials, model/governance mutations and QA verdicts.

## Context Used
- AGENTS.md, ROLES.md, PROJECT_CONTEXT.md, ARCHITECTURE_MAP.md,
  TEST_STRATEGY.md and TASK_TEMPLATE.md read.
- Accepted/current realm `mcp-owner` charter
  `656fdd41-a025-4f1e-8e44-b804c0657a0a` read through Onto MCP.
- Runtime main baseline `bb464c1a097aaf1cc362f6045da739e7881a8918`.
- Canonical process source: onto-docs/main; exact patch and behavioral evidence
  are recorded in `docs/agents/tasks/2026-11-02-mcp-direct-entry-result.md`
  in that repository.

## Changes
- Classify consultation/direct/routed work before package gates.
- Direct work builds its own bounded context, reads the applicable current
  instruction chain and continues permitted work in the same turn.
- Existing runtime-start, public-contract/auth/pagination, deploy/smoke,
  independent verification, memory/write and no-fallback gates remain.

## Validation
- Proofread project instruction chain and compare with the live charter.
- `git diff --check`; no runtime code or command examples changed.
- No local runtime tests/build/HTTP smoke: instructions-only change, consistent
  with the project Test Strategy. Actual role-entry probes are recorded in the
  canonical methodology report, with exact source/candidate revisions.

## Commit Description (English)
- Align direct-owner MCP intake with canonical role methodology.

## Handoff
- Review and merge this exact project PR to main after owner permission.
- No deploy or environment operation is assigned by this change.
- Independent QA and any future runtime/deploy work retain separate owners.
