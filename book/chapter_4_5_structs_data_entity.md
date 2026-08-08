# 5.6. Structs, data, and entity

Three ways to bundle fields without “full” class identity semantics.

<figure class="concept-diagram" role="img" aria-label="Three value bundles: struct bag, data value object, entity with identity key">
  <div class="diagram-grid-2" style="grid-template-columns:repeat(3,minmax(0,1fr))">
    <div class="diagram-box"><strong>struct</strong><span>field bag · copy · field ==</span></div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>data</strong>
      <span>immutable VO · all-field ==</span>
    </div>
    <div class="diagram-box diagram-layer-edge" style="border-style:dashed;border-width:2px;background:#f5ecd8;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>entity</strong>
      <span>identity(...) key · id ==</span>
    </div>
  </div>
  <figcaption>
    Three bundles, three equality stories — pick the story, not only the
    keyword.
  </figcaption>
</figure>

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
> optional trailing fields appear later. Do not mix styles in one call
> (`Damage(20, type="physical")` is illegal).

## `data` — value object (VO)

A **value object** (VO) is a bundle you treat as a *value*: two instances with
the same fields are interchangeable. In PYS, `data` is that construct.

What `data` locks in for you (sometimes called the **VO ceremony** — the
fixed rules you accept by choosing `data` instead of a plain `struct`):

1. every field is immutable (`fix`)
2. `==` / hashing compare **all** fields
3. no methods, no inheritance — only the value

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


> **Sidebar — `struct` vs `data`**
>
> Prefer `struct` when you only need a small field bag (fields may stay
> mutable; no full VO rules). Prefer `data` when the value must stay
> immutable and interchangeable — money, color, a point on a map.

## `entity` — identity key

Equality uses only `identity(...)` fields (must be `fix`). Two customers
with the same id are the same customer even if the name changed — that is
*identity* equality, opposite of `data`’s all-fields value equality.

<figure class="concept-diagram" role="img" aria-label="data Money equal when all fields match versus entity Customer equal when only id matches">
  <div class="memory-compare">
    <div class="concept-diagram" style="margin:0;max-width:18rem">
      <div class="diagram-stack">
        <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
          <strong>data Money</strong>
          <span>10000 · USD</span>
        </div>
        <div class="diagram-arrow" aria-hidden="true">==</div>
        <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
          <strong>data Money</strong>
          <span>10000 · USD</span>
        </div>
        <div class="diagram-box" style="margin-top:0.4rem"><strong>all fields</strong><span>True</span></div>
      </div>
    </div>
    <div class="memory-compare-arrow" aria-hidden="true">vs</div>
    <div class="concept-diagram" style="margin:0;max-width:18rem">
      <div class="diagram-stack">
        <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
          <strong>Customer 7</strong>
          <span>Ana</span>
        </div>
        <div class="diagram-arrow" aria-hidden="true">==</div>
        <div class="diagram-box"><strong>Customer 7</strong><span>Ana B.</span></div>
        <div class="diagram-box" style="margin-top:0.4rem"><strong>identity only</strong><span>True — name ignored</span></div>
      </div>
    </div>
  </div>
  <figcaption>
    Same field values make <code>data</code> equal. Same id makes an
    <code>entity</code> equal — even when other fields differ.
  </figcaption>
</figure>

> **Sidebar — why a language keyword?**
>
> Other languages often leave this to frameworks (`@Id`, `[Key]`) and hand-
> written `equals`/`hashCode`, which is a common source of `HashSet` bugs.
> PYS checks `identity(...)` and immutability at compile time. Longer story
> with real-world cases: [`docs/DATA_ENTITY.md`](../docs/DATA_ENTITY.md).

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

[Previous: Traits](chapter_4_4_traits.md) · [Next: Choosing the right construct](chapter_4_6_choosing_construct.md)
