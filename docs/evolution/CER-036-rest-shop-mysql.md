# CER-036: MySQL-backed REST shop (phase 2 / F-008)

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-07 |
| Source | [F-008](../TODO-FUTURE.md#f-008-rest-shop-mysql); `examples/rest-api/shop/mysql/` |
| Scope | MySQL store wiring; same HTTP surface as memory |

## Context

Phase 1 taught JSON CRUD with in-memory repos. Phase 2 swaps persistence to
the console shop’s MySQL stack without changing route shapes.

## Entries

### 1. Same API, MySQL behind ShopStore

- **Pre-behavior:** `memory/` only; `mysql/` was a README stub.
- **Why it hurt:** No persistence continuity with `examples/database`.
- **Post-behavior:** `store.pys` wires `ShopDatabase` + Mysql*Mapper +
  Default*Repository; port 8091; copied `shop.sql` / seed; CI transpile-only
  (`tests/test_rest_shop_mysql.py`).
- **Evidence:** transpile gate; README setup + curl.

## Trade-offs

- Live MySQL not required in CI (manual demo).
- Line numbers = `len(existing)+1` (teaching; concurrent inserts may race).
