# CER-044: FastAPI shop library-test (field research)

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-08 |
| Source | ADR-026 / CER-043; `library-tests/fastapi-shop/` |
| Scope | FastAPI+JWT+MySQL in `.pys`; emit PascalCase param annotations |

## Context

After library decorator application landed, we needed a non-teaching
**library field research** app to prove FastAPI-style `@router.get` works end
to end against the shared shop schema (accounts + NL address/payment seed).

## Entries

### 1. `library-tests/fastapi-shop` as PYS + FastAPI

- **Pre-behavior:** No FastAPI sample; absolute “no `@` in source” blocked it.
- **Why it hurt:** Could not validate third-party decorator APIs from `.pys`.
- **Post-behavior:** Port **8093** app under `library-tests/` (not `examples/`);
  routes use `@appRouter.*`; JWT (stdlib HS256) + bcrypt vs `account`; MySQL
  shared schema; OpenAPI `/docs`. Workarounds documented in README: path
  braces via `chr`, JSON body via `Request`+`anyio`, dict state holder.
- **Evidence:** `tests/test_fastapi_shop.py` (transpile always; live smoke when
  MySQL reachable); local `smoke_live.pys`.

### 2. Emit PascalCase param annotations for library DI

- **Pre-behavior:** Function params emitted bare (`def login(request):`), so
  FastAPI treated `Request` as a query field.
- **Why it hurt:** Sync injection failed without Python annotations.
- **Post-behavior:** Emitter keeps annotations when the PYS type base is a
  PascalCase identifier (`request: Request`). Builtins (`int`, `string`, …)
  stay unannotated.
- **Evidence:** `tests/test_decorators.py::test_emit_keeps_nominal_param_annotation`.

### 3. Shared shop accounts schema/seed

- **Pre-behavior:** `shop` had product/order only; teaching JWT used in-memory
  admin/clerk.
- **Post-behavior:** `account` / `account_address` / `account_payment_method` +
  nullable `order.account_id`; multicultural NL seed (password `Welcome1!`);
  SQL copies synced under rest-api mysql/jwt. Teaching jwt auth unchanged.

### 4. Strict typing (no lazy `object` rows)

- **Pre-behavior:** Routes mapped SQL rows into bare `dict` via
  `productRow(object row, object db)`; `ShopDatabase.cursor()` returned
  `object`; state accessors returned `object`.
- **Why it hurt:** Field research drifted from the teaching MySQL shop’s OO
  contract (`MySQLCursor`, `entity Product`, mappers) and hid shape errors.
- **Post-behavior:** `MySQLConnection` / `MySQLCursor`; domain entities in
  `models.pys`; `mappers.pys` + `views.pys`; typed `state` / `Security` /
  routers. Route handlers may still return `object` where FastAPI needs
  `dict | JSONResponse`. JWT payload remains `dict` (claims bag); `b64urlDecode`
  stays `object` (bytes).
- **Evidence:** `tests/test_fastapi_shop.py::test_fastapi_shop_main_transpiles`.

## Trade-offs

- Not a student example; teaching REST stays hand-rolled HTTP.
- PyJWT deferred until PYS has `try`/`catch`.
- No Marketplace release in this change set (tag only with approval).
