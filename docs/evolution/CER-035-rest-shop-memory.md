# CER-035: In-memory REST shop example (phase 1)

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-07 |
| Source | [examples/rest-api/shop/](../../examples/rest-api/shop/); plan REST shop memory |
| Scope | `examples/rest-api/shop/memory/**`; F-008 / F-009 placeholders |

## Context

Students need a REST teaching path that builds on the concurrent webserver and
the shop domain without requiring MySQL or JWT on day one. Cross-example
imports are awkward (each example is its own workspace root), so the REST shop
is a self-contained layered tree.

## Entries

### 1. Progression folders

- **Pre-behavior:** Shop lived only under `examples/database` (console/GUI +
  MySQL); webserver had stub `POST /orders` unrelated to products.
- **Why it hurt:** No HTTP JSON CRUD story; jumping straight to MySQL+auth
  buries transport and routing.
- **Post-behavior:** `examples/rest-api/shop/{memory,mysql,jwt}` with phase 1
  runnable in `memory/`; `mysql/` and `jwt/` README stubs gated by F-008/F-009.
- **Evidence:** parent README roadmap; deferred stubs.

### 2. Slim HTTP + JSON CRUD (in-memory)

- **Pre-behavior:** Full webserver resilience stack; plain-text responses.
- **Why it hurt:** Too much noise for a first REST lesson.
- **Post-behavior:** Copied slim HTTP/1.1 (`http11`, `conn_queue`,
  `conn_handler`, 4 workers); `application/json`; path dispatch via
  `split("/")`; `InMemory*` repos with same entity shapes as the console shop;
  seed catalog; port **8090**.
- **Evidence:** `tests/test_repos.pys`, `test_router.pys`, `test_http_e2e.pys`;
  `tests/test_rest_shop_memory.py` with `PYS_WORKSPACE_ROOT` = memory dir.

### 3. Copy entities, do not cross-import

- **Pre-behavior:** Temptation to import from `examples/database` /
  `examples/webserver`.
- **Why it hurt:** Breaks workspace-root / lock isolation and student
  copy-paste learning.
- **Post-behavior:** Local `models.pys` + abstract repo ports; phase 2 will
  swap MySQL mappers behind the same ports.

## Trade-offs

- Domain/SQL duplication until mysql phase (intentional for clarity).
- No TLS/HTTP2/circuit breaker in memory phase.
- Auth headers ignored until F-009.
