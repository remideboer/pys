# CER-009: Abstract classes

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Commits | (abstract-class increment) |
| Scope | `lex.py`, `parse.py`, `ast_nodes.py`, `sem.py`, `emit/python.py`, `emit/overloads.py`; `pys-language/*`; `docs/*`; `examples/abstract_classes.pys`; `tests/test_abstract_class.py` |
| ADRs | [ADR-010](../adr/ADR-010-abstract-classes.md) |

## Context

Requirements specify Java-style abstract classes with body-less abstract methods
and `void`, for template-method teaching samples.

### Pre-behavior

No `abstract` / `void` keywords; only `interface` signatures and concrete
classes. Overload post-pass treated `@decorator` lines as class text and
hoisted them before all methods.

### Post-behavior

- Lex/parse: `abstract class`, abstract methods (no body), `void` return type;
  `sealed` XOR `abstract`.
- Sem: placement, subclass implementation, no instantiate, void returns.
- Emit: `ABC` + `@abstractmethod`; overload rewriter keeps decorators attached
  to the following `def`.
- IDE: TextMate, hover, snippets, go-to; extension ≥ 0.0.42.
- Docs: LANGUAGE, EBNF, railroad, JIT `J-abstract`, ADR-010.

### Evidence

`tests/test_abstract_class.py`; `examples/abstract_classes.pys` (toys + base +
intermediate abstract class, two storage strategies, polymorphic helper,
comments) with workspace-isolated `run_source` (CER-001 §4).

## Trade-offs

- Runtime ABC enforcement is optional teaching sugar; compile-time checks are
  the source of truth for incomplete subclasses.
