# 10.7. Data paths — cache, versions, mappers, identity

## Cache-aside

Read cache → miss → load store → populate cache.

<figure class="concept-diagram" role="img" aria-label="Cache miss loads store then hit returns from cache">
  <div class="diagram-flow" style="min-width:34rem">
    <div class="diagram-box"><strong>get(sku)</strong><span>ask cache</span></div>
    <div class="diagram-arrow" aria-hidden="true">miss</div>
    <div class="diagram-box diagram-outside"><strong>Store</strong><span>load</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>populate</strong>
      <span>next call = hit</span>
    </div>
  </div>
  <figcaption>
    The app owns the cache fill — miss once, then hit.
  </figcaption>
</figure>

Demo: [`cache_aside.pys`](../examples/patterns/persistence/cache_aside.pys)

**Output:**

```text
cache-miss:BG-001
Catan
cache-hit:BG-001
Catan
True
```

## Optimistic concurrency

Carry a **version**; reject stale updates.

<figure class="concept-diagram" role="img" aria-label="Update succeeds when expected version matches; stale version denied">
  <div class="diagram-grid-2">
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>expectedVersion = 0</strong>
      <span>matches · write v1</span>
    </div>
    <div class="diagram-box" style="border:2px solid #8a6d3b;background:#f5ecd8;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>expectedVersion = 0 again</strong>
      <span>stale · reject</span>
    </div>
  </div>
  <figcaption>
    Last writer does not silently win — versions gate the update.
  </figcaption>
</figure>

Demo: [`optimistic_concurrency.pys`](../examples/patterns/persistence/optimistic_concurrency.pys)

**Output:**

```text
True
False
v1
1
```

## Data Mapper vs Active Record

| Style | Who knows persistence? |
|-------|-------------------------|
| Active Record | The row object (`save()` on itself) |
| Data Mapper | A mapper outside the domain object |

<figure class="concept-diagram" role="img" aria-label="Active Record saves itself versus Data Mapper outside the domain object">
  <div class="memory-compare">
    <div class="concept-diagram" style="margin:0;max-width:18rem">
      <div class="diagram-stack">
        <div class="diagram-box" style="border:2px solid #8a6d3b;background:#f5ecd8;padding:0.7rem;border-radius:6px;text-align:center">
          <strong>ArProduct</strong>
          <span>save() on itself</span>
        </div>
        <div class="diagram-box diagram-outside"><strong>db</strong><span>row knows the store</span></div>
      </div>
    </div>
    <div class="memory-compare-arrow" aria-hidden="true">vs</div>
    <div class="concept-diagram" style="margin:0;max-width:18rem">
      <div class="diagram-stack">
        <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
          <strong>DmProduct</strong>
          <span>data only</span>
        </div>
        <div class="diagram-box"><strong>ProductMapper</strong><span>persistence outside</span></div>
      </div>
    </div>
  </div>
  <figcaption>
    Prefer mapper style when you want domain objects free of storage verbs.
  </figcaption>
</figure>

Demo: [`data_mapper_vs_active_record.pys`](../examples/patterns/persistence/data_mapper_vs_active_record.pys)

**Output:**

```text
Catan
Ticket
```

## Identity Map

Within one session, same id → **same instance**.

<figure class="concept-diagram" role="img" aria-label="First get loads O-1; second get returns same instance from map">
  <div class="diagram-flow" style="min-width:32rem">
    <div class="diagram-box"><strong>get("O-1")</strong><span>map-load</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>Identity Map</strong>
      <span>one instance per id</span>
    </div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>get("O-1")</strong><span>map-hit · same object</span></div>
  </div>
  <figcaption>
    Mutating through one reference is visible on the other — same identity.
  </figcaption>
</figure>

Demo: [`identity_map.pys`](../examples/patterns/persistence/identity_map.pys)

**Output:**

```text
map-load:O-1
map-hit:O-1
shipped
```

### Prompt dialogue

> **You:** Use cache-aside for product titles and optimistic concurrency
> (version) on document updates. Prefer Data Mapper over Active Record for the
> domain model.
>
> **Not:** “Just update the row.”

---

[Previous: Composable rules](chapter_9_6_composable_rules.md) · [Next: Prompting an AI](chapter_9_8_prompting_ai.md)
