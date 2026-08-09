# 10.1. App shape — Repository, Unit of Work, service layer, DTO / ACL

Your program needs a clear **inside** (domain + use-cases) and **outside**
(HTTP, SQL, legacy systems). First learn what an **Aggregate** is, then four
pattern names that keep the boundary honest: Repository, Unit of Work, service
layer, and DTO / ACL.

<figure class="concept-diagram" role="img" aria-label="Layers from domain core through application and ports to outside adapters">
  <div class="diagram-layers">
    <div class="diagram-layer diagram-layer-core">
      <strong>Domain</strong>
      <span>entities, rules you protect</span>
    </div>
    <div class="diagram-layer">
      <strong>Application service</strong>
      <span>use-case orchestration</span>
    </div>
    <div class="diagram-layer diagram-layer-edge">
      <strong>Ports</strong>
      <span>Repository and other interfaces</span>
    </div>
    <div class="diagram-layer diagram-outside">
      <strong>Adapters / outside</strong>
      <span>memory, MySQL, HTTP, legacy CSV</span>
    </div>
  </div>
  <figcaption>
    Think container: protect the core; depend inward on ports; leave messy
    shapes at the edge.
  </figcaption>
</figure>

## Aggregate

Before you can say “repository for one aggregate,” you need the word
**Aggregate** itself. It is **design vocabulary** (Domain-Driven Design), not a
PYS keyword. You already know [`entity`](chapter_4_5_structs_data_entity.md) —
a type with a stable identity key. An Aggregate is a **cluster** of domain
objects that must stay consistent together.

| Term | Means |
|------|--------|
| **`entity`** | PYS construct: identity equality via `identity(...)` |
| **Aggregate** | Design boundary: root + parts loaded / changed / saved as one unit |
| **Aggregate root** | The entry object outsiders talk to (usually one root entity) |

Classic shop picture: **`Order`** is the root; **line items** live inside the
same boundary. You do not invent a separate write API for each line when the
order’s rules (totals, status, stock) need the whole cluster.

<figure class="concept-diagram" role="img" aria-label="Dashed aggregate boundary around Order root and line items">
  <div class="diagram-boundary">
    <strong>Order aggregate</strong>
    <span>one consistency cluster</span>
    <div class="diagram-stack" style="margin-top:0.6rem;width:100%">
      <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
        <strong>Order (root)</strong>
        <span>id · status · rules</span>
      </div>
      <div class="diagram-arrow" aria-hidden="true">contains</div>
      <div class="diagram-box"><strong>OrderLine …</strong><span>parts · no separate write port</span></div>
    </div>
  </div>
  <figcaption>
    Outside code addresses the root. Parts move with the root on load and
    save — that is the aggregate boundary.
  </figcaption>
</figure>

<figure class="concept-diagram" role="img" aria-label="entity keyword versus aggregate design cluster">
  <div class="diagram-grid-2">
    <div class="diagram-box">
      <strong>entity (language)</strong>
      <span>Customer · Order · one type, one id</span>
    </div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>Aggregate (design)</strong>
      <span>Order + lines as one unit</span>
    </div>
  </div>
  <figcaption>
    An Aggregate often has a root <code>entity</code>, but the Aggregate is the
    <em>boundary</em>, not the keyword.
  </figcaption>
</figure>

### Sketch — root owns its parts

```pys
data OrderLine {
    string sku
    int qty
}

entity Order identity(orderId) {
    private fix string orderId
    private list<OrderLine> lines

    public constructor(string orderId) {
        this.orderId = orderId
        list<OrderLine> empty = []
        this.lines = empty
    }

    public void addLine(string sku, int qty) {
        list<OrderLine> xs = this.lines
        xs.append(OrderLine(sku, qty))
        this.lines = xs
    }

    public int lineCount() {
        return len(this.lines)
    }
}

Order o = Order("O-1")
o.addLine("BG-1", 2)
o.addLine("BG-2", 1)
print(o.lineCount())
```

**Output:**

```text
2
```

Lines are reached through `Order`. A repository (next section) would
`save` / `findById` this **root** — meaning the cluster, not a lone table row.

### Why repositories care

- Prefer **one repository per aggregate type** (e.g. `OrderRepository`), keyed
  by the **root id**.
- `save(order)` / `findById(id)` mean load or persist the **whole** cluster your
  rules need.
- A teaching demo may show a single-entity Aggregate for brevity
  ([`repository.pys`](../examples/patterns/persistence/repository.pys)); living
  shops under [`examples/rest-api/shop/`](../examples/rest-api/shop/) model
  orders and lines — use Aggregate vocabulary even when the demo is thin.
  The JavaScript Express twin lives under
  [`examples/by-target/javascript/rest-api/express/`](../examples/by-target/javascript/rest-api/express/).

