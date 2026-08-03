# S8 — Refactor as a habit

## The idea

Industrial IDEs (IntelliJ, VS Code) treat refactoring as a **previewable, reversible
edit** — not a search-replace. PYS teaches the same habit with a small core set
aligned to Fowler’s [catalog](https://refactoring.com/catalog/): Rename, Extract,
Inline, Safe Delete, Introduce Parameter.

Framing:

> Learn the move once in PYS; carry the same discipline into Java/C#/Python even
> when the catalog is larger.

## Why preview matters

IntelliJ shows usages and conflicts before applying. PYS does the same: review
sites, exclude optional ones, then apply (`Ctrl+Z` undoes). Blind global replace
is not a refactor.

## Binding-aware vs text

Renaming `n` in an inner block must not touch an outer `n`. That is the educational
point of binding-aware Find Usages / Rename.

## Member order

When Extract Method runs inside a `class` / `entity`, the new method belongs in
the **methods** section ([ADR-015](../../docs/adr/ADR-015-enforced-ordering.md)).
Refactoring and ordering reinforce each other: structure stays readable after the
edit.

JIT forms: [J-refactor](../jit/J-refactor.md).
