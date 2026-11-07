# OAuth state: MongoDB implementation

## Task
- Objective: replace PostgreSQL OAuth binding/helper persistence with the existing
  MongoDB contract prepared by DevOps, before a later targeted specification update.
- Scope: MCP state adapter, dependency, cache cleanup, tests and operator docs.
- Out of scope: IAM/SSM grants, creating the PREPROD runtime user, TLS/backups,
  infrastructure configuration, deployment, merge, Core/Web UI and specification publication.

## Context Used
- AGENTS.md, PROJECT_CONTEXT.md, ARCHITECTURE_MAP.md and TEST_STRATEGY.md read: yes.
- Role: `mcp-owner`, active resident admission checked for realm
  `000ba00a-00a0-0a00-a000-000a0a0a0aa3`.
- `direct_owner_task_context_v1`:
  - source: owner's direct instruction on 2026-11-06, "Ну уже можно вносить
    правки в код, все это уже настройки", following the request to use MongoDB,
    implement code, and only then record precise specification corrections;
  - authority: Constitution `b826563c-f1ab-47ec-a994-0dfe86662833`, Registry
    `4b2edeff-fe1c-4419-a607-22843ffe27d6`, charter
    `656fdd41-a025-4f1e-8e44-b804c0657a0a`;
  - process: onto-docs `b9984318abb3bdbaabfb7b29817f0ad61b1adaa7`, MCP Owner
    bootstrap, DIRECT_OWNER_ASSIGNMENT.md MCP Direct Entry and
    MCP_RUNTIME_RECEIVER_KERNEL.md;
  - bounded source: MCP PR #32 head
    `12ef674a2226506b3d264c0ac96914d3fe2ab186`; isolated branch
    `codex/oauth-mongodb-state`; DevOps schema/role evidence at onto-delivery
    local commit `1cae319`;
  - allowed work: the exact files listed below and local synthetic verification;
  - no authority: IAM, PREPROD writes, deploy, push, merge, memory/specification
    publication or alteration of accepted package
    `f1acd520-10d4-4f29-b33f-3c36ee3f80b5`;
  - next owner: independent MCP reviewer, then QA and separately assigned DevOps.
- This is a direct owner code assignment, not continuation of the native feature
  controller. Historical approvals are not changed or claimed for this revision.

## Changes
- `onto_mcp/oauth_state.py`: one binding/helper document, atomic conditional
  helper updates, immutable expiry/first-save timestamp, ownership checks,
  pending failed invalidations, unconditional sweep and TTL cache reconciliation.
- `onto_mcp/oauth.py`: prune idle expired exchange-cache entries and expose only
  owner hashes to the state sweep; credentials are never persisted in MongoDB.
- `requirements.txt`: replace psycopg with pymongo 4.19.0.
- Remove the obsolete `sql/oauth_state.sql` provisioner. Operators provision
  MongoDB objects separately; runtime checks required indexes without DDL.
- README/ARCHITECTURE_MAP/DECISIONS: describe active Mongo configuration and
  explicitly separate outstanding environment prerequisites.
- Tests: adapt state/HTTP fixtures to Mongo operations; add configuration/TLS/
  index/error-redaction checks, TTL cache/unknown-delete coverage, idle cache
  pruning and opt-in authenticated MongoDB 6 integration coverage.
- This task note records the bounded change; it does not revise accepted specs.

## Validation
- Python 3.11 test image built from repository requirements, using the session
  trusted CA during dependency installation. No global Python change.
- Focused OAuth run: 409 passed before the final additional purge test.
- Full suite with opt-in disposable MongoDB harness: 764 passed, one warning.
- MongoDB 6.0.28 disposable container: verified TLS, SCRAM-SHA-256 runtime user,
  exact strict validator from DevOps contract and collection-only privileges
  (find/insert/update/remove/listIndexes); no published ports; isolated internal
  test network. Test databases/users/roles are removed by fixtures.
- Integration proves 20 concurrent saves, fixed lifetime and first-save time,
  literal `$` values, persisted-state reconstruction, cross-owner rejection,
  invalidation, expiry/purge, strict validator rejection and DDL denial.
- `ruff check` on changed Python files: passed.
- `black` on changed Python files: formatted.
- `python -m compileall -q onto_mcp`: passed.
- `git diff --check`: passed.
- No PREPROD/Core/Keycloak/browser checks or formal independent QA executed.
  A passing disposable harness does not establish production durability,
  backup coverage, provider revocation or ChatGPT interoperability.

## Handoff
- PREPROD prerequisites remain: collection-only runtime user; URI secret and
  injection (`ONTO_OAUTH_STATE_MONGO_URI`), verified MongoDB TLS and backup
  coverage/retention. Defaults: DB `onto_mcp`, collection `oauth_sessions`.
- The quoted request to grant ssm:PutParameter was evidence from DevOps, not an
  approval to edit IAM in this assignment. No infrastructure permission changed.
- Existing OAuth deployments using ONTO_OAUTH_STATE_DSN must receive the new
  secret/configuration with their separately approved rollout. There is no
  PostgreSQL fallback or automated state migration.
- Independent review/QA, precise specification correction and candidate rollout
  remain separate work. Accepted T1-C/audience risks are not reopened.

## Commit Description (English)
- Replace PostgreSQL OAuth state storage with MongoDB.
