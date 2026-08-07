# REST shop API (teaching progression)

| Folder | Phase | Status |
|--------|-------|--------|
| [`memory/`](memory/) | 1 — HTTP + JSON CRUD, in-memory | **Done** |
| [`mysql/`](mysql/) | 2 — MySQL persistence | **Done** |
| [`jwt/`](jwt/) | 3 — JWT on writes | **Done** |

```bash
python -m transpiler run examples/rest-api/shop/memory/src/main.pys   # :8090
python -m transpiler run examples/rest-api/shop/mysql/src/main.pys    # :8091
python -m transpiler run examples/rest-api/shop/jwt/src/main.pys      # :8092
```
