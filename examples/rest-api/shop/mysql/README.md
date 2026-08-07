# Phase 2 — MySQL-backed shop REST (deferred)

**Status:** placeholder until [F-008](../../../docs/TODO-FUTURE.md#f-008-rest-shop-mysql).

**Blocked by:** phase 1 ([`../memory/`](../memory/)) DoD.

## Intent

Keep the same `/api/products`, `/api/orders`, and `/api/orders/.../lines`
surface as memory, but wire `ShopDatabase` + mappers + repositories from the
console shop (`examples/database`) instead of `InMemory*Repository`.

Students should be able to diff `memory/` vs `mysql/` and see only the
persistence layer change.
