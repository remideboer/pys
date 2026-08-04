# CER-025: Result, propagation, panic, and entrypoint resolution

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-04 |
| Commits | (result / propagation / entrypoint increment) |
| Scope | lexer; AST; parser; imports; semantics; Python emit; pipeline; CLI; IDE; refactor; extension; docs |
| ADRs | [ADR-021](../adr/ADR-021-result-propagate-panic.md); [ADR-001](../adr/ADR-001-trust-boundaries.md); [ADR-014](../adr/ADR-014-pys-dap-stepping.md) |

## Context

PYS could represent a closed status enum, but had no typed success/error
payload, propagation operator, or terminal handling contract. Project runs also
treated the selected path as the entrypoint even when a project needed one
stable main file.

## Entry 1 — Dedicated result syntax and nodes

### Pre-behavior

Generic-looking type names parsed without result arity rules. `ok`, `err`, and
`propagate` had no language meaning, and switch labels could not bind a
payload.

### Why it hurt

Recoverable APIs could not state both their success and error contracts.
Encoding the feature as ordinary calls would lose contextual typing and
binding-aware tooling.

### Post-behavior

- `result<T,E>` requires one success and one concrete error type; only `T` may
  be `void`.
- Dedicated `ResultCtor`, `PropagateExpr`, and `ResultPattern` AST nodes retain
  source spans and intent.
- `ok(value)`, `ok()`, `err(error)`, postfix `propagate`, and result switch
  patterns parse in the existing single-lex RD/PEG-capable pipeline.
- `ok` and `err` cannot be redeclared.

### Evidence

`tests/test_result_propagate.py` parser, arity, payload, keyword, and reference
tests.

## Entry 2 — Contextual semantics and exhaustive matching

### Pre-behavior

The semantic analyzer did not retain imported function signatures or distinguish
a recoverable outcome from its success payload.

### Why it hurt

Constructor payloads and propagation could not be checked across modules.
Implicitly treating a result as `T` would discard a failure path.

### Post-behavior

- Local/imported function and class-method parameter/return signatures retain
  result types, including inherited and `this` method calls.
- Constructors are checked against assignment, argument, lambda, and return
  context. A result never implicitly converts to its success type.
- `propagate` requires a result boundary with exactly matching `E`, and is
  rejected in plain functions, non-entry top-level code, and across tasks.
- Result switches require `ok` plus `err` or `default`; bindings are arm-local,
  typed, and visible to rename/find-usages. Expression arms agree on type.

### Evidence

`tests/test_result_propagate.py` semantic, import, switch, lambda, runtime, and
refactor tests.

## Entry 3 — Private lowering and deterministic panic

### Pre-behavior

Generated programs had no tagged result value, propagation boundary, or
controlled terminal error chain.

### Why it hurt

A propagation operator in arbitrary expression position needs structured
non-local control flow without exposing Python exceptions as PYS behavior.

### Post-behavior

- Python emit supplies private `_PysResult` values and a private
  `_PysPropagateSignal`.
- Result-returning functions, methods, and typed lambdas catch only the private
  signal and return its unchanged error payload.
- Propagation records deterministic PYS file/line/function sites.
- Each propagation creates a new private error-chain value, so handling one
  traversal cannot pollute a later traversal of the same original error.
- Only an eligible entrypoint with top-level propagation receives a terminal
  wrapper. Panic writes the error and propagation chain to stderr, then exits
  non-zero.

### Evidence

`tests/test_result_propagate.py`; `tests/test_entrypoint_panic.py`.

## Entry 4 — One manifest entrypoint across CLI and IDE

### Pre-behavior

Run and Debug were selected-file operations. `pys.mainFile` was an
extension-local setting rather than a project contract.

### Why it hurt

Different launch surfaces could choose different files, and imported code could
not be classified reliably as entrypoint or library code.

### Post-behavior

- `project_manifest.resolve_entrypoint` validates contained `[project].main`
  paths and detects selected-file conflicts; the Python 3.10 fallback rejects
  non-string or duplicate main assignments instead of silently ignoring them.
- Transpile, Run, Debug preparation, and passive analysis carry explicit
  entrypoint identity through the pipeline.
- The extension reads and writes `[project].main`, exposes Set as entrypoint,
  watches manifest changes, and retains `pys.mainFile` only as a deprecated
  no-manifest fallback.
- Syntax highlighting, hover, completion/snippets, diagnostics, and code
  actions cover the result surface. Extension version is `0.0.69`.

### Evidence

`tests/test_entrypoint_panic.py`; `pys-language/test/project-main.test.js`;
the extension Node suite.

## Trade-offs / deferred

- No general exception syntax and no source-level panic construct.
- No implicit error conversion or task-crossing propagation.
- Result runtime values are private implementation details, not a reflection
  API.
