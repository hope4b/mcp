# Agents Bootstrap Template (Single File)

Copy sections into corresponding files in a new repository.

---

## File: `AGENTS.md`

```md
# Multi-Agent Context Protocol

This repository uses a shared context protocol for all coding agents.

## Goal
Keep project knowledge in versioned files so any agent can continue work safely.

## Required Read Order (Before Any Edit)
1. `AGENTS.md`
2. `docs/agents/ROLES.md`
3. `docs/agents/PROJECT_CONTEXT.md`
4. `docs/agents/ARCHITECTURE_MAP.md`
5. `docs/agents/TEST_STRATEGY.md`
6. `docs/agents/HANDOFF.md`
7. Last entries in `docs/agents/WORKLOG.md`

## Required Update Order (After Any Edit)
1. Add task note based on `docs/agents/TASK_TEMPLATE.md`
2. Append a short entry to `docs/agents/WORKLOG.md`
3. Update `docs/agents/HANDOFF.md` if there are next steps
4. Append to `docs/agents/DECISIONS.md` if process/architecture changed
5. If code was changed, end assistant response with short commit description in English (mandatory final line format: `Commit description (EN): <short text>`)

## Project Baseline
- Stack: `<stack>`
- Package manager: `<npm/pnpm/yarn>`
- Node version: `<version>`
- Main source: `<path>`
- Locales: `<if any>`

## Role Model
1. `Coordinator`
2. `Feature Agent`
3. `Data/API Agent`
4. `Platform/Infra Agent`
5. `QA/Reviewer Agent`

## Guardrails
- Do not commit secrets.
- Do not rewrite unrelated files.
- Keep changes minimal and scoped.
- Validate behavior with tests/lint when possible.
- After each code change task, assistant MUST end the final response with `Commit description (EN): <short text>` in English.
```

---

## File: `docs/agents/README.md`

```md
# Agents Context Files

- `PROJECT_CONTEXT.md`: stable project facts and product semantics.
- `ROLES.md`: role model and checklists.
- `ARCHITECTURE_MAP.md`: codebase map and risk zones.
- `TEST_STRATEGY.md`: validation matrix by scope.
- `HANDOFF.md`: active coordination state.
- `WORKLOG.md`: append-only task log.
- `DECISIONS.md`: accepted process/architecture decisions.
- `TASK_TEMPLATE.md`: task note template.
```

---

## File: `docs/agents/PROJECT_CONTEXT.md`

```md
# Project Context

## Summary
- Name: `<repo-name>`
- Type: `<app/service/library>`
- Domain: `<business domain>`

## Product Purpose
- `<why product exists>`
- `<main user value>`

## Core Product Capabilities
- `<capability 1>`
- `<capability 2>`
- `<capability 3>`

## Owner-Confirmed Product Semantics
- `<policy/constraint 1>`
- `<policy/constraint 2>`
- `<policy/constraint 3>`

## Runtime and Tooling
- Node: `<...>`
- Framework: `<...>`
- Test stack: `<...>`

## Domain Rules
- `<access rules>`
- `<lifecycle rules>`
- `<sharing/security rules>`

## Critical Invariants
- `<invariant 1>`
- `<invariant 2>`
```

---

## File: `docs/agents/ROLES.md`

```md
# Roles

## Coordinator
- Purpose: planning, sequencing, conflict prevention.
- Owns: `docs/agents/**`.

## Feature Agent
- Purpose: UI/feature behavior.
- Owns: `<paths>`.

## Data/API Agent
- Purpose: contracts, data flows.
- Owns: `<paths>`.

## Platform/Infra Agent
- Purpose: build/deploy/config.
- Owns: `<paths>`.

## QA/Reviewer Agent
- Purpose: regression/risk checks.
- Owns: tests and validation gates.
```

---

## File: `docs/agents/ARCHITECTURE_MAP.md`

```md
# Architecture Map

## Top-Level Layout
- `<path>`: `<purpose>`
- `<path>`: `<purpose>`

## Feature Areas
- `<feature area>`: `<summary>`

## Risk Zones
- `<path>`: `<why risky>`

## Ownership Hints
- Feature: `<paths>`
- Data/API: `<paths>`
- Platform: `<paths>`
```

---

## File: `docs/agents/TEST_STRATEGY.md`

```md
# Test Strategy

## Core Rules
- Run targeted tests for touched scope.
- Run full suite for cross-scope/high-risk changes.
- Record skipped checks and risks.

## Baseline Commands
- Lint: `<cmd>`
- Unit: `<cmd>`
- Build: `<cmd>`

## Scope To Validation Matrix
- `<path>` -> `<required checks>`
- `<path>` -> `<required checks>`
```

---

## File: `docs/agents/HANDOFF.md`

```md
# Handoff

## Role Directory
- `Coordinator`: `unassigned` (backup: `unassigned`)
- `Feature Agent`: `feature-main` (backup: `fix-main`)
- `Data/API Agent`: `unassigned` (backup: `unassigned`)
- `Platform/Infra Agent`: `unassigned` (backup: `unassigned`)
- `QA/Reviewer Agent`: `unassigned` (backup: `unassigned`)

## Active Claims
- None.

## Next Priority Queue
1. `<next task>`
2. `<next task>`

## Last Completed
- `<UTC timestamp>`: `<done item>`
```

---

## File: `docs/agents/WORKLOG.md`

```md
# Worklog

Append-only log. Newest entries on top.

## <UTC timestamp> - <short-id>
- Task: <what>
- Files: <files>
- Validation: <how verified>
- Next: <next action>
```

---

## File: `docs/agents/DECISIONS.md`

```md
# Decisions Log

## <YYYY-MM-DD> - <decision title>
- Status: Accepted
- Decision: <what was decided>
- Reason: <why>
- Consequences:
  - <impact 1>
  - <impact 2>
```

---

## File: `docs/agents/TASK_TEMPLATE.md`

```md
# Task Note Template

## Task
- Short objective:
- Scope:
- Out of scope:

## Context Used
- AGENTS.md read: yes/no
- PROJECT_CONTEXT.md read: yes/no
- ARCHITECTURE_MAP.md read: yes/no

## Changes
- Files changed:
- Behavioral impact:
- Risks:

## Validation
- Commands run:
- Result:
- Not run (and why):

## Commit Description (English)
- Short commit description:
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work:
- Recommended next owner (area):
```
