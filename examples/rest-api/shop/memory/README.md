# Phase 1 — In-memory shop REST API

Self-contained HTTP/1.1 JSON API. Entities match the console shop; storage is
process memory (lost on restart). No auth (see [`../jwt/`](../jwt/) later).

## Run

```bash
python -m transpiler run examples/rest-api/shop/memory/src/main.pys
```

Or right-click this folder’s `pys.toml` → **Run Project** (`[project].main`).

Listens on `127.0.0.1:8090`. Seeds three board-game products.

## Tests

```bash
set PYS_WORKSPACE_ROOT=examples\rest-api\shop\memory
python -m transpiler run examples/rest-api/shop/memory/tests/test_repos.pys
python -m transpiler run examples/rest-api/shop/memory/tests/test_router.pys
python -m transpiler run examples/rest-api/shop/memory/tests/test_http_e2e.pys
```

## Curl cookbook (expected shapes)

### Health

```bash
curl -s http://127.0.0.1:8090/health
```

Expected:

```json
{"ok": true}
```

### List products

```bash
curl -s http://127.0.0.1:8090/api/products
```

Expected (ids may vary after mutations; seed starts with three):

```json
[
  {"productId": 1, "sku": "BG-CATAN", "name": "Catan", "unitPrice": 44.95, "active": true, "createdAt": "..."},
  {"productId": 2, "sku": "BG-TICKET", "name": "Ticket to Ride", "unitPrice": 49.99, "active": true, "createdAt": "..."},
  {"productId": 3, "sku": "BG-AZUL", "name": "Azul", "unitPrice": 39.95, "active": true, "createdAt": "..."}
]
```

### Create product

```bash
curl -s -X POST http://127.0.0.1:8090/api/products ^
  -H "Content-Type: application/json" ^
  -d "{\"sku\":\"BG-NEW\",\"name\":\"New Game\",\"unitPrice\":12.5}"
```

Expected: `201` with body including `"sku": "BG-NEW"` and `Location: /api/products/{id}`.

### Get / update / delete product

```bash
curl -s http://127.0.0.1:8090/api/products/1
curl -s -X PUT http://127.0.0.1:8090/api/products/1 -H "Content-Type: application/json" -d "{\"unitPrice\":40.0,\"active\":false}"
curl -s -o NUL -w "%%{http_code}" -X DELETE http://127.0.0.1:8090/api/products/1
```

Delete expected status: `204`.

### Orders + lines

```bash
curl -s -X POST http://127.0.0.1:8090/api/orders -H "Content-Type: application/json" -d "{\"status\":\"placed\",\"customerRef\":\"ada@example.com\"}"
curl -s -X POST http://127.0.0.1:8090/api/orders/1/lines -H "Content-Type: application/json" -d "{\"productId\":2,\"quantity\":2}"
curl -s http://127.0.0.1:8090/api/orders/1/lines
```

Line create snapshots `sku` / `unitPrice` from the product; `lineTotal` = price × qty.

### Errors

| Case | Status | Body |
|------|--------|------|
| Unknown id | 404 | `{"error":"... not found"}` |
| Bad JSON / missing fields | 400 | `{"error":"..."}` |
| Wrong method | 405 | `{"error":"method not allowed"}` |

## Layout

| Path | Role |
|------|------|
| `src/main.pys` | Acceptor + 4 workers |
| `src/router.pys` | Method/path dispatch |
| `src/api_*.pys` | CRUD handlers |
| `src/repositories.pys` | `InMemory*` + `ShopStore` |
| `src/models.pys` | `Product` / `Order` / `OrderLine` |
| `src/http11.pys` | JSON HTTP/1.1 |
