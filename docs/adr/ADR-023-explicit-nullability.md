# ADR-023: Explicit nullability and SQL `NULL` fidelity

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-05 |
| Code detail | [CER-028](../evolution/CER-028-nullable.md) |

## Context

PYS accepted `null` for declarations whose types did not reveal absence:
`string name = null`. That hid a required control-flow branch, allowed unsafe
uses, and made SQL `NULL`, `0`, and `""` easy to collapse in teaching Data
Mappers. In particular, the database example converted SQL `NULL` to `""`.

PYS teaches important behavior by making it visible and compiler-enforced.
Students also need the transferable database meaning of `null`: no value is
present. The Dutch number *nul* (`0`) is still a present numeric value.

## Decision

1. Plain `T` is non-null. Only `nullable<T>` may hold either `T` or `null`.
2. `nullable<T>` is compile-time type information. Python uses `None` without
   allocating a wrapper, but PYS-facing output and debugger values say `null`.
3. Use of `nullable<T>` as `T` requires conservative flow proof from an
   explicit null check. Reassignment, mutable calls, loops, capture, and shared
   reads invalidate facts whenever safety cannot be proven.
4. `nullable<void>`, `nullable<nullable<T>>`, and `atomic nullable<T>` are
   invalid. `shared nullable<T>` is allowed, but separate shared reads do not
   narrow; authors copy a synchronized snapshot to a local first.
5. A present struct or data value remains complete. `nullable<Struct>` and
   nullable non-identity fields are allowed; plain `Struct = null` is not.
6. Entity identity fields remain non-null and `fix`. Nullable identity is a
   compile-time error.
7. `nullable<T>` represents expected absence. `result<T,E>` represents failure;
   `result<nullable<T>,E>` explicitly represents success-with-value,
   success-without-value, and failure.
8. SQL `NULL` maps to PYS `null` and back. Empty strings, zero, false, and empty
   collections remain present values. A database `NULL` for a non-null domain
   field is a mapping contract failure.
9. There is no compatibility flag, force unwrap, safe-navigation, coalescing
   operator, `T?` spelling, or alias such as `none` / `nothing`.

## Consequences

- Existing PYS sources that relied on implicit nullability migrate atomically.
- The semantic analyzer owns assignability, narrowing, invalidation,
  diagnostics, and narrowed hover facts.
- IDE Error/Warning diagnostics and CodeActions teach null handling rather than
  guessing defaults.
- ADR-005 evolves to permit an explicit nullable wrapper around complete
  values. ADR-011 evolves to permit nullable non-identity fields while keeping
  identity non-null.
- Data Mappers preserve SQL state faithfully.

## Rejected alternatives

- **Implicit nullability:** hides the branch obligation and defeats static
  checks.
- **`optional<T>`:** overloads absence with omitted arguments and configuration.
- **`T?`:** terse punctuation is weaker teaching syntax than `nullable<T>`.
- **`none`, `nothing`, `empty`, or `blank`:** weakens transfer to SQL and
  confuses absent values with present empty values.
- **Force unwrap:** bypasses the safety guarantee instead of handling absence.

## References

1. Oracle Corporation, “Working with NULL Values,” *MySQL 8.4 Reference
   Manual*, https://dev.mysql.com/doc/refman/8.4/en/working-with-null.html
   (accessed 2026-08-05).
2. Microsoft, “Nullable reference types,”
   https://learn.microsoft.com/dotnet/csharp/nullable-references
   (accessed 2026-08-05).
3. JetBrains, “Null safety,” https://kotlinlang.org/docs/null-safety.html
   (accessed 2026-08-05).
4. Microsoft, “strictNullChecks,”
   https://www.typescriptlang.org/tsconfig/strictNullChecks.html
   (accessed 2026-08-05).
5. Python Software Foundation, “typing.Optional,”
   https://docs.python.org/3/library/typing.html#typing.Optional
   (accessed 2026-08-05).
