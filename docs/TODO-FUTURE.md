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
| [F-006](#f-006-source-roots-and-same-package-tests) | Language / packages | **Active** | `pys.toml` source roots; same package across `src`/`tests` |
| [F-007](#f-007-webserver-full-spec-remainder) | Examples / webserver | Deferred | FR8 re-checkout, Toxiproxy, 1k-scale soak — after F-006 refactor |

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
| Status | **Active** — core + teaching example + IDE QF landed; webserver refactor still pending |
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

---

## F-007: Webserver full-spec remainder

| | |
| --- | --- |
| Status | Deferred (halted) |
| Source | `examples/webserver/`; [DEFERRED.md](../examples/webserver/DEFERRED.md) |
| Blocked by | [F-006](#f-006-source-roots-and-same-package-tests) + layout refactor |

Teaching increments 1–6 are shipped. Remaining vs full concurrent-webserver
spec/testplan (not scheduled until after F-006):

- **FR8** — each retry acquires a new downstream pool checkout
- **Toxiproxy** (or equivalent) for D/E/H fault scenarios
- **FR4** — broader 429 capacity shedding if distinct from 503 queue-full
- **FR1 / soak** — real ≥1k concurrent / memory-FD soak (H1–H3)
- Write-timeout enforcement parity with read/idle/handler

Do not resume webserver feature work until the example uses source-root
packages; the example exists to validate PYS under production-like layout.
