# Realm declaration publication oracle correction

## Scope

Remediated only `MCP-PUB-GUIDE-BLOCK-001` and
`MCP-PUB-GUIDE-BLOCK-002` from the exact independent review on base
`971cc4cbcae8e631b9889be476ea5dcfa1afaa69`.

## Contract effect

The runtime answer, safety notes, machine-readable contract, and rendered guide
now expose the complete closed `realm_declaration@1` body oracle: exact keys,
constants and types; outer/body/target realm-id equality; nonempty purpose;
ordered, nonempty, unique boundaries; ordered closed routes with four required
nonempty strings and the optional nonempty `next_discovery_step` omitted rather
than null; and no undeclared fields or duplicate JSON keys.

They require one RFC 8785 canonicalization, exact UTF-8 without BOM or trailing
LF, a maximum of 65,536 bytes inclusive, hashing those exact bytes, and passing
the unchanged resulting JSON text as the draft's `body` string. The structured
template distinguishes that string from the real `targets` array.

The lifecycle contour is eight distinct ordered calls. Artifact-ID reads require
`draft`, then `proposed`, then `accepted/current`, with unchanged bound fields
and body. The exact-path read requires the same artifact id/body; the subsequent
`about_realm` read requires `accepted_current` and the exact body/hash. Any
failed or ambiguous read-back stops without replay, fallback, or a second
candidate.

The publication route continues to emit `next_calls=[]` until the exact
owner-approved Constitutional Steward package and gates are present. No runtime
mutation was performed.

## Validation

```text
Focused contract suite: 55 passed in 0.24s
Full suite: 203 passed, 2 skipped
python3 -m compileall -q onto_mcp: passed
python3 -m json.tool onto_mcp/agent_contract.json: passed
git diff --check: passed
```

The two skips are unchanged existing real-FastMCP isolation behavior. Fresh
independent confirmation remains required.
