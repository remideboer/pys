# JIT — Enums

## Forms

```pys
package enum Priority {
    LOW,
    MEDIUM,
    HIGH
}

enum HttpStatus {
    OK = 200,
    CREATED = 201
}

HttpStatus s = HttpStatus.OK
print(s == HttpStatus.OK)
print(s.value)
```

## Rules

1. Non-empty body; members separated by `,` (optional trailing comma); all
   members have `=` or none do
2. Explicit values: all `int` or all `string`, unique
3. Use `EnumName.MEMBER` only; `.value` for underlying int/string
4. Same-enum `==` only; no bare int/string assign into an enum type
5. Prefer `SCREAMING_SNAKE_CASE` (warning + IDE rename fix)
6. Visibility: optional `global` / `package` / `module` on the enum

Closed set of named constants → **enum**. Fixed fields without behavior →
**struct** ([J-struct](J-struct.md)). Behavior / inheritance → **class**
([J-class](J-class.md)).
