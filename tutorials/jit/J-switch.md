# JIT — Switch

## Statement

```pys
switch (day) {
    case MONDAY:
        continue
    case FRIDAY:
        continue
    case SUNDAY:
        numLetters = 6
    default:
        numLetters = 0
}
```

- No implicit fall-through
- Trailing `continue` in a case body = fall through to the next case
- Nested-loop `continue` / `break` keep loop meaning
- Bare enum labels resolve from the subject type (`MONDAY` → `Day.MONDAY`)

## Expression

```pys
numLetters = switch (day) {
    case MONDAY, SUNDAY, FRIDAY => 6
    case WEDNESDAY => 9
    default => 0
}
```

- Usable as an assignment RHS
- Multi-label with commas
- Must be exhaustive (all enum members or `default`; non-enum needs `default`)
- All arms must yield the same type

## Rules

1. Subjects: enums and equality-comparable primitives
2. Do not mix `:` (statement) and `=>` (expression) in one switch
3. Statement non-exhaustiveness → warning; expression → error
