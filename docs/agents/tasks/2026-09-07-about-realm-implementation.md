# `about_realm` runtime implementation

Date: 2026-09-07

Role: resident `mcp-owner`

Mode: `runtime`

Manifest: `realm-declaration-about-realm-mcp-runtime-v2`

Manifest SHA-256: `0f63115865d57c72f47f7ed03a0231d94d2c12f54085c350e842c3b65d3e821e`

## Result

Implemented one read-only FastMCP tool, `about_realm(realm_id)`, on branch
`feat/about-realm` from pinned base
`576a3ba0846e670db5d4c94454c654c1e3e3f652`.

The implementation:

- rejects non-canonical realm UUIDs locally before credentials or backend I/O;
- performs one authenticated declaration-specific `GET` for
  `realm/declaration`;
- validates the closed backend projection, exact accepted/current lifecycle,
  exact `realm_declaration@1` canonical body, exact body SHA-256, and the
  inclusive 65,536-byte bound;
- returns only the exact public whitelist in `MCP-REQ-003` and does not expose
  backend-only lifecycle or generic MemoryArtifact fields;
- maps every reviewed backend outcome and transport boundary to the stable,
  no-body MCP tool-error envelope;
- registers separate global-Onto and concrete-realm guidance without fallback,
  route execution, resident selection, authorization, or run behavior; and
- advances the canonical machine-readable agent contract and its rendered
  entry guide to 66 registered tools.

## Verification

The implementation was checked with focused declaration/guidance/schema tests,
the full Python test suite, Python bytecode compilation, source diff checks,
and real FastMCP registration/client smoke probes. Exact commands and results,
the pushed commit/tree identities, and strict remote read-back evidence are
recorded in the external implementation result named by the manifest.

No backend source, deployment, realm state, declaration publication, PROD
state, or external realm was changed. Independent review and QA remain owned by
the orchestrator after this source-only runtime handoff.

Next owner: `orchestrator`.
