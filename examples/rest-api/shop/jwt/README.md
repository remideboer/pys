# Phase 3 — JWT authentication (deferred)

**Status:** placeholder until [F-009](../../../docs/TODO-FUTURE.md#f-009-rest-shop-jwt).

**Blocked by:** phase 2 ([`../mysql/`](../mysql/)) DoD.

## Intent

Add `Authorization: Bearer <jwt>` to mutating (and optionally read) routes.
Login/token issuance endpoints; keep CRUD handlers mostly unchanged — auth as
a thin gate in front of the router.

Students should be able to diff `mysql/` vs `jwt/` and see only the auth layer.
