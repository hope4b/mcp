# MCP Central Delivery

- Date: 2026-08-19
- Owner approval: explicit `начинай`
- Scope: delivery callers and project records only; MCP runtime/API behavior is unchanged.

## Result

`mcp` now contains four minimal GitHub Actions callers for the central
`onto-delivery` contract:

- exact-head PR test and one-time image build;
- immutable candidate publication;
- owner-requested `/deploy preprod`;
- post-merge same-digest INTERNAL delivery and private organization-baseline
  update.

All implementation remains in `hope4b/onto-delivery` commit
`e84c01dba3b6d97fdd7f5b66e48f269e4c099e19`. The post-merge caller passes only
repository secret `MCP_SERVER_DELIVERY_TOKEN` to update private
`hope4b/mcp-server:org/deforg`. Public `mcp` has no organization branch.

## Boundaries

- No MCP runtime, tool, API or Dockerfile change.
- No AWS, PREPROD, INTERNAL or organization runtime mutation.
- No setup PR.
- PROD and private-organization deployment remain out of scope.
- The historical `mcp-server` host-build workflow remains until live
  acceptance succeeds; it is not a fallback for the new path.

## Validation

- YAML parse for all four callers.
- `actionlint` for all four callers.
- static assertions: exact central commit, minimal event/permission surface,
  no local build/deploy implementation, no `secrets: inherit`.
- `git diff --check`.

## Delivery state

Implementation is prepared in an isolated worktree from exact `origin/main`
`3add05128b7a44a8963755cab78dbf94ca130710`. Commit, push, AWS stack creation,
secret configuration, live acceptance PR and deployment are separate gates.
