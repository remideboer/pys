## PYS Language Specification — Explicit `nullable<T>` and SQL `NULL` Fidelity

> **Status:** Absorbed — implemented. Permanent homes:
> [ADR-023](../docs/adr/ADR-023-explicit-nullability.md),
> [CER-028](../docs/evolution/CER-028-nullable.md),
> `docs/LANGUAGE.md` (§ Explicit absence), EBNF/railroad, book `basics_null`,
> and `examples/nullable.pys` / `examples/database/`.

### 1. Overview

PYS currently accepts `null` in places whose declared type does not say that a
value may be absent:

```pys
string nickname = null
```

That contradicts PYS's central teaching rule: **make important behavior visible
in the source and enforce it in the compiler**. A reader cannot tell from
`string` alone whether every use is safe, and the compiler cannot require the
author to check before using the value.

It also obscures a foundational database distinction for Dutch students:

- `0` is the number *nul*: a present numerical value.
- `""` is a present string containing zero characters.
- `"   "` is a present but blank string.
- `null` means that no value is present.
- SQL `NULL` is not equal to zero or to an empty string [1].

PYS therefore introduces the built-in generic type `nullable<T>`. Ordinary
`T` is non-null by default; only `nullable<T>` may contain either a `T` value
or the literal `null`.

```pys
string requiredName = "Sanne"
nullable<string> preferredName = null
```

The keyword remains `null`, rather than replacing it with `nothing`, because
students must learn the same technical concept in SQL, C#, Java, Kotlin, and
database APIs. The stronger signal belongs on the **type side**:
`nullable<string>` explicitly announces that different control flow is
required at every use.

### 2. Design goals

1. **Non-null by default.** A plain `T` never silently contains `null`.
2. **Absence visible in the type.** Every nullable parameter, field, local, and
   return value says `nullable<T>`.
3. **Check before use.** A nullable value cannot be used as `T` until control
   flow proves that it is non-null.
4. **Database fidelity.** SQL `NULL`, zero, `false`, empty strings, and empty
   collections remain different values through mapping and persistence.
5. **Transferable vocabulary.** Students learn the industry term `null` while
   PYS removes the implicit-nullability traps found in older type systems.
6. **Explicit words over punctuation.** `nullable<T>` follows `result<T,E>`,
   `lambda<T,R>`, `identity(...)`, and `propagate`; no terse `T?` or `!`.
7. **No duplicate spellings.** `null` is the sole absence literal. PYS does not
   add permanent aliases such as `none`, `nothing`, `empty`, or `blank`.

### 3. Non-goals

1. `nullable<T>` does not mean that a function argument is optional or may be
   omitted. PYS gains no default-argument behavior from this feature.
2. `nullable<T>` does not represent recoverable failure. Use `result<T,E>` when
   the caller needs an error value.
3. This revision adds no force-unwrap operator, safe-navigation operator, or
   null-coalescing operator.
4. This revision does not infer database schemas or automatically generate
   entities from SQL.
5. Python's `None` remains an emitter detail, not an additional PYS spelling.

### 4. Terminology

- **Non-null type `T`:** contains a valid value of `T`; never `null`.
- **Nullable type `nullable<T>`:** contains either a valid `T` or `null`.
- **Underlying type:** the `T` inside `nullable<T>`.
- **Null check:** an explicit comparison with `null`.
- **Narrowing:** compiler proof, within a control-flow region, that a
  `nullable<T>` currently contains `T`.
- **Stable expression:** storage whose value cannot change between its null
  check and use without the compiler observing an invalidating operation.

`null` is a literal and a value-state marker. It is **not** a primitive type,
not the integer zero, and not the empty value of every container.

### 5. Grammar (EBNF extension)

```ebnf
(* ------------------------- Nullable type ------------------------- *)

nullable_type    = "nullable" , "<" , type_expr , ">" ;

(* Amendment to type_expr *)
type_expr        = primitive_type
                 | collection_type , [ type_args ]
                 | named_type , [ type_args ]
                 | array_type
                 | lambda_type
                 | result_type
                 | nullable_type ;

(* Existing literal production; null_lit remains one spelling. *)
literal          = integer | float | boolean | null_lit
                 | char_lit | string_lit ;

null_lit         = "null" ;
```

