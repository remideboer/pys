# 10.1. App shape — Repository, Unit of Work, service layer, DTO / ACL

Your program needs a clear **inside** (domain + use-cases) and **outside**
(HTTP, SQL, legacy systems). Four names keep that boundary honest.

## Repository

A **Repository** is a port that looks like a collection for one aggregate:
`save`, `findById`. Application code depends on the interface; an adapter talks
to memory or MySQL.

```pys
interface OrderRepository {
    save(Order order)
    nullable<Order> findById(string orderId)
}
```

Full demo: [`examples/patterns/persistence/repository.pys`](../examples/patterns/persistence/repository.pys).

```text
python -m transpiler run examples/patterns/persistence/repository.pys
```

**Output:**

```text
placed:O-1
True
True
```

### Prompt dialogue

> **You:** Persist orders with a Repository port and an in-memory adapter. The
> use-case takes the repository in its constructor.
>
> **Not:** Stick a global `dict` in the route handler.

## Unit of Work

A **Unit of Work** gathers changes during one business transaction, then
`commit()` or `rollback()`.

Demo: [`unit_of_work.pys`](../examples/patterns/persistence/unit_of_work.pys).

**Output (concept):** first product visible after commit; second missing after
rollback.

```text
True
True
```

**Confusion:** Unit of Work ≠ Repository.

## Service layer

An **application service** (service layer) is a use-case class: orchestrate
ports, return a result, no HTTP/SQL.

Demo: [`service_layer.pys`](../examples/patterns/application/service_layer.pys).

**Output:**

```text
created:O-9@2026-08-08T12:00:00Z
```

## DTO and Anti-Corruption Layer

- **Anti-Corruption Layer (ACL):** map foreign field names into your domain at
  the edge.
- **DTO:** flat shape for APIs/UI — not your entity.

Demo: [`dto_acl.pys`](../examples/patterns/application/dto_acl.pys).

**Output:**

```text
BG-001
4599 EUR
Catan
```

### Non-golden note

If the legacy row is incomplete, fix the adapter contract — do not sprinkle
`product_code` through domain services.

### Exercise

> Name the pattern: “I need to save three new rows only if stock checks pass;
> otherwise nothing is written.” (Answer: Unit of Work, often with a Repository.)

---

[Previous: Patterns session](chapter_9_session_patterns.md) · [Next: Authorization](chapter_9_2_authorization.md)
