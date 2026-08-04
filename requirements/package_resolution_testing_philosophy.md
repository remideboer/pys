## PYS Language Specification — Package Resolution and Testing Philosophy

### 1. Decision record

- Package identity for `top_visibility = "package"` is resolved via **multi-root, relative-path matching**: each declared source root (e.g. `src`, `tests`) is stripped from a file's path before package identity is computed, so identical relative structures under different roots resolve to the same package. No new keyword, no grammar change — this is a project-manifest concept, not a language construct.
- **No `private`-bypass mechanism is provided.** Testing must go through the class's `public`/`package` surface. A test that "needs" a `private` member is treated as a signal of an incomplete or poorly designed public API, not a gap the language should paper over.
- **No C#-style decoupled `namespace` keyword**, and no multi-file class definitions (C# `partial class`). Both are rejected for the same underlying reason: they let a class's identity or membership diverge from where it is physically written, which contradicts PYS's design philosophy applied consistently throughout this specification — member ordering, `requires`, `identity(...)`, the rejected `atomic`/`shared` redundancy — that structure in the source must be a truthful, singular record of what exists, not something requiring the reader to hold a mental cross-reference. A class split across files, or a namespace unrelated to its folder, is precisely the kind of "spaghetti" the ordering rules were introduced to eliminate — it would reintroduce disorder at a coarser grain than the one already solved.

### 2. Rationale, stated as a teaching principle

Forcing students onto the public surface for testing is not merely a workaround for the package-resolution problem — it is the more valuable lesson. A class whose behavior cannot be adequately verified through its public API is, by definition, exposing too little contract or hiding too much responsibility behind implementation details that the design should have surfaced deliberately (as a queryable method, a returned result object, or a smaller extracted class with its own public surface). This is a restatement, in testing terms, of the same principle already applied to `entity`'s non-overridable equality and `trait`'s `requires` clause: where PYS could offer a flexible escape hatch, it instead asks the student to make the underlying design decision explicit and correct, rather than routing around it.

### 3. Project structure (non-normative, project-manifest level)

```
pys.toml
src/
  billing/
    Invoice.pys        # package: billing
tests/
  billing/
    InvoiceTest.pys    # package: billing — same relative path, different root
```

```toml
[source_roots]
main = "src"
test = "tests"
```

**Resolution rule**: a file's package is its path relative to whichever declared source root contains it. Two files under different roots are in the same package if and only if their post-root-stripping relative paths are identical. `package`-scoped members declared in `src/billing/Invoice.pys` are therefore visible to `tests/billing/InvoiceTest.pys` without any widening of access modifiers, and without any declaration inside either file naming the other.

### 4. Diagnostic for a common beginner mistake this resolution rule creates

Since package identity is now root-relative rather than absolute, a new class of easy-to-make error emerges: a test file placed under the wrong subfolder inside `tests/` silently lands in the wrong package, gaining no special access and failing with an ordinary access-modifier error that gives no hint about *why*. Worth specifying now, consistent with the educational-diagnostic pattern used throughout:

```
Error: 'Invoice.recalculateTotal' is package-private and not visible here.
'InvoiceTest.pys' resolves to package 'test_utils' (relative to source
root 'tests'), which does not match package 'billing' (relative to
source root 'src') where 'Invoice' is declared.
Did you mean to place this file at 'tests/billing/InvoiceTest.pys'?
```

This is the direct testing-context counterpart to the member-ordering diagnostics already specified: it names not just what failed, but the structural reason, and offers the concrete fix.