`nullable` and `null` are reserved lowercase language words. They cannot be
declared as variable, function, parameter, field, or type names.

All declaration, parameter, field, generic-argument, and return-type positions
that accept `type_expr` also accept `nullable_type`. Parser productions with a
historically narrower type alternative must be brought into agreement rather
than adding context-specific nullable syntax.

### 6. Well-formed nullable types

1. `nullable<T>` has exactly one type argument.
2. `T` must be a concrete, non-`void` PYS type.
3. `nullable<void>` is illegal: `void` means a function returns no value; it is
   not a runtime value that can be present or absent.
4. `nullable<nullable<T>>` is illegal. It carries no state beyond
   `nullable<T>` and would add meaningless nesting.
5. `nullable<T>` may wrap primitives, strings, collections, arrays, lambdas,
   classes, interfaces, structs, data values, entities, enums, and results,
   subject to their ordinary type rules.
6. A present struct or data value remains complete. `MyStruct x = null` stays
   illegal; `nullable<MyStruct> x = null` explicitly models absence around the
   complete value.
7. Entity fields named in `identity(...)` may not be nullable. PYS identity
   keys remain present, `fix`, and stable from construction onward.
8. `atomic nullable<T>` is illegal. Atomic remains restricted to its documented
   primitive operations; this feature adds no atomic nullable state machine.

Allowing `nullable<Struct>` and nullable fields inside value types extends the
current ADR-005/ADR-011 null contract and therefore requires an explicit ADR
amendment when implemented. It must not be smuggled in as an emitter accident.

### 7. Assignment and conversion

For an underlying type `T`:

1. A value of type `T` is assignable to `nullable<T>`.
2. `null` is assignable to `nullable<T>`.
3. `null` is not assignable to plain `T`.
4. `nullable<T>` is not assignable to `T` unless the source expression is
   narrowed to `T` at that program point.
5. Ordinary subtype assignment applies to present values. If `Dog` is
   assignable to `Animal`, a `Dog` is assignable to `nullable<Animal>`.
6. PYS performs no conversion from `nullable<Dog>` to `nullable<Animal>` unless
   the ordinary generic/type-variance rules explicitly permit it.
7. Assigning a new value to a narrowed mutable binding invalidates the old
   proof and derives the binding's state from the new right-hand side.
8. Nullable declarations are not implicitly initialized. Authors must still
   initialize fields and locals under the existing definite-assignment rules.

Valid:

```pys
nullable<string> name = null
name = "Fatima"
name = null
```

Rejected:

```pys
string name = null
# Error: Type 'string' does not allow null.
```

### 8. Type inference

1. `var value = null` is illegal because `null` does not reveal an underlying
   type.
2. A contextual target may type the literal:

   ```pys
   nullable<int> score = null
   ```

3. Null elements in a collection literal require a nullable expected element
   type:

   ```pys
   list<nullable<string>> aliases = ["Ada", null, "A."]
   ```

4. A bare collection inferred without an expected type may not infer
   nullability from `null` alone. The author supplies the type.
5. Function calls may use `null` only when the selected parameter type is
   `nullable<T>`. Null must not silently influence overload selection toward an
   unrelated reference type.

### 9. Use-before-check rule

Operations requiring `T` are illegal on an expression of type `nullable<T>`
until it has been narrowed:

- member access and method calls
- indexing, slicing, invocation, arithmetic, and ordering
- passing to a non-null `T` parameter
- returning from a function declared to return non-null `T`
- interpolation formats requiring a concrete primitive/object value

The following is rejected:

```pys
nullable<string> name = null
print(name.upper())
# Error: 'name' may be null; check it before member access.
```

A nullable value is always legal in:

- `== null` and `!= null`
- assignment to a compatible nullable target
- return from a compatible nullable function
- a `switch` whose labels handle the null state
- plain debug/diagnostic inspection

PYS does not treat nullable values as booleans:

```pys
if (name) {             # Error: nullable<string> is not bool
    print(name)
}
```

### 10. Flow-sensitive narrowing

