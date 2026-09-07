# `about_realm` independent-review corrections

Date: `2026-09-07`

Role/mode: resident `mcp-owner` / `runtime`

Manifest: `realm-declaration-about-realm-mcp-correction-v1`

Manifest identity: `6820` bytes, SHA-256
`cacb856fb7c6930053baa06d2125fec49af7a24359329c647ea067294c4c9554`

Base: `9471106e9cd01780ce36ae0ceec8b09b9ba5cfaf`

## Corrected findings

- `MCP-REV-BLOCK-001`: an `about_realm`-only FastMCP call boundary now
  validates the raw argument object before framework function validation.
  Missing, null, non-string, non-canonical, or extra arguments raise the exact
  stable `invalid_request` MCP tool-error envelope without reaching credentials
  or the backend. The advertised operation remains closed to exactly one
  required string property, `realm_id`.
- `MCP-REV-BLOCK-002`: the shared outer timeout wrapper now has an exact
  `about_realm` branch that raises the stable `dependency_unavailable` MCP
  tool-error envelope with `retryable=true` and the wrapper's opaque
  correlation id. It emits no generic timeout, tool, transport, or request-state
  fields.

The independent review's non-blocking timestamp note was also addressed within
the authorized resolver and test paths: `accepted_at` must use an exact UTC
date-time shape with seconds, optional one-to-nine-digit fractional seconds,
and terminal `Z`; semantic date/time validity is still checked by the standard
parser.

## Verification route

- Real isolated FastMCP client/schema/invalid-shape/outer-timeout tests: passed.
- Focused runtime plus resolver tests: passed.
- Full pytest, compileall, and diff checks: results are recorded in the external
  correction result required by the manifest.

No alternate endpoint, fallback, alias, compatibility behavior, backend edit,
deployment, realm mutation, declaration publication, PROD operation, or release
decision was introduced.

Fresh independent confirmation remains required. Next owner: `orchestrator`.
