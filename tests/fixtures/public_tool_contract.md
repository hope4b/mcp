# Public tool contract golden

`public_tool_contract.json` was captured from the independent pre-batch MCP
source at commit `50d57adbd99d4f67f2ef8c2a52b6470c21a7a1a6` (tree
`3b76bcaa243723cf7c12153f149d3e86ae9677f5`), using the
`_PUBLIC_CONTRACT_PROBE` in `tests/test_server_runtime.py`. It contains all 69
existing tools, their complete protocol metadata/input/output schemas and the
probe's deterministic success/error envelopes. It was not generated from the
batch candidate. File SHA256 at capture:
`48e82cb56ed5c24f2f9e969bdf21f7a5208c4915753ab324a2d8e2e4671534d9`.

Capture procedure: export only `onto_mcp` from that commit into a temporary
directory with `git archive`; run the probe there with the current interpreter,
`PYTHONPATH` pointing solely to that directory, stdio transport, and the probe's
non-routable API base and dummy API key. Save the unique
`PUBLIC_CONTRACT_SNAPSHOT=` JSON output as indented UTF-8 JSON. No tool body or
network dependency is called. A local-only periodic asyncio timer was needed
to wake worker completions in this author's sandbox; it changed no tool,
transport, schema, result converter or envelope. No workaround is required by
the committed test. Capture logs: `/tmp/mcp-runtime-repair-baseline-assisted.log`.

The recorded Python/FastMCP versions describe capture provenance. They are not
public contract fields: the regression compares every tool record exactly,
without requiring a matching Python patch version. A dependency change that
changes public metadata or envelopes still fails the comparison and requires
review; do not regenerate the golden merely to obtain a pass.

The only permitted inventory addition is `create_relations_batch`. The
regression neither removes that tool from the live probe nor filters fields
from existing tool records. Batch-specific schema/envelope checks remain in
`tests/test_relation_batch.py`. An unrelated addition, removal, or change to an
existing record must fail.