Given `nullable<T> value`:

1. In the true branch of `value != null`, `value` narrows to `T`.
2. In the false branch of `value == null`, `value` narrows to `T`.
3. The corresponding `else` branch receives the complementary state.
4. A guard that exits through `return`, `propagate`, `break`, or `continue`
   narrows the surviving control-flow path.
5. Short-circuit `and` / `or` narrow the right operand only when evaluation of
   that operand proves the value non-null.
6. A `switch` `case null` handles absence. A complementary `default` or
   exhaustive non-null arm treats the expression as `T`.
7. Narrowing is lexical/control-flow information, not a runtime cast.

```pys
function string display(nullable<string> name) {
    if (name == null) {
        return "(geen naam)"
    }
    return name.upper()       # name is string here
}
```

Output:

```text
display(null)       -> (geen naam)
display("Ada")      -> ADA
```

Narrowing is allowed only while the checked storage is stable:

- Local variables and parameters remain narrowed until reassigned.
- `fix` fields remain narrowed after a successful check.
- Assignment to the same mutable field invalidates narrowing.
- A call capable of mutating the same receiver invalidates narrowing of its
  mutable fields.
- `shared` nullable state is not narrowed across separate reads; copy a
  synchronized snapshot into a non-shared local first.
- Captured bindings follow the existing lambda/task capture rules.

The compiler must prefer a conservative rejection over a stale narrowing proof.

### 11. Equality and formatting

1. `null == null` is `true`.
2. `null != null` is `false`.
3. A present value is never equal to `null`.
4. Equality between two present nullable values delegates to `T`'s ordinary
   equality rules.
5. Ordering (`<`, `>`, and related operators) is not defined for `null`.
6. PYS source-level formatting uses the word `null`; Python `None` must not leak
   into `print`, interpolation, debugger display, or diagnostics.

Example:

```pys
nullable<int> unknown = null
nullable<int> zero = 0
print(unknown == null)
print(zero == null)
```

Output:

```text
true
false
```

### 12. Functions: absence versus failure

Use `nullable<T>` when absence is an expected, non-error outcome:

```pys
function nullable<Product> findProduct(string sku) {
    # A missing SKU is ordinary absence.
    return null
}
```

Use `result<T,E>` when an operation can fail and the caller needs the reason:

```pys
function result<Product, string> loadProduct(string sku) {
    return err("database unavailable")
}
```

Use `result<nullable<T>,E>` when all three states are meaningful:

```pys
function result<nullable<Product>, string> queryProduct(string sku) {
    # ok(product): found
    # ok(null): query succeeded, no matching row
    # err(message): query failed
}
```

There is no implicit conversion or unwrapping between `nullable<T>` and
`result<T,E>`.

### 13. Collections and nested position

The position of `nullable` is semantically significant:

```pys
nullable<list<string>> names = null
# The entire list may be absent; present elements are strings.

list<nullable<string>> names = ["Ada", null]
# The list is present; individual elements may be absent.
```

This distinction must survive parsing, semantic analysis, hover text, emitted
runtime behavior, and database/JSON mapping. Diagnostics must print the full
type, not collapse both forms to “nullable list”.

### 14. SQL and Data Mapper contract

SQL `NULL` represents a missing/unknown field and is distinct from every
ordinary domain value [1]. PYS Data Mappers must preserve that distinction.

Given:

```sql
customer_ref VARCHAR(128) NULL
quantity     INT NOT NULL
```

the domain-facing types are:

```pys
public nullable<string> customerRef
public int quantity
```

Required mapping behavior:

1. SQL `NULL` read into `nullable<T>` becomes PYS `null`.
2. A present SQL value becomes a present `T`.
3. PYS `null` bound to a nullable SQL parameter becomes SQL `NULL`.
4. PYS must never silently convert SQL `NULL` to `""`, `0`, `false`, `[]`, or
   `{}`.
5. Reading SQL `NULL` for a domain field declared non-null `T` is a mapping/data
   contract failure, not a default value.
6. SQL `NOT NULL` should map to non-null PYS `T`.
7. Entity identity fields remain non-null even when a database normally
   allocates surrogate keys. Construction/mapping must supply the identity
   before a PYS entity exists, preserving ADR-011.

