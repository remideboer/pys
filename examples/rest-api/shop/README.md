# REST shop API (teaching progression)

Layered examples so students can see each concern land separately:

| Folder | Phase | Status |
|--------|-------|--------|
| [`memory/`](memory/) | 1 — HTTP + JSON CRUD, in-memory repos | **Runnable** |
| [`mysql/`](mysql/) | 2 — Same API, MySQL persistence | Deferred ([F-008](../../docs/TODO-FUTURE.md#f-008-rest-shop-mysql)) |
| [`jwt/`](jwt/) | 3 — Auth with JWT on top of MySQL | Deferred ([F-009](../../docs/TODO-FUTURE.md#f-009-rest-shop-jwt)) |

Domain entities match the console shop (`Product`, `Order`, `OrderLine` from
`examples/database`). Phase 1 copies a slim HTTP/1.1 stack from
`examples/webserver` (no circuit breaker / TLS / HTTP/2).

## Quick start (phase 1)

```bash
python -m transpiler run examples/rest-api/shop/memory/src/main.pys
curl http://127.0.0.1:8090/health
```

See [`memory/README.md`](memory/README.md) for the full curl cookbook.
