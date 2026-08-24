# Remove public MCP delivery workflows

## Task

- Objective: keep internal delivery implementation out of public
  `hope4b/mcp`.
- Owner decision: MCP delivery remains two explicit DevOps commands backed by
  the existing private `mcp-server` workflow.
- Scope: remove the three experimental central-delivery callers from public
  `mcp`.
- Out of scope: MCP runtime/API behavior, workflow dispatch, PR closure, AWS,
  secrets and environment changes.

## Changes

- Removed PR build, candidate publication and `/deploy preprod` callers that
  depended on private reusable workflows in `onto-delivery`.
- Public `mcp` now contains application source and no active GitHub delivery
  workflow.

## Validation

- Exact workflow inventory is empty.
- `git diff --check` passes.
- Runtime tests are not required because application code is unchanged.

## Handoff

- PREPROD: resolve the requested public PR head SHA and dispatch private
  `mcp-server/.github/workflows/docker-build.yml` with `preprod-onto`.
- PROD: dispatch the same private workflow with `prod-onto` and `main`.
- PR `#21` is obsolete but was not closed by this repository change.
