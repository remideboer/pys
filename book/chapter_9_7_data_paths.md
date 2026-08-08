# 10.7. Data paths — cache, versions, mappers, identity

## Cache-aside

Read cache → miss → load store → populate cache.

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

Demo: [`data_mapper_vs_active_record.pys`](../examples/patterns/persistence/data_mapper_vs_active_record.pys)

**Output:**

```text
Catan
Ticket
```

## Identity Map

Within one session, same id → **same instance**.

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
