# Pin the validated MCP dependency stack

## Task
- Objective: make fresh test and runtime installations use the MCP stack verified against the existing public contract baseline.
- Scope: dependency versions in `requirements.txt` and this task note.
- Out of scope: tool implementation, public schemas, golden fixtures, test assertions, delivery workflows, deployment and merge.

## Context Used
- AGENTS.md read: yes.
- PROJECT_CONTEXT.md read: yes.
- ARCHITECTURE_MAP.md read: yes.
- Source candidate: `548e6786c191be672394dca075f616229afca6ab`.
- A fresh delivery installation selected FastMCP 4.1.4, Pydantic 2.14.2 and MCP 2.3.0; the public contract comparison reported 69 differing tool records. The retained independent golden must not be regenerated to obtain a pass.

## Changes
- Files changed: `requirements.txt`, this note.
- Pin `fastmcp==4.0.10`, `pydantic==2.13.5`, and `mcp==2.2.0` together.
- Behavioral impact: fresh test installations and the existing Docker build consume the same declared dependency versions. No source, schema, envelope or test-oracle edits.
- Risks: these three contract-sensitive distributions are pinned; other dependencies remain resolved by pip. Future dependency upgrades require contract verification. Local validation used Python 3.12.14, matching the delivery Python minor version; the unchanged Docker target is Python 3.11 and was not built in this task.

## Validation
- Fresh Python 3.12.14 venv; `python -m pip install --no-cache-dir -r requirements.txt --report <receipt>`: PASS. No existing QA environment was changed.
- Actual versions: FastMCP 4.0.10, fastmcp-slim 4.0.10, Pydantic 2.13.5, pydantic-core 2.46.5, MCP 2.2.0, mcp-types 2.2.0, pytest 9.2.0.
- `python -m pip check`: PASS, no broken requirements.
- Focused existing public contract test: PASS, 1 test (the unchanged test compares all 69 baseline tool records), 18 deselected, 2.62s.
- Full `python -m pytest -q -p no:cacheprovider`: PASS, 329 top-level tests, 0 failures/errors/skips, 1 warning, 9.12s. Raw JUnit reports `tests=826` with 329 testcase elements, counting 497 nested subtests in its aggregate; the console reports 329 passed. The focused JUnit aggregate similarly reports 70 for its one testcase plus 69 baseline comparisons.
- `python -m compileall -q onto_mcp`: PASS.
- `git diff --check`: PASS.
- Golden SHA-256 before and after: `48e82cb56ed5c24f2f9e969bdf21f7a5208c4915753ab324a2d8e2e4671534d9`.
- Evidence: `/tmp/mcp-dependency-repair-install-report.json`, `/tmp/mcp-dependency-repair-versions.json`, `/tmp/mcp-dependency-repair-freeze.txt`, `/tmp/mcp-dependency-repair-pip-check.log`, `/tmp/mcp-dependency-repair-focused-host.xml`, `/tmp/mcp-dependency-repair-full.xml`, `/tmp/mcp-dependency-repair-full.log`, `/tmp/mcp-dependency-repair-result.json`.
- Sandbox install could not resolve the package index; the fresh install succeeded on the host. The sandbox protocol probe timed out after 120 seconds; the unchanged focused test and full suite passed on the host, following the repository transport instruction. Failed sandbox receipts remain `/tmp/mcp-dependency-repair-focused.xml` and `/tmp/mcp-dependency-repair-focused.log`.
- Not run: container image build, independent review, independent QA and PREPROD checks. These are subsequent gates; these developer checks do not substitute for them.

## Commit Description (English)
- Short commit description: Pin the MCP dependency stack validated against public contracts.

## Handoff
- Remaining work: independent review of the exact dependency diff, publication to the existing candidate branch, fresh delivery installation/tests, and independent candidate/PREPROD QA under their retained authorization gates.
- Recommended next owner: independent MCP reviewer; pipeline maintainer routes the reviewed candidate onward. No push, deployment or merge performed by this task.
