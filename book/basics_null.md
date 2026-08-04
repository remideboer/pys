# 2.7. Null and missing values

Sometimes a drawer exists but is **empty on purpose**: “we do not have a
value yet.” In PYS that empty marker is `null`.

```pys
string nickname = null

if (nickname == null) {
    print("No nickname yet")
} else {
    print("Hi, " + nickname)
}
```

- `null` means “no value”.
- Always **check** before you use a value that might be null. Using a null
  where a real object is required blows up at runtime.

> Not every type happily accepts `null`. Struct fields, for example, reject
> null — structs are meant to be complete values. Classes and many reference
> types can be null; follow the compiler when it refuses an assignment.

### Exercise

> Declare `string city = null`. If it is null, print `"unknown city"`;
> otherwise print the city name. Then set `city` to `"Utrecht"` and run the
> `else` path mentally (or by editing the program).

---

[Previous: Conversion](basics_conversion.md) · [Next: Expressing success and failure](basics_outcomes.md)
