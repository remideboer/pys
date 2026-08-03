# JIT — `data` (value objects)

## Forms

```pys
data Money {
    int amountCents
    string currency
}

Money m1 = Money(10000, "USD")
Money m2 = Money(amountCents=10000, currency="USD")
print(m1 == m2)  # True — all fields

Money m3 = Money(m1.amountCents, "EUR")  # new instance, not a mutation
```

## Rules

1. Fields only — no methods, no `inherits` / `uses` / `implements`  
2. Fields are implicitly `fix` and public (no `fix` keyword needed)  
3. Construct with `Type(...)` like a `struct`  
4. Assignment / call / return **copy** the value  
5. `==` / hash / string form are generated over **all** fields (not overridable)  

Immutable interchangeable values → **`data`**. Ad-hoc bag without VO contract →
[`struct`](J-struct.md). Lifecycle row with a key → [`entity`](J-entity.md).

Full rationale: [`docs/DATA_ENTITY.md`](../../docs/DATA_ENTITY.md).
