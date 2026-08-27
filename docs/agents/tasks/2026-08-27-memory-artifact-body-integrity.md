# MemoryArtifact body integrity

## Task
- Short objective: Preserve exact MemoryArtifact body content and reject locally detectable governance body/hash mismatches.
- Scope: MCP create, update, append, and direct-supersede payload construction plus focused regression tests.
- Out of scope: backend implementation, routes/tool signatures, preliminary reads, compatibility behavior, merge, deploy, and data repair.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes
- Approved Change Spec and implementation handoff read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`, `tests/test_memory_artifact_tools.py`, and required project-memory notes.
- Behavioral impact: accepted nonblank bodies retain exact leading/trailing whitespace and CR/LF characters; whitespace-only bodies fail locally. Normative governance create/supersede calls require a matching canonical lowercase SHA-256 over the exact UTF-8 body before the existing backend mutation call.
- Risks: authoritative update/append governance validation remains a backend responsibility because MCP does not have all effective context without an unapproved read.

## Validation
- Commands run: focused and full `unittest`, temp-cache `compileall`, `git diff --check`, Ruff, and Black checks.
- Result: focused `21/21`, full `184/184`, compileall, and diff checks passed. Ruff reports the existing 31-file-scope baseline findings and no task-owned unsuppressed finding. Black reports the two pre-existing non-Black-formatted touched files; bulk reformatting is out of scope.
- Not run (and why): live MCP/backend smoke was not run because combined exact-commit backend QA is the next independent gate and no deploy is authorized.

## Commit Description (English)
- Short commit description: Preserve exact MemoryArtifact bodies in MCP writes

## Handoff
- Remaining work: independent combined QA against the exact MCP and backend implementation commits, then owner-controlled merge/delivery decisions.
- Recommended next owner (area): Orchestrator for QA routing; independent QA for the backend/API contract gate.
