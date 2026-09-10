# Realm declaration publication guidance correction

## Scope

Corrected only the canonical `how_to_use_onto_mcp` guidance at base
`dc5fc7b308b769ca9383b9e9d08fccee2dccb871`. The publication route remains
terminal with `next_calls=[]` until an exact owner-approved Constitutional
Steward package and its gates are present.

## Contract effect

The runtime answer, safety notes, machine-readable contract, and rendered guide
now state that publication storage uses the existing MemoryArtifact tools in
this exact order:

`create_memory_artifact_draft -> get_memory_artifact ->
submit_memory_artifact -> get_memory_artifact -> accept_memory_artifact ->
get_memory_artifact -> get_memory_artifact_by_path/about_realm`.

They specify the 400-avoiding draft contract: canonical `realm_id`, exact path
`realm/declaration`, `decision`, `replace`, the exact canonical
`realm_declaration@1` UTF-8 JSON string without trailing LF/BOM, nonempty
summary/source ref, approved-package review destination, and exactly one
primary realm target whose id equals `realm_id`. Initial publication omits
`supersedes_artifact_id`; a successor provides the exact accepted/current
predecessor only on the create-draft call.

The guidance explicitly rejects `update_realm` and arbitrary/probe artifacts.
It no longer says declaration publication is not a MemoryArtifact lifecycle or
implies that the existing tools are missing.

## Validation

```text
Focused contract suite: 55 passed in 0.26s
Full suite: 203 passed, 2 skipped in 4.70s
python3 -m compileall -q onto_mcp: passed
python3 -m json.tool onto_mcp/agent_contract.json: passed
git diff --check: passed
```

The two skips are unchanged existing real-FastMCP isolation behavior. No
backend/resolver source, deploy, environment, realm, declaration, governance,
subject, memory, or object-chat state was changed. Independent review remains
required.
