# Project Context

## Summary
- Name: `onto-mcp-server`
- Type: service/library
- Domain: MCP integration layer for Onto platform resources and authentication workflows

## Product Purpose
- Provide an MCP server that exposes Onto operations, search, and workspace management to MCP-compatible clients.
- Preserve exact Onto API-key authentication and optional session-state helper
  behavior across supported MCP transports.

## Core Product Capabilities
- Authenticate Onto calls with configured/client-passthrough API keys or optional delegated HTTP OAuth.
- Search Onto realms, templates, and objects with pagination-aware helpers.
- Expose MCP tools/resources for workspace discovery and entity/template management.

## Owner-Confirmed Product Semantics
- Authentication is required before protected Onto operations can succeed.
- MCP does not collect login/password or external-client refresh tokens. Optional HTTP OAuth validates original access tokens, freshly introspects them and performs subject-preserving Core token exchange; the issuer/client owns interactive login.
- Transport-specific behavior (`stdio` vs `http`) must preserve the same tool semantics where possible.

## Runtime and Tooling
- Python: setuptools-based package, local code suggests Python 3.12+
- Framework: FastMCP
- Test stack: `pytest`

## Domain Rules
- Access rules: Core remains authoritative for the active key or delegated user. OAuth MCP read/write consent does not replace domain permissions.
- HTTP mode may use incoming `X-Onto-Api-Key`; the runtime forwards it to Onto
  as `X-API-Key`. Stdio requires configured `ONTO_API_KEY`.
- Sharing/security rules: secrets, tokens, API keys, and session artifacts must never be committed.

## Critical Invariants
- Tool outputs must reflect the active request/runtime authentication context.
- API-key and optional session-state helper failures must fail safely without
  exposing credentials.
