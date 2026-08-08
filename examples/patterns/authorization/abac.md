# ABAC

**Category:** Authorization  
**Demo:** [abac.pys](abac.pys)  
**Wikipedia / ref:** [ABAC](https://en.wikipedia.org/wiki/Attribute-based_access_control)

## Intent

Decide from attributes (owner, admin flag, action) via a policy.

## Prompting an AI

**Say this:** “ABAC policy: allow if isAdmin or username == resourceOwner.”

**Not this:** “Only check a role string.”

**Confusion to avoid:** ABAC ≠ RBAC.

## Run

```text
python -m transpiler run examples/patterns/authorization/abac.pys
```
