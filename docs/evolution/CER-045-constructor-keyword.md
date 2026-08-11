# CER-045: Explicit `constructor` keyword

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-08 |
| Extends | [ADR-027](../adr/ADR-027-constructor-keyword.md) |
| Scope | `lex.py`, `parse.py`, `emit/python.py`, examples, book, IDE |

## Context

Class-name constructors blocked JS transfer and hid the “constructor” concept.

## Entries

### 1. `constructor` replaces type-name form

- **Pre-behavior:** `public constructor(string name) { ... }` with name matching class.
- **Why it hurt:** Positional convention; not JS’s reserved word.
- **Post-behavior:** `public constructor(...)`; class-name form FatalParseError
  with tip. Entity uses the same keyword. Emit still `def __init__`.
- **Evidence:** `tests/test_constructor_keyword.py`.

### 2. `this(...)` ctor chaining emit

- **Pre-behavior:** Parse rewrote `this` → `self`; emit called `self(...)`.
- **Why it hurt:** Runtime TypeError; overload chains broken.
- **Post-behavior:** Statement-level `self(...)` in a constructor emits
  `self.__init__(...)` and counts as chaining (no extra implicit `super()`).
- **Evidence:** chaining test in `test_constructor_keyword.py`.

### 3. Explicit `this.` for fields

- **Pre-behavior:** Bare field ids often worked by convention / emit rewrite.
- **Post-behavior:** Unresolved bare id matching an instance field → Error with
  tip `this.name` (methods, constructors, trait methods).
- **Evidence:** `tests/test_this_field_fix_ctor.py`.

### 4. `fix` definite assignment in constructors

- **Pre-behavior:** Uninitialized `fix` fields were not path-checked across
  `this(...)` / `super(...)`.
- **Post-behavior:** Every constructor path must assign each uninitialized
  `fix` field (directly or via `this(...)` delegation).
- **Evidence:** `tests/test_this_field_fix_ctor.py`.

### 5. Omitted constructor access defaults to `module`

- **Pre-behavior:** Bare `constructor(...)` failed (“access modifier required”).
- **Why it hurt:** Top-level types already default to module scope without a
  prefix; constructors felt inconsistent.
- **Post-behavior:** Omitted `member_access` on `constructor` ⇒ `module`
  (class and entity). `public constructor(...)` remains the teaching default
  for exported APIs.
- **Superseded for fields/methods:** [CER-058](CER-058-member-access-module-default.md)
  extends the same omit⇒`module` rule to **all** class/entity members.
- **Evidence:** `tests/test_constructor_keyword.py`.

## Trade-offs

- One-shot break + migrate; no dual-form window.
