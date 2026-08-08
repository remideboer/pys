# 10.1. App shape — Repository, Unit of Work, service layer, DTO / ACL

Your program needs a clear **inside** (domain + use-cases) and **outside**
(HTTP, SQL, legacy systems). Four names keep that boundary honest.

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

## Repository

A **Repository** is a port that looks like a collection for one aggregate:
`save`, `findById`. Application code depends on the interface; an adapter talks
to memory or MySQL.

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