The current teaching helper in `examples/database/db.pys`:

```pys
public string cellStr(var value) {
    if (value == null) {
        return ""
    }
    return str(value)
}
```

is explicitly pre-behavior to remove. It collapses two database states and can
silently change query/update behavior. A nullable-aware mapper returns
`nullable<string>` and preserves `null`; a mapper for a `NOT NULL` column must
reject a violated database contract rather than invent a value.

### 15. Runtime representation

1. `null` emits to Python `None`.
2. `nullable<T>` is compile-time type information and requires no wrapper
   allocation around present values.
3. Runtime checks use identity with `None` in generated Python, never Python
   truthiness.
4. PYS formatting/debug layers translate backend `None` back to source-level
   `null`.
5. Copy semantics apply only to a present `T`. Copying/assigning `null` remains
   `null`.
6. Hash/equality generation for data/entity/struct values must not accidentally
   treat absent identity as legal; nullable entity identity is rejected
   statically (§6.7).

### 16. Diagnostics and quick fixes

All diagnostics carry PYS source spans, actionable tips, JSON severity, and IDE
CodeActions where an unambiguous edit exists.

#### 16.1 Null assigned to a non-null type — Error

```text
Type 'string' does not allow null.
Tip: Change the declaration to 'nullable<string>' if absence is intentional,
or provide a string value.
```

Quick fixes:

- **Make type nullable**: `string name` → `nullable<string> name`
- **Replace null** is offered only when a safe default is known from an
  explicit source construct; the IDE must not guess `""` or `0`.

#### 16.2 Nullable value used without proof — Error

```text
'name' has type nullable<string> and may be null before '.upper()'.
Tip: Check 'name != null' and handle both paths.
```

Quick fix:

- **Surround with null check**, when the expression is a simple stable name.

#### 16.3 Cannot infer from null — Error

```text
Cannot infer an underlying type from null.
Tip: Write 'nullable<T> value = null' with the intended type.
```

No guessed-type quick fix.

#### 16.4 Invalid nullable argument — Error

```text
'nullable<void>' is invalid because void is not a runtime value.
```

Equivalent tailored messages apply to nested nullable and nullable identity
fields.

#### 16.5 Redundant null check — Warning

```text
'name' has non-null type string, so 'name == null' is always false.
Tip: Remove the check, or make the declaration nullable if absence is intended.
```

Quick fixes:

- Remove the redundant condition when structurally safe.
- Make the declaration nullable when the checked binding is directly editable.

### 17. IDE and tooling surface

Production-ready support includes:

1. `nullable` keyword highlighting in PYS and fenced `pys` Markdown.
2. Completion/snippet for `nullable<T>`.
3. Hover showing the complete declared and narrowed type.
4. Diagnostics and quick fixes from §16 with correct Error/Warning severity.
5. Go to Definition / Find Usages / Rename treating `nullable` as a built-in,
   never a user symbol.
6. Debug Variables, Watch, evaluation, and inline values displaying `null`, not
   Python `None`.
7. Formatter/semantic tokens preserving nested forms such as
   `result<nullable<Product>, string>`.
8. Repository/Data Mapper examples whose contracts use nullable return/field
   types rather than returning `null` from methods declared as plain entities.

### 18. Migration of existing PYS source

The feature is intentionally breaking. PYS is pre-1.0 and should migrate the
repository atomically rather than keep two permanent nullability models.

1. Find every `null` initializer, assignment, return, argument, and comparison.
2. Change the owning type from `T` to `nullable<T>` only where absence is part
   of the domain contract.
3. Replace accidental null defaults with real values or explicit errors.
4. Add narrowing checks before all uses.
5. Update abstract/interface/repository signatures. An implementation may not
   return `null` from a method declared to return plain `T`.
6. Preserve SQL `NULL` in Data Mappers; remove null-to-empty/zero conversions.
7. Keep entity identity fields non-null.
8. Remove the beginner-book form `string nickname = null`; teach
   `nullable<string> nickname = null`.
9. Do not retain `null` as implicitly assignable to legacy non-null types behind
   a compatibility flag.

