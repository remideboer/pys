# Code evolution records (CERs)

These notes track **why the code changed**, not system architecture.

They sit between commit messages (too short) and ADRs (system-level decisions
in [`../adr/`](../adr/README.md)): each record describes a concrete pre-behavior,
the measurable or security cost of that behavior, and the post-behavior that
replaced it.

**Project memory (look back + write forward):** consult relevant CERs/ADRs before
changing related code, and **update or add** records in the same change set when
behavior or decisions move. Stale memory is a defect. Enforced by
`.cursor/rules/project-memory.mdc`.

## Format

| Field | Meaning |
| --- | --- |
| Status | `Accepted` once landed on the branch / merge commit |
| Date | When the change landed |
| Commits | Primary git SHA(s) |
| Scope | Files / symbols that moved |

Each record then uses:

1. **Context** — what the code was doing and for whom
2. **Entries** — one subsection per distinct code change:
   - Pre-behavior
   - Why it hurt
   - Post-behavior
   - Evidence (tests, benches, risk)
3. **Trade-offs** — what we deliberately did *not* change

## Index

| ID | Title | Theme |
| --- | --- | --- |
| [CER-001](CER-001-security-boundaries.md) | Harden security boundaries | Security |
| [CER-002](CER-002-compile-performance.md) | Cut redundant parse and filesystem work | Performance |
| [CER-003](CER-003-peg-frontend.md) | Lexer/deps wins + PEG-capable parse front-end | Performance |
| [CER-004](CER-004-structs.md) | Identity-free struct types | Language |
| [CER-005](CER-005-enums-and-warnings.md) | Enums + first-class compiler warnings | Language |
| [CER-006](CER-006-int-literals-bitwise-widths.md) | Binary/hex literals, bitwise, width aliases | Language |
| [CER-007](CER-007-switch-stmt-and-expr.md) | Switch statement and expression | Language |
| [CER-008](CER-008-traits.md) | Traits composition (`uses` / `requires`) | Language |
| [CER-009](CER-009-abstract-classes.md) | Abstract classes (`abstract` / `void`) | Language |
| [CER-010](CER-010-interface-method-access.md) | Interface methods: no access mods; nominal returns | Language |
| [CER-011](CER-011-data-and-entity.md) | `data` value objects and `entity` identity types | Language |
| [CER-012](CER-012-lambdas.md) | Lambdas with by-value capture | Language |
| [CER-013](CER-013-atomic.md) | Atomic qualifier (implies shared) | Language |
| [CER-014](CER-014-pys-dap-stepping.md) | PYS source-level DAP stepping | IDE |
| [CER-015](CER-015-block-scope.md) | Brace `{ }` block scope (binders / locals) | Language |
| [CER-016](CER-016-find-usages.md) | Find Usages for identifiers under cursor | IDE |
| [CER-017](CER-017-enforced-ordering.md) | Grammar-level member / import kind ordering | Language |
| [CER-018](CER-018-ide-refactoring.md) | Binding-aware refs + educational IDE refactoring | IDE |
| [CER-019](CER-019-multidim-arrays.md) | Multi-dimensional `T[][]…` + nested init / alloc | Language |
| [CER-020](CER-020-source-roots-package.md) | Source-root package identity (`pys.toml`) | Language |
| [CER-021](CER-021-collection-literals.md) | Collection literals (dict / set / tuple) | Language |
| [CER-022](CER-022-run-deps-context-menu.md) | Run Deps Lock from `pys.deps` context menu | IDE |
| [CER-023](CER-023-create-pys-project.md) | Create PYS Project from activity bar | IDE |
| [CER-024](CER-024-book-link-rewrite.md) | Published book link rewriting | Docs |
| [CER-025](CER-025-result-propagate-panic.md) | Result, propagation, panic, and entrypoint resolution | Language / IDE |
| [CER-026](CER-026-optional-terminators-grammar.md) | Optional `;`, C-for `;`, comma enums, multi-label switch | Language |
| [CER-027](CER-027-trait-requires-remapping.md) | Trait `requires` remapping via `uses Trait(a: b)` | Language |
| [CER-028](CER-028-nullable.md) | Explicit nullable values | Language / IDE |
| [CER-029](CER-029-gui-book-track.md) | Procedural Tkinter book track + temperature examples | Docs / Examples |
| [CER-030](CER-030-parse-float-int.md) | `parseFloat` / `parseInt` recoverable builtins | Language |
| [CER-031](CER-031-builtin-input.md) | Builtin `input` (no import) | Language |
| [CER-032](CER-032-to-bin-hex-oct.md) | `toBin` / `toHex` / `toOct` display builtins | Language |
| [CER-033](CER-033-string-plus-coerce.md) | String-involved `+` concatenates with coerce | Language |
| [CER-034](CER-034-webserver-full-spec.md) | Webserver full-spec remainder (F-007) | Examples |
| [CER-035](CER-035-rest-shop-memory.md) | In-memory REST shop (phase 1) | Examples |
| [CER-036](CER-036-rest-shop-mysql.md) | MySQL REST shop (phase 2 / F-008) | Examples |
| [CER-037](CER-037-rest-shop-jwt.md) | JWT shop REST (phase 3 / F-009) | Examples |
| [CER-038](CER-038-webserver-static.md) | Static-file HTTP example | Examples |
| [CER-039](CER-039-webserver-templates.md) | Template HTTP example | Examples |
| [CER-040](CER-040-webserver-templates-logic.md) | Template HTTP with if/for | Examples |
| [CER-041](CER-041-webserver-templates-query.md) | Template HTTP with query-string binding | Examples |
| [CER-042](CER-042-var-declaration-only.md) | Ban type-position `var`; formalize `object` | Language |
| [CER-043](CER-043-library-decorators.md) | Library decorator application | Language |
| [CER-044](CER-044-fastapi-shop-library-test.md) | FastAPI shop library-test (field research) | Library / examples |
| [CER-045](CER-045-constructor-keyword.md) | Explicit `constructor` keyword | Language |
| [CER-046](CER-046-open-override-closed.md) | `open` / `override` / `closed` extension points | Language |
| [CER-047](CER-047-static-members.md) | Class `static` members | Language |
| [CER-048](CER-048-named-call-args.md) | Named call args (no positional+named mix) | Language |
| [CER-049](CER-049-gof-design-patterns-examples.md) | Pattern teaching examples + book Session 10 (incl. Multitier) | Examples |

Related architecture overview: [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

Recurring CI reds (showcase transpile, `pys.lock` inheritance, extension
version pins, book/railroad drift): [`../ci-failure-patterns.md`](../ci-failure-patterns.md).
