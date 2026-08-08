# Identity Map

**Category:** Persistence  
**Demo:** [identity_map.pys](identity_map.pys)  
**Wikipedia / ref:** [Identity Map](https://martinfowler.com/eaaCatalog/identityMap.html)

## Intent

Same id resolves to the same instance within a session.

## Prompting an AI

**Say this:** “IdentityMapSession.get twice; mutate one, observe the other.”

**Not this:** “new entity from DB on every lookup in one request.”

**Confusion to avoid:** Identity Map ≠ cache-aside (identity vs performance).

## Run

```text
python -m transpiler run examples/patterns/persistence/identity_map.pys
```
