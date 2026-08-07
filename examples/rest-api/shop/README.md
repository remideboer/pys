# REST shop API (teaching progression)

Layered examples so students can see each concern land separately:

| Folder | Phase | Status |
|--------|-------|--------|
| [`memory/`](memory/) | 1 — HTTP + JSON CRUD, in-memory repos | **Done** |
| [`mysql/`](mysql/) | 2 — Same API, MySQL persistence | **Done** |
| [`jwt/`](jwt/) | 3 — Auth with JWT on top of MySQL | Deferred ([F-009](../../docs/TODO-FUTURE.md#f-009-rest-shop-jwt)) |

Domain entities match the console shop (`Product`, `Order`, `OrderLine`).

## Quick start

```bash
# Phase 1 — no database
python -m transpiler run examples/rest-api/shop/memory/src/main.pys
curl http://127.0.0.1:8090/health

# Phase 2 — needs MySQL shop schema/seed
python -m transpiler run examples/rest-api/shop/mysql/src/main.pys
curl http://127.0.0.1:8091/health
```

See each folder’s README for curl cookbooks.
