# Pipeline migration checklist

Track retiring the legacy `Parser` and related product work.
Check items off as they land; keep the suite green after each step.

## A. Finish retiring legacy `Parser` (core completeness)

- [x] **A1.** Move remaining semantics into `sem.py`
  - [x] A1a. const / fix immutability
  - [x] A1b. undeclared variables
  - [x] A1c. loop-counter immutability
  - [x] A1d. typed interpolation checks
  - [x] A1e. member / private / protected / sealed access
  - [x] A1f. interface implementation + arity
  - [x] A1g. shared capture rules (Policy B)
  - [x] A1h. array bounds / element-type checks
  - [x] A1i. class `function` / `method` / missing access-modifier errors
- [x] **A2.** Stop double work in emit (no full legacy `Parser.parse()` for validation)
- [x] **A3.** Own without calling into `Parser`
  - [x] A3a. `.pys` import resolution / visibility (via `imports` module facade)
  - [x] A3b. overload rewriting (`emit/overloads.py`)
  - [x] A3c. concurrency preamble as shared module (`concurrency.py`)
- [x] **A4.** Remove quarantine silent fallback (AST emit no longer catches and re-runs legacy)
- [x] **A5.** Harden parse/AST (kwargs, generics/collections, generic classes/ctors, `main.pys` on AST+sem)
- [x] **A6.** Tests: sem/errors without legacy; optional CI guard against `Parser` in emit
- [x] **A7.** Production compile path is AST-only
  - [x] A7a. `imports.ImportResolver` loads sibling `.pys` metadata via `parse_program` (no `Parser`)
  - [x] A7b. Remove `Module.use_legacy` / `_legacy_emit`; parse errors raise `TranspileError`
  - [x] A7c. `transpile_with_modules` discovers deps via `discover_imported_modules`

## B. Product / distribution

- [ ] **B1.** Marketplace publish (`VSCE_PAT` / publisher setup)
- [ ] **B2.** Repo cleanup (old tracked `.vsix`, scratch `tools/` scripts)
- [ ] **B3.** Push local commits to `origin/main` when ready

## C. Later backends / IDE

- [ ] **C1.** Java / C# emitters under `emit/`
- [ ] **C2.** PYS step-through debug (DAP)
- [x] **C3.** Extension diagnostics from the new pipeline (`ide.analyze_file` uses compile_pys + AST + ImportResolver)
- [x] **C4.** Delete legacy `Parser` class from `transpiler.py` (public API is transpile/run only). `language_spec.py` remains for emit helpers + `translate_line` tests — not on the compile path.

---

**Done when:** A1–A7 + C3–C4 complete; no `Parser` in the package.
Architecture diagrams: [`ARCHITECTURE.md`](ARCHITECTURE.md).

**Already done (context):** lex/parse/sem/emit for goldens and main examples; AST import resolver;
acceptance tests for `examples/main.pys`, concurrency, and pokemontcg; IDE analysis on AST.