Concrete database-example migrations include:

```pys
public abstract nullable<Product> get(int id)
public nullable<Product> findById(int id)
public nullable<string> customerRef
```

### 19. Alternatives considered

#### 19.1 Keep implicit nullability (`string name = null`) — rejected

The declaration hides a control-flow obligation, permits unsafe member access,
and contradicts PYS's explicit-type teaching goal.

#### 19.2 Rename the literal to `nothing` / `none` — rejected

A clearer literal alone does not make the type safe. It also weakens direct
transfer to SQL `NULL` and mainstream nullable-reference documentation.

#### 19.3 `optional<T>` — rejected for this concept

“Optional” is broader and overloaded: it may mean an omitted argument, an
optional configuration field, a collection lookup result, or a wrapper such as
Java `Optional`. The selected name states the exact runtime possibility being
taught: this value may be `null`.

#### 19.4 `T?` — rejected

The punctuation is concise but carries too little meaning for beginners and
conflicts with PYS's established preference for full, deliberate language
forms over single-character escape hatches.

#### 19.5 `void`, `empty`, or `blank` as absence literals — rejected

- `void` is a return type and has no runtime value.
- `empty` describes present values such as `""`, `[]`, and `{}`.
- `blank` describes text containing no visible characters, including
  whitespace; it is still a present string.

Reusing these words would teach incorrect concepts that later conflict with
databases and mainstream languages.

#### 19.6 Force unwrap (`name!`) — deferred/rejected for v1

It bypasses the exact safety guarantee `nullable<T>` introduces and encourages
silencing the compiler rather than handling absence. Explicit control flow is
the initial PYS contract.

### 20. Cross-language comparison

| Language/system | Type-level signal | Absence value | Main teaching consequence |
| --- | --- | --- | --- |
| SQL | Column `NULL` / `NOT NULL` constraint | `NULL` | Zero, empty string, and NULL are distinct; comparisons use `IS NULL` [1] |
| C# nullable reference types | `string?` versus `string` | `null` | Compiler flow analysis warns on possible dereference [2] |
| Kotlin | `String?` versus `String` | `null` | Member access requires a null-safe operation or proof [3] |
| TypeScript strict mode | `string | null` | `null` | `strictNullChecks` makes null a distinct type [4] |
| Java | Annotations or `Optional<T>` conventions | `null` / empty Optional | Core reference types remain nullable unless tools/frameworks add discipline [5] |
| Python typing | `T | None` (`Optional[T]`) | `None` | Static checker convention; runtime does not enforce it [6] |
| PYS | `nullable<string>` versus `string` | `null` | Full-word signal, compiler narrowing, SQL vocabulary, no implicit dereference |

PYS deliberately differs in spelling while preserving transferable semantics:
students should recognize C# `string?`, Kotlin `String?`, TypeScript
`string | null`, and SQL `NULL` as other languages' ways to expose the same
state.

### 21. Didactic notes for Dutch students

The first lesson must explicitly separate Dutch *nul* from technical `null`:

> `0` is een waarde: het getal nul. `null` betekent dat er geen waarde
> aanwezig is.

Use paired examples before any nullable member access:

```pys
nullable<int> number = null   # onbekend / afwezig
number = 0                    # bekend: precies nul

nullable<string> text = null  # geen tekstwaarde aanwezig
text = ""                     # tekstwaarde aanwezig, maar leeg
text = " "                    # tekstwaarde aanwezig, maar blanco
```

Expected observations:

```text
null is not 0
null is not ""
"" and " " are both present strings
```

Teaching must then connect the same distinction to a nullable database column.
The SQL example is not an implementation detail; it is the reason retaining
the word `null` is pedagogically valuable.

### 22. BDD acceptance scenarios

#### Scenario A — non-null by default

**Given** `string name = null`  
**When** the program is analyzed  
**Then** compilation fails with `pys.null-non-nullable` and offers **Make type
nullable**.

#### Scenario B — explicit nullable assignment

**Given** `nullable<string> name = null`  
**When** the program is analyzed and emitted  
**Then** compilation succeeds and the runtime stores Python `None` without
exposing the word `None` in PYS output/debug views.

