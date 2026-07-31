# Pipeline migration checklist

Track retiring the legacy `Parser` and related product work.
Check items off as they land; keep the suite green after each step.

## A. Finish retiring legacy `Parser` (core completeness)

- [ ] **A1.** Move remaining semantics into `sem.py`
  - [x] A1a. const / fix immutability
  - [x] A1b. undeclared variables
  - [x] A1c. loop-counter immutability
  - [ ] A1d. typed interpolation checks
  - [ ] A1e. member / private / protected / sealed access
  - [ ] A1f. interface implementation + arity
  - [ ] A1g. shared capture rules (Policy B)
  - [ ] A1h. array bounds / element-type checks
  - [ ] A1i. class `function` / `method` / missing access-modifier errors
- [ ] **A2.** Stop double work in emit (no full legacy `Parser.parse()` for validation)
- [ ] **A3.** Own without calling into `Parser`
  - [ ] A3a. `.pys` import resolution / visibility
  - [ ] A3b. overload rewriting
  - [ ] A3c. concurrency preamble as shared module (optional cleanup)
- [ ] **A4.** Remove quarantine (`use_legacy`, `_legacy_emit`, unused line-regex path)
- [ ] **A5.** Harden parse/AST (indent-mode, generics/collections, `main.pys` / tutorials on AST+sem)
- [ ] **A6.** Tests: sem/errors without legacy; optional CI guard against `Parser` in emit

## B. Product / distribution

- [ ] **B1.** Marketplace publish (`VSCE_PAT` / publisher setup)
- [ ] **B2.** Repo cleanup (old tracked `.vsix`, scratch `tools/` scripts)
- [ ] **B3.** Push local commits to `origin/main` when ready

## C. Later backends / IDE (deferred)

- [ ] **C1.** Java / C# emitters under `emit/`
- [ ] **C2.** PYS step-through debug (DAP)
- [ ] **C3.** Extension diagnostics from the new pipeline

---

**Done when:** A1–A4 complete and no production path needs `Parser.parse()`.

**Already done (context):** lex/parse/AST emit for goldens; concurrency AST; `.pys` import helper; prefer AST emit; first sem checks (`let`, simple types, return types, await cycles).
