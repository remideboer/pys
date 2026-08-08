# RBAC

**Category:** Authorization  
**Demo:** [rbac.pys](rbac.pys)  
**Wikipedia / ref:** [RBAC](https://en.wikipedia.org/wiki/Role-based_access_control)

## Intent

Map users to roles and roles to permissions; authorize by permission name.

## Prompting an AI

**Say this:** “Add RBAC: roles admin/clerk with permissions order:read/write. authorize(user, permission).”

**Not this:** “Hard-code if username == admin everywhere.”

**Confusion to avoid:** RBAC ≠ authentication (login).

## Run

```text
python -m transpiler run examples/patterns/authorization/rbac.pys
```
