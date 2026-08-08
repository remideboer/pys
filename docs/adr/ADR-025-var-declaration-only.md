# ADR-025: `var` is declaration-only; `object` for opaque foreign values

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-08 |
| Commits | (same change set as CER-042) |

## Context

EBNF already treats `var` as a declaration form (`var name = expr`), not a
type. The toolchain still accepted `var` as a return type, parameter type, and
field type — used as a dynamic escape hatch for sockets, locks, and driver
cells in production-style examples. That under-specification hid invalid
teaching surface (e.g. `public var lookup(...)`).

## Decision

1. **`var` is only a local / script-top declaration** with a required
   initializer. Type is inferred. Script/module top-level `var name = expr`
   remains legal (teaching programs have no enclosing function).
2. **`var` is illegal in type position:** method/function return types,
   parameters, instance fields, generic type arguments, and lambda parameters
   without a known target type.
3. **`object` is the opaque foreign-value type** for returns and fields when no
   concrete PYS type applies. Anything may assign **into** `object`.
4. **Parameters may omit the type** at foreign boundaries (`serveOne(conn)`),
   matching existing EBNF `parameter = [ type_name ] , identifier`.

## Consequences

- Parser rejects type-position `var` with code `pys.var-as-type` (tips + IDE
  quick fixes).
- Sem assignability escape hatch moves from `declared == "var"` to
  `declared == "object"`.
- Examples that used signature/field `var` migrate to `object` or omitted
  param types (CER-042).

## Rejected alternatives

- New `any` keyword — duplicates `object` without clearer teaching value.
- Banning script-top `var` — would rewrite the beginner book for little gain.
