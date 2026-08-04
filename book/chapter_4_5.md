# 5.5. Structs, data, and entity

Three ways to bundle fields without “full” class identity semantics.

## `struct` — identity-free value bag

Fields only (no methods). Copy on assign; `==` compares fields.

```pys
struct Damage {
    int amount
    string type
}

Damage d1 = Damage(20, "physical")
Damage d2 = Damage(amount=20, type="physical")
print(d1 == d2)
```

Output:

```text
True
```


> **Sidebar — named constructor arguments**
>
> `Damage(20, "physical")` fills fields in declaration order.
> `Damage(amount=20, type="physical")` names each field — handy when
> optional trailing fields appear later.

## `data` — value object

All fields immutable; equality over **all** fields; generated contract.

```pys
data Money {
    int amountCents
    string currency
}

Money m1 = Money(10000, "USD")
Money m2 = Money(10000, "USD")
print(m1 == m2)
```

Output:

```text
True
```


## `entity` — identity key

Equality uses only `identity(...)` fields (must be `fix`).

```pys
entity Customer identity(customerId) {
    private fix int customerId
    public string name

    public Customer(int customerId, string name) {
        this.customerId = customerId
        this.name = name
    }
}

Customer a = Customer(7, "Ana")
Customer b = Customer(7, "Ana B.")
print(a == b)
```

Output:

```text
True
```


Body order for entities: identity fields → other `fix` → mutable →
constructors → methods.

### Exercise

> Define `data Temperature { float celsius }` and construct two equal
> instances. Confirm `==` is true.

---

[Previous: Traits](chapter_4_4.md) · [Next: Choosing the right construct](chapter_4_6.md)
