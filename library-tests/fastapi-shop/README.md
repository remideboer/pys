# FastAPI shop — library field research (not a teaching example)

PYS + [FastAPI](https://fastapi.tiangolo.com/) under `library-tests/` to prove
**library decorator application** ([ADR-026](../../docs/adr/ADR-026-library-decorators.md))
against a mature stack: JWT login, bcrypt passwords, MySQL `shop` schema
(accounts / NL addresses / fake payment instruments).

Teaching hand-rolled HTTP shops stay under `examples/rest-api/shop/` (ports
8090–8092). This app listens on **8093**.

## Prerequisites

1. Schema + seed (shared with console/REST shops):

```text
mysql -u pys -p123456789 < examples/database/shop.sql
mysql -u pys -p123456789 shop < examples/database/seed_boardgames.sql
```

2. Lock deps (once per machine/platform):

```text
python -m transpiler deps lock library-tests/fastapi-shop/pys.deps
```

## Run

```text
set PYS_WORKSPACE_ROOT=library-tests\fastapi-shop
python -m transpiler run library-tests/fastapi-shop/src/main.pys
```

- OpenAPI UI: http://127.0.0.1:8093/docs
- Health: `GET /health`
- Login: `POST /api/login` with seeded users (password **`Welcome1!`** for all):
  `admin`, `clerk`, `amira`, `mehmet`, `priya`, …

## Auth model

| Method | Auth |
|--------|------|
| GET | open |
| POST /api/login | open |
| other POST/PUT/DELETE | `Authorization: Bearer <token>` |

JWT is stdlib HS256 (same teaching approach as `examples/rest-api/shop/jwt`).
PyJWT is deferred until PYS has `try`/`catch` for invalid-token errors.
Passwords use **bcrypt** against `account.password_hash`.

### Field-research notes (PYS ↔ FastAPI)

- Route decorators (`@appRouter.get` / `.post` / …) are ADR-026 library application.
- Path templates use `chr(123)`/`chr(125)` via [`paths.pys`](src/paths.pys) — brace chars inside PYS strings become f-string interpolations.
- JSON bodies are read with `Request` + `anyio.from_thread.run(request.json)` ([`json_body.pys`](src/json_body.pys)) because PYS has no default parameter values for `Body()`.
- Emit keeps PascalCase param annotations (`Request`) so FastAPI can inject them.
- Module wiring uses a dict holder ([`state.pys`](src/state.pys)) — plain module reassignment inside `bind` would be Python locals without `global`.

## Curl sketch

```text
curl -s http://127.0.0.1:8093/health
curl -s -X POST http://127.0.0.1:8093/api/login -H "Content-Type: application/json" -d "{\"username\":\"amira\",\"password\":\"Welcome1!\"}"
curl -s http://127.0.0.1:8093/api/products
curl -s http://127.0.0.1:8093/api/accounts/3/addresses
curl -s -X POST http://127.0.0.1:8093/api/products -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d "{\"sku\":\"X\",\"name\":\"Y\",\"unitPrice\":1.5}"
```

## Layout

| File | Role |
|------|------|
| `src/main.pys` | FastAPI app + uvicorn |
| `src/routes_*.pys` | `@router.get` / `.post` / … |
| `src/security.pys` | bcrypt + JWT |
| `src/db.pys` | MySQL session |
| `pys.deps` | fastapi, uvicorn, mysql-connector, bcrypt, httpx |
