# Future development log

Explicitly deferred work. Prefer shipping maturity with each feature; entries
here are only items the project **chose** to postpone (see feature-maturity DoD).

When starting an entry: promote it to a plan / ADR+CER as usual, then remove or
mark it done here.

| ID | Area | Status | Summary |
| --- | --- | --- | --- |
| [F-001](#f-001-bitwise-rotate) | Language / bitwise | Deferred | Rotate `<<<` / `>>>` and word forms |
| [F-002](#f-002-enum-match-exhaustiveness) | Language / enums | Superseded | Was `match`; delivered as `switch` (ADR-008) |
| [F-003](#f-003-enum-value-aliases) | Language / enums | Deferred | Duplicate enum values via real syntax (not `@`) |
| [F-004](#f-004-pys-dap-stepping) | IDE / debug | **Done** | PYS source-level DAP stepping (ADR-014) |
| [F-005](#f-005-full-fowler-refactor-catalog) | IDE / refactor | Deferred | Remaining Fowler catalog beyond educational core (ADR-016) |
| [F-006](#f-006-source-roots-and-same-package-tests) | Language / packages | **Done** | `pys.toml` source roots; same package across `src`/`tests` |
| [F-007](#f-007-webserver-full-spec-remainder) | Examples / webserver | **Done** | FR8 re-checkout, MockDownstream faults, 429 inbound shed, write timeout, manual 1k soak |
| [F-008](#f-008-rest-shop-mysql) | Examples / REST shop | **Done** | MySQL-backed shop REST (`examples/rest-api/shop/mysql`) |
| [F-009](#f-009-rest-shop-jwt) | Examples / REST shop | **Done** | JWT auth layer (`examples/rest-api/shop/jwt`) |
| [F-010](#f-010-javascript-dap-and-os-thread-tasks) | Emit / IDE | **Partial** | Node DAP **Done**; OS-thread JS tasks still deferred |
| [F-011](#f-011-host-runtime-ensure) | IDE | **Done** | Create Project target + PATH probe / install prompt |
| [F-012](#f-012-express-rest-shop) | Examples / REST shop | **Done** | Express JS shop under `by-target/javascript/rest-api/express` |
| [F-013](#f-013-generate-menu-bodies) | IDE / generate | Deferred | Constructor / toString / override / getters / test (menu placeholders) |

---

## F-001: Bitwise rotate

| | |
| --- | --- |
| Status | Deferred |
| Source | [`requirements/binairy_hexadecimal_literals.pys`](../requirements/binairy_hexadecimal_literals.pys); [ADR-007](adr/ADR-007-int-literals-and-widths.md) |
| Related | Lex already accepts `<<<` / `>>>` and parse rejects them with a tip |

### Intent

Hardware-style rotate for int-like values:

- `<<<` / `>>>` (and/or `rotate left` / `rotate right`)
- Later still: rotate through carry variants (requirements “for later”)

### Notes

- Must define width for rotate (use operand width alias vs unbounded `int`).
- Keep `<<` / `>>` as arithmetic/logical shifts; do not overload them.
- No `@` annotations — real operators / keywords only.

---

## F-002: Enum match exhaustiveness

| | |
| --- | --- |
| Status | **Superseded** by [ADR-008](adr/ADR-008-switch-stmt-and-expr.md) / [CER-007](evolution/CER-007-switch-stmt-and-expr.md) |
| Source | [`requirements/enums.pys`](../requirements/enums.pys); [ADR-006](adr/ADR-006-enums-as-nominal-sets.md) |

Originally: `match` / `case` with exhaustiveness over enum members.

**Delivered as** PYS `switch` (statement + expression) with enum bare labels,
`continue` fall-through, and expression exhaustiveness — not a separate
`match` keyword.

---

## F-003: Enum value aliases

| | |
| --- | --- |
| Status | Deferred |
| Source | [ADR-006](adr/ADR-006-enums-as-nominal-sets.md); project-memory (no `@`) |

Allow two members to share a value only via a **real language construct**
(never `@alias`).

---

## F-004: PYS source-level DAP stepping

| | |
| --- | --- |
| Status | **Done** — [ADR-014](adr/ADR-014-pys-dap-stepping.md) / [CER-014](evolution/CER-014-pys-dap-stepping.md) |
| Source | [ARCHITECTURE.md](ARCHITECTURE.md); [pipeline-migration.md](pipeline-migration.md) C2 |

Debug adapter stepping mapped to `.pys` lines (not only generated Python).
Delivered: emit line maps, `prepare_debug`, debugpy launch of generated program,
`DebugAdapterTracker` remap, extension 0.0.47.

---

## F-005: Full Fowler refactor catalog

| | |
| --- | --- |
| Status | Deferred |
| Source | [ADR-016](adr/ADR-016-ide-refactoring.md); https://refactoring.com/catalog/ |

Educational core (Rename, Extract Variable/Function, Inline Variable/Function,
Safe Delete, Introduce Parameter) shipped under ADR-016. Deferred examples:
Change Signature, Move Function/Field, Extract Class, Replace Conditional with
Polymorphism, and other catalog entries not in the core DoD.

---

## F-006: Source roots and same-package tests

| | |
| --- | --- |
| Status | **Done** (core + DoD example/QF + webserver `src`/`tests` layout); product remainder → F-007 |
| Source | [`requirements/package_resolution_testing_philosophy.md`](../requirements/package_resolution_testing_philosophy.md); [ADR-017](adr/ADR-017-source-roots-same-package-tests.md); surfaced by `examples/webserver/` |

### Intent

Project-manifest source roots so production and tests can share a package
without living in the same folder or widening `package` → `public`:

```text
pys.toml
src/billing/Invoice.pys       # package billing
tests/billing/InvoiceTest.pys # same package (mirrored relative path)
```

```toml
[source_roots]
main = "src"
test = "tests"
```

**Resolution:** package = path relative to the containing declared source root.
Same package across roots iff those relative paths are identical.

**Also:** no `private` bypass for tests; no C# `namespace` / `partial class`
(see requirements §1–2). Wrong-folder tests get an educational diagnostic (§4).

### Follow-up refactor

When F-006 / ADR-017 is implemented, **refactor `examples/webserver/`** (and
any other flat same-folder test examples) into main/test roots with mirrored
paths. Do not widen access modifiers as a substitute.

**Done:** `examples/webserver/` now uses `src/` + `tests/` + `pys.toml`.
Remaining webserver product work is [F-007](#f-007-webserver-full-spec-remainder).

---

## F-007: Webserver full-spec remainder

| | |
| --- | --- |
| Status | **Done** |
| Source | `examples/webserver/`; [DEFERRED.md](../examples/webserver/DEFERRED.md); [CER-034](evolution/CER-034-webserver-full-spec.md) |
| Blocked by | ~~[F-006](#f-006-source-roots-and-same-package-tests)~~ (layout done) |

Teaching increments 1–6 were already shipped. F-007 closed the remaining
full-spec gaps:

- **FR8** — `RetryPolicy.executeOnPool`: each retry acquires a new downstream
  pool checkout; backoff holds no slot (`tests/test_integration.pys` E6,
  `tests/test_faults.pys`).
- **Toxiproxy equivalent** — `MockDownstream` fail / reset / fatal / latency
  knobs for D/E-shaped scenarios (real Toxiproxy still optional).
- **FR4** — inbound `ConnQueue` capacity → **429** `inbound_full`; downstream
  pool / circuit → **503** (distinct metrics).
- **Write-timeout** — `writeTimeoutMs` applied before HTTP/1.1 and HTTP/2 writes.
- **FR1 / soak** — manual ≥1k VU gate documented in
  [`examples/webserver/load/SOAK.md`](../examples/webserver/load/SOAK.md)
  (not CI).

Layout uses `src/` + `tests/` + `pys.toml` (ADR-017).

---

## F-008: REST shop MySQL phase

| | |
| --- | --- |
| Status | **Done** — [CER-036](evolution/CER-036-rest-shop-mysql.md) |
| Source | [`examples/rest-api/shop/mysql/`](../examples/rest-api/shop/mysql/) |
| Blocked by | ~~Phase 1 memory~~ |

Same `/api/*` surface as memory; `ShopStore` uses MySQL mappers. Port 8091.
CI: transpile gate only (live DB is local/manual).

---

## F-009: REST shop JWT phase

| | |
| --- | --- |
| Status | **Done** — [CER-037](evolution/CER-037-rest-shop-jwt.md) |
| Source | [`examples/rest-api/shop/jwt/`](../examples/rest-api/shop/jwt/) |
| Blocked by | ~~[F-008](#f-008-rest-shop-mysql)~~ |

`POST /api/login` + Bearer gate on writes; MySQL persistence unchanged. Port 8092.

---

## F-010: JavaScript DAP and OS-thread tasks

| | |
| --- | --- |
| Status | **Partial** (item 1 Done; item 2 Deferred) |
| Source | [ADR-030](adr/ADR-030-javascript-emit-target.md); [CER-050](evolution/CER-050-javascript-emit-target.md) §9–10; [ADR-014](adr/ADR-014-pys-dap-stepping.md) |

### Intent

1. **Node DAP** — map breakpoints / stack / variables from emitted `.mjs` +
   `.pysmap.json` back to `.pys` (parity with ADR-014 for Python). **Done**
   (prepare_debug `--target javascript`, target-neutral `debug-map.js`,
   `pwa-node` via `debug-launch.js`).
2. **OS-thread (or worker) tasks** — real interleaving for shared-race teaching
   demos; keep cooperative await as the default or document the switch.
   **Still deferred.**

Until item 2: JS `tasks` use the cooperative `_PysTaskGroup` trampoline.

---

## F-011: Host runtime ensure

| | |
| --- | --- |
| Status | **Done** |
| Source | [CER-051](evolution/CER-051-runtime-ensure.md); [ADR-001](adr/ADR-001-trust-boundaries.md) |

Create Project picks emit target; PATH probe + curated install prompt for
Python (always) and Node (JavaScript). Visible `winget` / `brew` / docs only
in trusted workspaces. Activation also probes Python (and Node when the
workspace target is JavaScript).

---

## F-012: Express REST shop (JavaScript)

| | |
| --- | --- |
| Status | **Done** |
| Source | [`examples/by-target/javascript/rest-api/express/`](../examples/by-target/javascript/rest-api/express/) |
| Related | [CER-050](evolution/CER-050-javascript-emit-target.md) §13; [ADR-030](adr/ADR-030-javascript-emit-target.md) |

Node Express twin of the Python socket shop: memory (8190) → mysql2 (8191) →
JWT writes (8192). Emit maps `express` (default import), `crypto`/`buffer`,
and `json`/`time` shims. CI: memory suites + mysql transpile + jwt crypto.

---

## F-013: Generate menu bodies

| | |
| --- | --- |
| Status | Deferred |
| Source | [CER-018](evolution/CER-018-ide-refactoring.md) context-menu order |

Editor **Generate** submenu already lists Constructor, toString, Override
Methods, Getters/Setters, and Test (disabled placeholders) plus Create Class
(enabled). Implement real insert/edit plans for the disabled entries; enable
when each is ready.

