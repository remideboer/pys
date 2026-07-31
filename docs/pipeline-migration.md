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
- [x] **A4.** Remove quarantine silent fallback (AST emit no longer catches and re-runs legacy; `use_legacy` remains only for sources the AST parser cannot represent yet)
- [x] **A5.** Harden parse/AST (kwargs, generics/collections, generic classes/ctors, `main.pys` on AST+sem)
- [x] **A6.** Tests: sem/errors without legacy; optional CI guard against `Parser` in emit

## B. Product / distribution

- [ ] **B1.** Marketplace publish (`VSCE_PAT` / publisher setup)
- [ ] **B2.** Repo cleanup (old tracked `.vsix`, scratch `tools/` scripts)
- [ ] **B3.** Push local commits to `origin/main` when ready

## C. Later backends / IDE (deferred)

- [ ] **C1.** Java / C# emitters under `emit/`
- [ ] **C2.** PYS step-through debug (DAP)
- [ ] **C3.** Extension diagnostics from the new pipeline

---

**Done when:** A1–A6 complete for the AST pipeline; remaining `use_legacy` only for
unparsed edge cases. Architecture diagrams: [`ARCHITECTURE.md`](ARCHITECTURE.md).

**Already done (context):** lex/parse/AST emit for goldens and main examples; concurrency AST;
`.pys` import helper; sem owns language checks; emit skips legacy validation on the AST path.
