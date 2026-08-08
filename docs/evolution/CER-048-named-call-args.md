# CER-048: Named call arguments (no mix)

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-08 |
| Commits | `f20adf3` (+ generic-ctor follow-up) |
| Scope | `transpiler/call_args.py`; `sem.py` call binding; `imports.py` `function_param_names`; `ClassDef.type_params`; LANGUAGE / EBNF / book; `tests/test_named_call_args.py` |

## Context

Call sites already parsed `name=expr` (`KeywordArg`) for `struct` / `data`
constructors. Functions, methods, and class constructors emitted keyword args
to Python without binding by parameter name (types were still checked by
position), and structs allowed positional-then-named mixes.

## Entries

### 1. All-positional or all-named for PYS callables

**Pre-behavior:** Named args on functions/methods/ctors were unchecked;
`greet(times=2, name="Ada")` failed type-check as if `times` were argument 1.
Structs allowed `Point(1, y=2)`.

**Why it hurt:** Students expect named binding; mixed styles are easy to
misread; position-based typing of named calls was wrong.

**Post-behavior:** `bind_call_arguments` / `classify_call_args` reject any mix
of positional and named arguments for known PYS functions, methods,
class/`entity` constructors, and `struct`/`data` construction. Named calls
bind by parameter/field name (unknown / duplicate / missing rejected).
Unknown **library** callees may still pass mixed kwargs through to Python
(Tk / connectors).

**Evidence:** `tests/test_named_call_args.py`; updated struct rejection message;
shop GUI still transpiles with mixed Tk kwargs.

### 2. Generic ctor args vs unbound type parameters

**Pre-behavior (after entry 1):** Nullability started type-checking constructor
arguments via `ctor_overloads`. Class type parameters were discarded at parse,
so `Pair<Car, Truck>(car, truck)` compared `Car` to unbound `T` and failed
(`examples/main.pys` / acceptance gates).

**Why it hurt:** Call-site type arguments are still erased for emit; comparing
to `T`/`U` invents a false error and breaks the dense showcase corpus.

**Post-behavior:** Parse keeps `ClassDef.type_params`. Constructor argument
assignability skips slots whose declared type mentions an open type parameter
(arity / named binding still enforced). Concrete ctor params on generic classes
still type-check.

**Evidence:** `test_generic_class_constructor_accepts_concrete_args`,
`test_generic_class_constructor_named_args`, acceptance `examples/main.pys`.

## Trade-offs

- No default parameter values in function signatures (still declaration
  `type name` only) — call-site naming only.
- Library interop keeps Python mixed kwargs; the “no mix” rule is for PYS
  callables students define.
- Full generic substitution at call sites (using preserved `Pair<Car, Truck>`
  type args) remains future work; open type-param slots are unchecked for now.
