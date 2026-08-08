# ACL

**Category:** Authorization  
**Demo:** [acl.pys](acl.pys)  
**Wikipedia / ref:** [ACL](https://en.wikipedia.org/wiki/Access-control_list)

## Intent

Per-resource list of allowed principals.

## Prompting an AI

**Say this:** “Use an ACL map resourceId → principals for order O-1.”

**Not this:** “Give every clerk access to every order.”

**Confusion to avoid:** ACL ≠ RBAC (resource list vs role permissions).

## Run

```text
python -m transpiler run examples/patterns/authorization/acl.pys
```
