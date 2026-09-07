# Realm-description how-to hardening correction

## Scope

Closed only independent review finding `HOWTO-REV-BLOCK-001` on base commit
`80eed01b9f4aed9ad28c9a1c4f5b0f95092812ab`.

The bounded Russian publication stem in
`_REALM_DECLARATION_PUBLICATION_RE` was corrected from `опубликов` to
`опублик`. Because the matcher still simultaneously requires the exact
`realm/declaration` path or the phrase `декларация пространства`, this covers
the natural imperatives `Опубликуй` and `Опубликуйте` without reclassifying
unrelated requests.

The exact review transcript `Опубликуй декларацию пространства` and its polite
imperative variant now assert:

- `next_calls=[]`;
- an owner-decided Constitutional Steward handoff with separate package/gates;
- the exhaustive avoid set of every registered tool except the two canonical
  safe realm-description reads; and
- no resolver discovery, mutation, generic read fallback, or broad exploration.

## Validation

```text
Focused contract suite: 53 passed in 0.24s
Full suite: 201 passed, 2 skipped in 4.60s
python3 -m compileall -q onto_mcp: passed
git diff --check: passed
```

The two skips are unchanged existing real-FastMCP isolation behavior. No
resolver/backend, deploy, realm, declaration-publication, governance, subject,
memory, or object-chat state was changed. Fresh independent confirmation of
the correction commit remains required.