### Non-golden note

Updating a line item **in isolation** while totals or status live on the order
breaks the boundary. **Unit of Work** (later) batches a *transaction*;
**Aggregate** answers *what belongs together* inside that transaction.

### Prompt dialogue

> **You:** Treat `Order` as the aggregate root; line items are parts of that
> Aggregate. Persist through `OrderRepository` by order id — do not expose a
> separate write service for lines that bypasses order rules.
>
> **Not:** “Every table gets its own repository and the handler updates lines
> directly.”

### Exercise

> Is `entity Customer` automatically an Aggregate? (Answer: it can be a
> one-object Aggregate, but Aggregate names the *consistency boundary*; the
> keyword alone does not.)

## Repository

A **Repository** is a port that looks like a collection for **one Aggregate**
(usually addressed by the aggregate root’s id): `save`, `findById`. Application
code depends on the interface; an adapter talks to memory or MySQL.

<figure class="concept-diagram" role="img" aria-label="Caller uses OrderRepository socket; InMemoryOrderRepository machine wires the socket">
  <div class="diagram-stack">
    <div class="diagram-box"><strong>PlaceOrderService</strong><span>caller · depends on the socket</span></div>
    <div class="diagram-arrow" aria-hidden="true">↓</div>
    <div class="diagram-box diagram-layer-edge" style="border-style:dashed;border-width:2px;background:#f5ecd8;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>OrderRepository</strong>
      <span>interface · port · save / findById</span>
    </div>
    <div class="diagram-arrow" aria-hidden="true">↓</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>InMemoryOrderRepository</strong>
      <span>adapter · real storage behind the port</span>
    </div>
  </div>
  <figcaption>
    Same socket idea as interfaces: the service holds a fitting cable to the
    port; swap the adapter without rewriting the use-case.
  </figcaption>
</figure>

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

<figure class="concept-diagram" role="img" aria-label="Pending tray of products then commit writes them or rollback empties the tray">
  <div class="diagram-flow" style="min-width:28rem">
    <div class="diagram-box"><strong>Pending tray</strong><span>registerNew products</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>commit()</strong>
      <span>write through store</span>
    </div>
    <div class="diagram-arrow" aria-hidden="true">or</div>
    <div class="diagram-box diagram-outside">
      <strong>rollback()</strong>
      <span>drop pending work</span>
    </div>
  </div>
  <figcaption>
    Batch first, then one decision: keep all changes or keep none.
  </figcaption>
</figure>

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

<figure class="concept-diagram" role="img" aria-label="Thin HTTP edge calls CreateOrderService which uses OrderRepository and Clock ports">
  <div class="diagram-flow" style="min-width:32rem">
    <div class="diagram-box diagram-outside"><strong>HTTP / CLI</strong><span>thin edge</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>CreateOrderService</strong>
      <span>use-case</span>
    </div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>Ports</strong><span>Repository · Clock</span></div>
  </div>
  <figcaption>
    Controllers stay thin; the named use-case owns the workflow.
  </figcaption>
</figure>

Demo: [`service_layer.pys`](../examples/patterns/application/service_layer.pys).

**Output:**

```text
created:O-9@2026-08-08T12:00:00Z
```

## DTO and Anti-Corruption Layer

- **Anti-Corruption Layer (ACL):** map foreign field names into your domain at
  the edge.
- **DTO:** flat shape for APIs/UI — not your entity.

<figure class="concept-diagram" role="img" aria-label="Legacy foreign row crosses dashed ACL boundary into domain CatalogItem then out as DTO">
  <div class="diagram-stack">
    <div class="diagram-box diagram-outside"><strong>Legacy row</strong><span>product_code · descr · price_cents</span></div>
    <div class="diagram-boundary">
      <strong>Anti-Corruption Layer</strong>
      <span>translate names at the edge</span>
    </div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>CatalogItem (domain)</strong>
      <span>sku · title · Money</span>
    </div>
    <div class="diagram-arrow" aria-hidden="true">↓</div>
    <div class="diagram-box"><strong>CatalogItemDto</strong><span>flat transport for API / UI</span></div>
  </div>
  <figcaption>
    Foreign keys never leak past the dashed boundary into domain services.
  </figcaption>
</figure>

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

[Previous: How these diagrams work](chapter_9_0_visual_style.md) · [Next: Multitier architecture](chapter_9_1a_multitier.md)
