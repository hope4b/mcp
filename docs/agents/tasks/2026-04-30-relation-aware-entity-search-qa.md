# QA Report: Relation-Aware Entity Search MCP Tool

- Date: `2026-04-30`
- Target repo: `mcp`
- Tool: `search_entities_by_relations`
- Verdict: `pass`

## Static Review
- Result:
  - Tool is present and discoverable as `search_entities_by_relations`.
  - Public input contract matches the task: `realm_id`, `searched_meta_ids`, optional flat `predicates[]`.
  - Predicate public fields are limited to `relation_type_names`, `related_meta_ids`, `related_entity_ids`.
  - Wrapper maps snake_case to backend camelCase and calls only `POST /realm/{realmId}/entity/search`.
  - No fallback to `entity/find`, `entity/find/v2`, client-side scanning, or mutation endpoints is present in the tool path.
- Notes:
  - Implementation reviewed in `onto_mcp/api_resources.py`.
  - `stdio` auth baseline for this tool is `ONTO_API_KEY` -> outbound `X-API-Key`.

## Unit/Contract Tests
- Commands:
  - `python -m unittest tests.test_search_entities_by_relations`
  - `python -m compileall onto_mcp`
- Result:
  - `7/7` tests passed.
  - `compileall` passed.
- Notes:
  - Unit coverage confirms root-only mapping, predicate camelCase mapping, local rejection for empty `searched_meta_ids`, limit checks, and rejection of `direction`, boolean operators, nested predicates, and name-based classification inputs.

## Live Smoke
- Environment:
  - `stdio MCP` subprocess transport through real `fastmcp` client/server.
  - Local backend target: `http://localhost:8080/api/core`
  - Preprod backend target: `https://preprod.ontonet.ru/api/v2/core`
  - Auth: `ONTO_API_KEY` (`X-API-Key` path), not Bearer.
  - Realm used for semantic fixture: `9ae9190c-ad78-47ad-b680-e7fb405d7023`
- Result:
  - Local `stdio` smoke: passed.
  - Preprod `stdio` smoke: passed on a temporary QA realm created and deleted during the run.
- Notes:
  - Local fixture-backed semantic checks passed through the MCP tool:
    - root-only search returned `qa-root1..qa-root4`
    - relation type + concrete related entity returned `qa-root1`
    - wrong related entity returned no match
    - relation type + related meta returned `qa-root3`, `qa-root4`
    - multiple predicates worked as `AND`
    - multiple `relation_type_names` worked as `OR`
    - multiple `related_entity_ids` worked as `OR`
    - `related_meta_ids + related_entity_ids` narrowed by both
    - one-hop boundary returned no match for the two-hop case
  - Local invalid-shape checks were rejected by the MCP wrapper before backend call:
    - empty `searched_meta_ids`
    - unsupported `direction`
    - nested `predicates`
  - Preprod `stdio` smoke was re-run against the correct base URL and used a temporary QA realm:
    - realm: `48c36b94-69fa-4df0-abd1-aed9aa7b3990`
    - root meta: `a49a6e7d-e419-467c-984a-42aa2f2f18b9`
    - user meta: `61808b62-d781-419f-95c6-96fb307c25bd`
    - folder meta: `0a149e02-8955-45e1-a420-23ba710c4f50`
    - service meta: `20aea321-67ae-41a1-b531-08e2886d7989`
    - team meta: `0e9853c6-ea6a-43bf-ae36-73e90dfcac2d`
  - Preprod semantic checks passed through the MCP tool:
    - root-only search returned 4 root entities
    - relation type + concrete related entity returned the expected single root
    - wrong related entity returned no match
    - relation type + related meta returned the expected 2 roots
    - multiple predicates worked as `AND`
    - multiple values in `relation_type_names` worked as `OR`
    - multiple values in `related_entity_ids` worked as `OR`
    - `related_meta_ids + related_entity_ids` narrowed by both
    - one-hop boundary returned no match for the two-hop case
    - invalid shapes were rejected locally by the wrapper
  - The temporary preprod QA realm was deleted successfully after the smoke.

## Findings
- Severity: none
- Comment: No blocking QA findings for the MCP wrapper or the live `stdio` runtime path after re-running preprod smoke against the correct base URL `https://preprod.ontonet.ru/api/v2/core`.
- Risk: Low. The wrapper is presentation-oriented, so future changes should preserve the confirmed structural-search semantics and local validation behavior.
- Proposed change: Reuse this preprod fixture pattern for future stdio MCP smoke checks that need controlled relation-aware semantics.
- Blocking: no
