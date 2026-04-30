# Task Note

## Task
- Short objective: Record the repeatable live `stdio MCP` QA baseline for the Onto MCP server.
- Scope: Agent instructions and test-strategy guidance for real MCP transport checks.
- Out of scope: MCP product behavior changes.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `AGENTS.md`, `docs/agents/TEST_STRATEGY.md`
- Behavioral impact: Documentation only. Future agents now have an explicit baseline for `ONTO_API_KEY`, the correct preprod base URL, `.deps`-based runtime fallback, and temporary QA realm cleanup.
- Risks: None beyond future drift if runtime packaging or preprod URL conventions change.

## Validation
- Commands run: none
- Result: Documentation-only update
- Not run (and why): The actual stdio smoke was already validated in prior QA work; this task only captures the procedure.

## Commit Description (English)
- Short commit description: document repeatable stdio MCP QA baseline
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: Keep the runbook aligned with actual FastMCP runtime/import behavior if packaging changes.
- Recommended next owner (area): `QA/Reviewer Agent`
