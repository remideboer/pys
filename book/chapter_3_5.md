# 4.5. Enums and switch

## Enums

Closed sets of named constants — member names should be
`SCREAMING_SNAKE_CASE`:

```pys
enum Day {
    MONDAY
    WEDNESDAY
    FRIDAY
    SUNDAY
}

Day today = Day.FRIDAY
print(today == Day.FRIDAY)
```

Output:

```text
True
```


## Switch statement

No implicit fall-through. Use bare `continue` to fall into the next case
when you mean it:

```pys
enum Day {
    MONDAY
    WEDNESDAY
    FRIDAY
    SUNDAY
}

Day day = Day.FRIDAY
int numLetters = 0
switch (day) {
    case MONDAY:
        continue
    case FRIDAY:
        continue
    case SUNDAY:
        numLetters = 6
    case WEDNESDAY:
        numLetters = 9
    default:
        numLetters = 0
}
print(numLetters)
```

Output:

```text
6
```


> **Sidebar — loop `continue` vs switch `continue`**
>
> In a **loop**, `continue` means “skip to the next iteration”
> ([Loops](chapter_3_2.md)). In a **switch statement**, bare `continue`
> means “fall through into the next `case`.” Same word, different jobs —
> read the surrounding keyword (`loop` vs `switch`) to know which.

## Switch expression

```pys
enum Day {
    MONDAY
    WEDNESDAY
    FRIDAY
    SUNDAY
}

Day day = Day.WEDNESDAY
int numLetters = switch (day) {
    case MONDAY, SUNDAY, FRIDAY => 6
    case WEDNESDAY => 9
    default => 0
}
print(numLetters)
```

Output:

```text
9
```


Do not mix `:` arms and `=>` arms in one switch.

### Exercise

> Define `enum TrafficLight { RED, YELLOW, GREEN }`. Given a light, print
> whether to `"stop"`, `"wait"`, or `"go"` using a switch expression.

---

[Previous: Dicts, tuples, and sets](chapter_3_4.md) · [Next: Classes and member order](chapter_4_1.md)
