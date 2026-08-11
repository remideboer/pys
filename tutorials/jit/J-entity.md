# JIT — `entity` (identity keys)

## Forms

```pys
entity Customer identity(customerId) {
    private fix int customerId
    public string name

    public constructor(int customerId, string name) {
        this.customerId = customerId
        this.name = name
    }
}

Customer a = Customer(7, "Ana")
Customer b = Customer(7, "Ana B.")
print(a == b)  # True — same customerId
```

Shared key (child omits `identity`):

```pys
entity User inherits Account {
    public string username
    ...
}
```

Composite key (child appends):

```pys
entity OrderLine inherits Order identity(lineNumber) {
    private fix int lineNumber
    ...
}
# Effective key: (orderId, lineNumber) — parent fields first
```

## Rules

1. Root entity: `identity(...)` is **mandatory**  
2. Every identity field must be declared `fix` in that entity’s body  
3. Explicit constructor required; omitted field/method access ⇒ `module` (same-file)  
4. `==` / hash / string form use **identity fields only** (not overridable)  
5. May `inherits` another **entity** only; no `uses` / `implements`  
6. Non-key fields may change; key fields stay `fix`  
7. **Body order**: identity fields → other `fix` → mutable → ctor → methods — [J-member-order](J-member-order.md)

Lifecycle / row identity → **`entity`**. Immutable value → [`data`](J-data.md).
General OOP → [`J-class`](J-class.md).

MySQL CRUD walkthrough (menus + identity demos):
[`examples/database/`](../../examples/database/).

Full rationale: [`docs/DATA_ENTITY.md`](../../docs/DATA_ENTITY.md).
