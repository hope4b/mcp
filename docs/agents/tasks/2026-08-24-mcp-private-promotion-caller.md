# MCP private promotion caller boundary

## Task

- Short objective: remove private post-merge delivery authority from public
  `hope4b/mcp`.
- Scope: delete the public `push:main` caller that required
  `MCP_SERVER_DELIVERY_TOKEN`; retain the three PR build/publication/PREPROD
  callers unchanged.
- Out of scope: MCP runtime/API changes, workflow dispatch, IAM, secrets,
  deployment and private repository mutation.

## Context Used

- `AGENTS.md` and its required read order: read.
- Approved Change Spec:
  `onto-docs/docs/agents/tasks/2026-08-24-mcp-private-promotion-change-spec.md`.
- Trusted implementation: `hope4b/onto-delivery` private-dispatch promotion.

## Changes

- Deleted `.github/workflows/mcp-main-delivery.yml`.
- Public repository retains no private write token or automatic post-merge
  trigger.
- Build, immutable candidate publication and `/deploy preprod` remain unchanged.

## Validation

- YAML parse and static caller assertions for the three retained workflows.
- Exact workflow inventory and `git diff --check`.
- No runtime tests: no MCP application source changed.

## Handoff

- Private post-merge caller belongs in `hope4b/mcp-server` and accepts exact
  `mcp_merge_sha`.
- This setup change does not deploy anything.
