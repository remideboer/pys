# 10.2. Authorization — RBAC, ACL, ABAC

**Authentication** answers *who are you?* (see
[`examples/patterns/authentication/`](../examples/patterns/authentication/)).
**Authorization** answers *what may you do?*

## RBAC (role-based)

Users have **roles**; roles have **permissions**.

Demo: [`rbac.pys`](../examples/patterns/authorization/rbac.pys)

```text
python -m transpiler run examples/patterns/authorization/rbac.pys
```

**Output:**

```text
True
False
True
False
```

### Prompt dialogue

> **You:** Add RBAC. Admin may `order:write`; clerk only `order:read`.
> Authorize with `allows(username, permission)`.
>
> **Not:** `if (user == "ada")` scattered in every handler.

## ACL (access-control list)

A **resource** maps to allowed **principals** (users or groups).

Demo: [`acl.pys`](../examples/patterns/authorization/acl.pys)

**Output:**

```text
True
False
False
```

## ABAC (attribute-based)

A **policy** decides from attributes: owner, admin flag, action.

Demo: [`abac.pys`](../examples/patterns/authorization/abac.pys)

**Output:**

```text
True
False
True
```

### Confusion card

| Name | Idea |
|------|------|
| AuthN | Prove identity |
| RBAC | Roles → permissions |
| ACL | Resource → who |
| ABAC | Attributes → decision |

### Exercise

> A shared document should be editable by its owner or any admin. Which pattern
> fits best? (ABAC, or RBAC plus an ownership check.)

---

[Previous: App shape](chapter_9_1_app_shape.md) · [Next: Resilience](chapter_9_3_resilience.md)
