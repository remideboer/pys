# Phase 3 — JWT on MySQL shop REST

Same routes as [`../mysql/`](../mysql/), plus:

- `POST /api/login` → `{ accessToken, tokenType, username }`
- **POST / PUT / DELETE** require `Authorization: Bearer <token>`
- **GET** stays open (easier demos)

Teaching users: `admin` / `admin123`, `clerk` / `clerk123`.

## Run

```bash
python -m transpiler run examples/rest-api/shop/jwt/src/main.pys
```

Port **8092**.

```bash
curl -s -X POST http://127.0.0.1:8092/api/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"admin123\"}"
curl -s http://127.0.0.1:8092/api/products
curl -s -X POST http://127.0.0.1:8092/api/products -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d "{\"sku\":\"X\",\"name\":\"Y\",\"unitPrice\":1}"
```

Without a token, writes return `401` `{"error":"bearer token required"}`.

## Diff vs mysql

| File | Role |
|------|------|
| `jwt_service.pys` | HS256 JWT (stdlib hmac) |
| `auth.pys` | login + bearer check |
| `http11.pys` | parses `Authorization` |
| `router.pys` | write gate + `/api/login` |

## Tests

```bash
set PYS_WORKSPACE_ROOT=examples\rest-api\shop\jwt
python -m transpiler run examples/rest-api/shop/jwt/tests/test_jwt_crypto.pys
python -m pytest tests/test_rest_shop_jwt.py -q
```
