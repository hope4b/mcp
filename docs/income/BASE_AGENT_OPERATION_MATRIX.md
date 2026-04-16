# Base Agent Operation Matrix

## Status
- State: `draft`
- Scope: minimum operation surface that the `base` agent must expose to the user after onboarding

## Purpose
- Record the minimum semantic operation coverage expected from the `base` agent.
- Map user-visible semantic actions to concrete Onto API operation IDs.
- Keep API-level capability inventory out of `REQUIREMENTS.md` while preserving a reviewable source of truth.

## Source Of Truth
- `D:\git\onto\_assist\onto-docs\income\api-onto.json`
- This matrix is intentionally API-oriented. Controller names are implementation detail and should not be treated as the stable capability boundary.

## Operation Surface

### Realm
- `createRealm` - create
- `updateRealm` - update
- `deleteRealm` - delete

### Template
- `saveMetaEntity` - create
- `saveMetaEntity` - update
- `deleteMetaEntity` - delete
- `getMetaEntity` - read
- `getFilteredRealmMeta` - read
- `linkMetaEntityToParents` - update

### Knowledge Base Entity
- `saveEntity` - create
- `saveEntity` - update
- `saveEntityBatch` - create
- `saveEntityBatch` - update
- `changeMetaEntity` - update
- `getEntity` - read
- `searchEntities` - read
- `searchEntitiesWithRelatedMeta` - read
- `deleteEntity` - delete

### Relation
- `createRelation` - create
- `updateRelation` - update
- `deleteRelation` - delete

### Relation Template
- `createMetaRelation` - create
- `updateMetaRelation` - update
- `deleteMetaRelation` - delete

### Object Fields
- `saveFields` - update
- `deleteFields` - delete

### Template-Derived Fields
- `saveFields` - update
- `deleteFields` - delete

### Template Fields
- `saveMetaFields` - update
- `deleteMetaFields` - delete

### Diagram
- `createDiagram` - create
- `createDiagram` - update
- `getDiagram` - read
- `updateDiagram` - update
- `deleteDiagram` - delete

## Notes
- `createDiagram` currently has upsert semantics (`create + update`). This is operation-level technical debt and should not be silently hidden by assistant documentation.
- If API operation IDs or paths change in `api-onto.json`, this matrix should be updated before changing capability claims for the `base` agent.
