# 2.8. Expressing success and failure

PYS has no Rust-style `Result` type and no `try` / `catch` keywords. When
an operation can succeed or fail in a *business* sense, name those outcomes
explicitly — often with an **enum** and a `switch`.

```pys
enum ParseResult {
    OK
    BAD_INPUT
}

function ParseResult checkAge(int age) {
    if (age < 0) {
        return ParseResult.BAD_INPUT
    }
    return ParseResult.OK
}

ParseResult result = checkAge(15)
switch (result) {
    case OK:
        print("age looks fine")
    case BAD_INPUT:
        print("age cannot be negative")
}
```

Output:

```text
age looks fine
```


- `enum ParseResult` — a closed set of named outcomes.
- Members use `SCREAMING_SNAKE_CASE` by convention.
- The function returns which case happened; the caller switches on it.

This pattern scales: add more enum members when you need more distinct
failures, instead of overloading a single magic number.

### Exercise

> Write `function ParseResult checkPassword(string password)` that returns
> `BAD_INPUT` if the password length is less than 8 (`len(password) < 8`),
> otherwise `OK`. Print a message for each outcome.

---

[Previous: Null and missing values](basics_null.md) · [Next: Structuring code](basics_structuring.md)
