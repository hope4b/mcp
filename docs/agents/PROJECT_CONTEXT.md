# Project Context

## Summary
- Name: `onto-mcp-server`
- Type: service/library
- Domain: MCP integration layer for Onto platform resources and authentication workflows

## Product Purpose
- Provide an MCP server that exposes Onto operations, search, and workspace management to MCP-compatible clients.
- Keep authentication state persistent and manageable across MCP sessions and transport modes.

## Core Product Capabilities
- Authenticate against Keycloak using credentials and token/session helpers.
- Search Onto realms, templates, and objects with pagination-aware helpers.
- Expose MCP tools/resources for workspace discovery and entity/template management.

## Owner-Confirmed Product Semantics
- Authentication is required before protected Onto operations can succeed.
- Session persistence is part of the product contract and should not silently regress.
- Transport-specific behavior (`stdio` vs `http`) must preserve the same tool semantics where possible.

## Runtime and Tooling
- Python: setuptools-based package, local code suggests Python 3.12+
- Framework: FastMCP
- Test stack: `pytest`

## Domain Rules
- Access rules: realm and object visibility depend on the authenticated Onto user and token scopes.
- Lifecycle rules: tokens may refresh automatically and can be persisted between runs.
- Sharing/security rules: secrets, tokens, API keys, and session artifacts must never be committed.

## Critical Invariants
- Tool outputs must reflect the authenticated session state accurately.
- Session storage and token refresh logic must fail safely and provide actionable error guidance.
