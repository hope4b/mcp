# Realm-description `how_to_use_onto_mcp` hardening

## Scope

Implemented the runtime-only guidance correction authorized by manifest
`realm-declaration-how-to-hardening-v1` at base
`4d1cfb260adb72a590206adfe1e881ae05f10a4a`. No resolver, backend, deploy,
realm, declaration-publication, subject, memory, or object-chat mutation was
performed.

## Behavior

- A realm-description request with canonical `realm_id` emits exactly one
  `about_realm` call.
- The same request without an id emits exactly
  `list_available_realms` -> `about_realm`; the second call declares its
  `realm_id` dependency on the first.
- A reported `about_realm` `declaration_not_found` is terminal: the response
  says that no declaration is published, tells the caller to report and stop,
  and emits no next call.
- A request to publish or update `realm/declaration` is terminal in this
  router and identifies the separate exact owner-decided Constitutional
  Steward flow with its own package and gates.
- Realm-description `avoid_tools` contains every registered tool except the
  two canonical safe route tools, so all mutations and generic read fallbacks
  are explicitly excluded without also excluding `list_available_realms` or
  `about_realm`.

Canonical machine-readable guidance and the rendered entry guide carry the
same boundaries. RU/EN transcript-shaped tests cover known and unknown realm
sequences, terminal missing declaration, separate publication flow, zero
writes, and explicit fallback avoidance.

## Validation

```text
PYTHONPATH=/tmp/mcp-realm-declaration:/tmp/mcp-about-realm-deps \
  python3 -m pytest -q tests/test_agent_contract.py
52 passed

PYTHONPATH=/tmp/mcp-realm-declaration:/tmp/mcp-about-realm-deps \
  python3 -m pytest -q
200 passed, 2 skipped

python3 -m compileall -q onto_mcp
passed

python3 -m json.tool onto_mcp/agent_contract.json >/dev/null
passed

git diff --check
passed
```

The two skips are the existing real-FastMCP isolation behavior already covered
by the accepted correction QA baseline; this hardening changes only guidance
carriers and their tests.