#### Scenario C — use requires proof

**Given** `nullable<string> name`  
**When** `name.upper()` appears without a dominating null check  
**Then** compilation fails with `pys.nullable-use-before-check`.

#### Scenario D — flow narrowing

**Given** `if (name != null) { print(name.upper()) }`  
**When** the body is analyzed  
**Then** `name` has narrowed type `string` in the body and nullable type after
the branch merge.

#### Scenario E — loop re-assignment invalidates proof

**Given** a narrowed mutable nullable binding  
**When** the binding is assigned `null` before a later member access  
**Then** the access fails analysis; the earlier proof is not reused.

#### Scenario F — SQL NULL round trip

**Given** a SQL nullable column containing `NULL`  
**When** a Data Mapper loads and saves the entity unchanged  
**Then** PYS observes `null` and writes SQL `NULL`, never `""` or another
default.

#### Scenario G — present empty string round trip

**Given** the same column contains `""`  
**When** it is loaded and saved  
**Then** PYS observes a present empty string and preserves it as `""`, proving
that empty and null are distinct.

#### Scenario H — identity cannot be nullable

**Given** an `entity` whose `identity(...)` names a `nullable<int>` field  
**When** the entity is analyzed  
**Then** compilation fails with an actionable non-null identity diagnostic.

#### Scenario I — nested position remains distinct

**Given** `nullable<list<string>>` and `list<nullable<string>>`  
**When** hovers, analysis, and emission run  
**Then** each retains its distinct type and allowed null position.

#### Scenario J — nullable is not failure

**Given** `result<nullable<Product>, string>`  
**When** the result is `ok(null)`  
**Then** it is a successful query with no row, distinct from `err(message)`.

### 23. Definition of done

The feature is not complete until all of the following land together:

1. Lexer/parser/AST support for `nullable<T>`.
2. Semantic assignability, inference rejection, stable flow narrowing, branch
   merging, and invalidation.
3. Non-null entity identity enforcement and explicit decisions for structs,
   data, shared state, arrays, lambdas, and generic nesting.
4. Python emission and PYS-facing `null` formatting/debug behavior.
5. Unit tests for happy paths, edge cases, and every rejection in §22.
6. Golden/acceptance tests including SQL NULL versus empty-string round trips.
7. IDE highlighting, completion, hover, diagnostics, severity, and quick fixes.
8. `docs/LANGUAGE.md`, EBNF, `docs/language-railroad.html`, tutorials, and
   examples updated.
9. Beginner-book null chapter rewritten with runnable output/error examples;
   static HTML rebuilt in the same change.
10. Repository/Data Mapper examples migrated to truthful nullable contracts.
11. ADR/CER written or amended, including the deliberate evolution of the
    ADR-005/ADR-011 “no null struct/identity” boundaries.
12. Full Node/Python suites and static checks green.

### 24. References

[1] Oracle Corporation, “Working with NULL Values,” *MySQL 8.4 Reference
Manual*. [Online]. Available:
https://dev.mysql.com/doc/refman/8.4/en/working-with-null.html. [Accessed:
Aug. 5, 2026].

[2] Microsoft, “Nullable reference types,” *C# documentation*. [Online].
Available:
https://learn.microsoft.com/en-us/dotnet/csharp/nullable-references.
[Accessed: Aug. 5, 2026].

[3] JetBrains, “Null safety,” *Kotlin documentation*. [Online]. Available:
https://kotlinlang.org/docs/null-safety.html. [Accessed: Aug. 5, 2026].

[4] Microsoft, “strictNullChecks,” *TypeScript TSConfig Reference*. [Online].
Available:
https://www.typescriptlang.org/tsconfig/strictNullChecks.html. [Accessed:
Aug. 5, 2026].

[5] Oracle Corporation, “Class Optional<T>,” *Java SE API documentation*.
[Online]. Available:
https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html.
[Accessed: Aug. 5, 2026].

[6] Python Software Foundation, “typing — Support for type hints: Optional,”
*Python 3 documentation*. [Online]. Available:
https://docs.python.org/3/library/typing.html#typing.Optional. [Accessed:
Aug. 5, 2026].
