# CER-037: JWT shop REST (phase 3 / F-009)

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-07 |
| Source | [F-009](../TODO-FUTURE.md#f-009-rest-shop-jwt); `examples/rest-api/shop/jwt/` |
| Scope | HS256 JWT login + write gate on MySQL shop API |

## Context

Phase 2 exposed open MySQL CRUD. Phase 3 adds bearer auth without rewriting
handlers.

## Entries

### 1. Login + write write gate

- **Pre-behavior:** `jwt/` README stub only.
- **Post-behavior:** `POST /api/login`; mutating methods require
  `Authorization: Bearer`; GETs open; stdlib HS256 (`jwt_service.pys`);
  port 8092; crypto unit tests without MySQL; main transpile CI gate.
- **Evidence:** `tests/test_jwt_crypto.pys`, `tests/test_rest_shop_jwt.py`.

## Trade-offs

- Teaching users hardcoded (not a user table).
- Reads unauthenticated for demo simplicity.
