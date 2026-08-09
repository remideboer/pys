# Phase 3 — Express JWT + MySQL shop (JavaScript target)

Port **8192**. Same mysql2 persistence as phase 2, plus:
- `POST /api/login` → `{ accessToken, tokenType, username }`
- Bearer required on **POST/PUT/DELETE** (GET open)

Teaching users: `admin`/`admin123`, `clerk`/`clerk123`.

HS256 via Node `crypto` (not `jsonwebtoken`), matching the Python stdlib JWT lesson.

## Run

```bash
python -m transpiler run examples/by-target/javascript/rest-api/express/jwt/src/main.pys
```

## Tests

```bash
set PYS_WORKSPACE_ROOT=examples\by-target\javascript\rest-api\express\jwt
python -m transpiler run examples/by-target/javascript/rest-api/express/jwt/tests/test_jwt_crypto.pys --target javascript
```

## Curl

```bash
curl -s -X POST http://127.0.0.1:8192/api/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"admin123\"}"
curl -s -X POST http://127.0.0.1:8192/api/products -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d "{\"sku\":\"BG-X\",\"name\":\"X\",\"unitPrice\":1}"
```
