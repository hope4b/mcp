"""User-facing instructions shared by the connector and how-to tool."""

CONNECTOR_GUIDANCE = """Discover realms and search targets using actual authorized results. Present identifiable choices
(names, stable IDs and distinguishing context), ask and wait when realm or target selection is ambiguous.
Never select by list order, last-used realm, or fabricated IDs. Clarify vague replies again. Cancellation ends
the request. A changed realm invalidates prior targets; resolve them again. Explicit identified multiple-target
requests are not ambiguity. Make the resolved realm and targets visible before mutation. Selection grants
neither write consent nor backend permission. Ordinary explicitly instructed editing needs no additional
confirmation. Before deletion, clearing or replacement losing prior content, explain the known action and
targets, obtain additional conversational confirmation and wait before invoking the existing tool. Cancellation
prevents invocation; material changes require fresh confirmation. Save/upsert defaults and helper replacement
can lose prior content under existing semantics. MCP cannot prove human receipt or confirmation, or actual
client adherence. Preserve checkable source IDs and provenance in results. First use may provision an Onto
user and personal realm, even with read-only consent; deployed provisioning behavior remains unverified.

Each configured external OAuth client owns renewal and its refresh token. To revoke, identify that client's
actual consent entry in the configured issuer's Keycloak Account Console and use remove access. Example
application labels are not mandatory names. Alternatively that authorized client/provider POSTs to
{configured issuer}/protocol/openid-connect/revoke using its own configured authentication, refresh token,
and token_type_hint=refresh_token. MCP never holds that refresh token. HTTP 200 proves neither prior grant
existence/absence nor effective revocation. Provider action plus fresh introspection of an outstanding
original access token returning active=false is the effective denial oracle. New dispatch then stops despite
caches; already dispatched work may finish. User/client-wide revocation differs from jti revocation, provider
session identity is not device identity, and ChatGPT Disconnect behavior remains unverified.
"""
