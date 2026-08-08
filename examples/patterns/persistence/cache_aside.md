# Cache-aside

**Category:** Persistence  
**Demo:** [cache_aside.pys](cache_aside.pys)  
**Wikipedia / ref:** [Cache-aside](https://learn.microsoft.com/azure/architecture/patterns/cache-aside)

## Intent

Read cache; on miss load store and populate cache.

## Prompting an AI

**Say this:** “CacheAside.get: miss then hit for same sku.”

**Not this:** “Cache forever with no invalidation story.”

**Confusion to avoid:** Cache-aside ≠ write-through.

## Run

```text
python -m transpiler run examples/patterns/persistence/cache_aside.pys
```
