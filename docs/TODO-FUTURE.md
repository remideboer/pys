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