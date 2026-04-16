## Task
- Short objective: Make batch entity classification input consistent with the rest of the MCP surface.
- Scope: `onto_mcp/api_resources.py`, QA catalog, agent coordination files.
- Out of scope: Onto backend payload semantics, any rename of raw Onto API keys.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes

## Changes
- Files changed: `onto_mcp/api_resources.py`, `docs/income/QA_MCP_TOOL_CATALOG.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`, `docs/agents/tasks/2026-04-17-batch-meta-key-alias.md`
- Behavioral impact: `save_entities_batch` and `create_entities_batch` now accept `meta_entity_id` as the canonical MCP input, while still supporting legacy `metaEntityId` as a backward-compatible alias.
- Risks: Existing clients that send both keys with conflicting values now receive an MCP validation error instead of a silently ignored classification mismatch.

## Validation
- Commands run: import smoke for `onto_mcp.api_resources`
- Result: `onto_mcp.api_resources` imports successfully with dummy env values after the batch key normalization.
- Not run (and why): live Onto QA was not re-run here because the fix is a contract normalization on top of already validated batch behavior.

## Commit Description (English)
- Short commit description: normalize batch entity classification input to snake_case
- Required for code changes: assistant final response must end with `Commit description (EN): <short text>`.

## Handoff
- Remaining work: Re-run the batch classification scenario with `meta_entity_id` as input and keep the alias only for backward compatibility.
- Recommended next owner (area): QA/Reviewer Agent.
