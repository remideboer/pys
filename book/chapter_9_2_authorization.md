# 10.2. Authorization — RBAC, ACL, ABAC

**Authentication** answers *who are you?* (see
[`examples/patterns/authentication/`](../examples/patterns/authentication/)).
**Authorization** answers *what may you do?*

<figure class="concept-diagram" role="img" aria-label="Fork: AuthN proves identity then AuthZ decides allowed actions">
  <div class="diagram-flow" style="min-width:28rem">
    <div class="diagram-box"><strong>AuthN</strong><span>who are you?</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>AuthZ</strong>
      <span>what may you do?</span>
    </div>
  </div>
  <figcaption>
    Login proves identity; a separate decision grants or denies the action.
  </figcaption>
</figure>

## RBAC (role-based)

Users have **roles**; roles have **permissions**.

<figure class="concept-diagram" role="img" aria-label="User maps to role maps to permissions list">
  <div class="diagram-flow" style="min-width:30rem">
    <div class="diagram-box"><strong>User</strong><span>ada</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>Role</strong><span>admin</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>Permissions</strong>
      <span>order:read · order:write</span>
    </div>
  </div>
  <figcaption>
    Authorize by permission name, not by hard-coded usernames in every handler.
  </figcaption>
</figure>

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

<figure class="concept-diagram" role="img" aria-label="Resource order O-1 lists principals ada and bob">
  <div class="diagram-stack">
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>Resource order:O-1</strong>
      <span>one list of who may touch it</span>
    </div>
    <div class="diagram-arrow" aria-hidden="true">↓</div>
    <div class="diagram-box"><strong>Principals</strong><span>ada · bob</span></div>
  </div>
  <figcaption>
    Per-resource membership — different from role-wide permissions.
  </figcaption>
</figure>

Demo: [`acl.pys`](../examples/patterns/authorization/acl.pys)

**Output:**

```text
True
False
False
```

## ABAC (attribute-based)

A **policy** decides from attributes: owner, admin flag, action.

<figure class="concept-diagram" role="img" aria-label="Attributes feed a policy box that outputs allow or deny">
  <div class="diagram-flow" style="min-width:32rem">
    <div class="diagram-box"><strong>Attributes</strong><span>owner · isAdmin · action</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-boundary">
      <strong>Policy</strong>
      <span>OwnerOrAdmin</span>
    </div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>allow / deny</strong><span>one decision</span></div>
  </div>
  <figcaption>
    Rules read attributes; useful when “owner or admin” is the real rule.
  </figcaption>
</figure>

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

[Previous: Multitier architecture](chapter_9_1a_multitier.md) · [Next: Resilience](chapter_9_3_resilience.md)
