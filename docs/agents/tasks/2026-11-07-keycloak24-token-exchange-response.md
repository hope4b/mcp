# Keycloak 24 token-exchange response compatibility

## Task
- Objective: fix the reproduced `dependency_unavailable` when Keycloak 24.0.1
  omits `issued_token_type` from an otherwise valid exchange response.
- Scope: MCP response validation, regression tests, reproducible local provider
  fixture, operator documentation and publication in existing PR #32.
- Out of scope: PREPROD deployment/configuration, Keycloak upgrade or writes,
  IAM, secrets, Core/Web UI, accepted specification and independent QA approval.

## Context Used
- AGENTS.md, PROJECT_CONTEXT.md, ARCHITECTURE_MAP.md, TEST_STRATEGY.md: read
  during this continuing direct-owner assignment; applicable runtime bootstrap
  and receiver kernel retained.
- `direct_owner_task_context_v1`: role=mcp-owner, mode=runtime,
  orchestrator_run=none; owner instruction "вперед" follows the diagnosed exact
  missing-member incompatibility, proposed implementation and authorization to
  implement it. The context includes publication in the existing PR; no new
  PREPROD operation is authorized by this correction.
- Governance references retained from this session: Constitution
  b826563c-f1ab-47ec-a994-0dfe86662833, registry
  4b2edeff-fe1c-4419-a607-22843ffe27d6, charter
  656fdd41-a025-4f1e-8e44-b804c0657a0a. Process source:
  onto-docs b9984318abb3bdbaabfb7b29817f0ad61b1adaa7, MCP Direct Entry and
  MCP_RUNTIME_RECEIVER_KERNEL.md.
- Source/preimage: e1893029467cb2c96035a970a4fe886ab2c072ce, isolated checkout
  codex/oauth-mongodb-state, PR #32 head confirmed before editing.
- Diagnosis: /tmp/mcp-keycloak24-token-exchange-diagnosis-2026-11-07.md;
  actual PREPROD `kc.sh --version` reported 24.0.1. The prior local isolated
  reproduction verified signatures and all identity checks; restoring only
  the absent member in memory removed the failure.

## Changes
- `onto_mcp/oauth.py`: allow only absence of `issued_token_type`, while a
  present value must identify an access token. Explicit access-token request,
  mandatory Bearer response, signed JWT parsing/signature/issuer/expiry,
  complete subject/session binding, exchange-client azp and Core audience
  checks are preserved. No fallback credential or alternate endpoint.
- `tests/test_oauth_authorization.py`: successful legacy response reaches the
  inert Core transport with delegated Bearer only; malformed present types,
  bad signatures/Bearer response and invalid signed claims still deny access.
- `tests/test_oauth_keycloak24_integration.py`: opt-in regression with actual
  local Keycloak 24.0.1 response and real RS256/JWKS verification.
- `tests/fixtures/oauth_keycloak24_realm.json`: dedicated synthetic realm,
  client and user, disposable public test credentials only. Password grant,
  HTTP and shared requester/target client are local-fixture shortcuts, not
  deployment settings or proof of production permissions/interoperability.
- README and DECISIONS describe the bounded compatibility correction.
- This note records direct-owner authority/evidence and next owners. Accepted
  specification, task ledgers and historical approvals are not rewritten.

## Validation
- Focused OAuth/authentication/HTTP/formal-contract tests: 430 passed.
- Full test suite with opt-in real Keycloak fixture: 787 passed, 2 MongoDB
  integration tests skipped, 1 warning.
- Ruff on changed Python: passed. `compileall -q onto_mcp`: passed.
- Black on changed Python: passed. `git diff --check`: passed.
- MongoDB integration tests are opt-in and skipped in this run: state adapter
  is unchanged; its prior real MongoDB validation belongs to e189302 evidence.
- No PREPROD changes, current-user token extraction, live Core calls, formal
  independent review or QA approval are claimed.

### Reproduce the isolated Keycloak integration

Use a task-owned internal network and container with no published ports. The
following fixture can be deleted after the test; never mount a live database.

```sh
docker network create --internal mcp-keycloak24-response-net
docker run -d --name mcp-keycloak24-response-fixture \
  --network mcp-keycloak24-response-net --memory 1536m \
  -e JAVA_OPTS_KC_HEAP='-Xms128m -Xmx512m' \
  -v "$PWD/tests/fixtures/oauth_keycloak24_realm.json:/opt/keycloak/data/import/realm.json:ro" \
  quay.io/keycloak/keycloak:24.0.1 start-dev \
  --features=token-exchange,admin-fine-grained-authz --import-realm
```

After fixture readiness, run Python 3.11 with this repository's dependencies
on the same network. Set
`MCP_TEST_KEYCLOAK24_URL=http://mcp-keycloak24-response-fixture:8080/realms/mcp-response-fixture`
and run `python -m pytest -q tests/test_oauth_keycloak24_integration.py`.
The opt-in guard rejects other URLs. Production HTTPS configuration is not
relaxed by this fixture. Synthetic tokens stay in test process memory.

## Handoff
- Next owner: independent MCP reviewer, then separately authorized candidate
  publication/rollout and real ChatGPT read-tool verification. The developer's
  local provider test does not establish Core/user authorization or live QA.
- No Keycloak upgrade or ChatGPT form change is needed for this specific defect.
- T1-C and fixed-audience compatibility risks remain accepted and unverified.

## Commit Description (English)
- Accept Keycloak 24 token exchange responses without issued_token_type.
