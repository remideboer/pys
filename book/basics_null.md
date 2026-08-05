# 2.7. Null and missing values

Sometimes a drawer exists but is **empty on purpose**: “we do not have a
value yet.” In PYS that empty marker is `null`. Ordinary types such as
`string` and `int` never hold `null`. Absence must be written on the type:
`nullable<T>`.

> **Sidebar — Dutch *nul* versus technical `null`**
>
> `0` is een waarde: het getal nul. `null` betekent dat er geen waarde
> aanwezig is. An empty string `""` is also a present value — it is text
> with zero characters, not “no string.”

```pys
nullable<string> nickname = null

if (nickname == null) {
    print("No nickname yet")
} else {
    print("Hi, " + nickname)
}
```

Output:

```text
No nickname yet
```

Assign a present value, then use it only after a check (or in the `else`
branch of a null check):

```pys
nullable<string> nickname = null
nickname = "Sanne"

if (nickname != null) {
    print(nickname.upper())
}
```

Output:

```text
SANNE
```

Zero and empty stay distinct from absence:

```pys
nullable<int> number = null
number = 0
nullable<string> text = null
text = ""
print(number == null)
print(text == null)
print(text == "")
```

Output:

```text
false
false
true
```

Compile error — plain types reject `null`:

```pys
string city = null
```

```text
Type 'string' does not allow null.
```

- `null` means “no value is present.”
- Declare `nullable<T>` when absence is part of the contract.
- Always **check** before you use a nullable value as `T`. The compiler
  rejects member access without proof.
- Prefer `result<T, E>` when the interesting case is a **failure** with a
  reason, not ordinary absence. Use `result<nullable<T>, E>` when found,
  not-found, and failed are all meaningful.

> **Sidebar — databases**
>
> SQL `NULL` is the same idea: missing/unknown. A `VARCHAR NULL` column maps
> to `nullable<string>` in PYS. Do not convert SQL `NULL` to `""` — students
> must keep absent and empty distinct. See the shop example under
> `examples/database/`.

### Exercise

> Declare `nullable<string> city = null`. If it is null, print
> `"unknown city"`; otherwise print the city name. Then set `city` to
> `"Utrecht"` and run the non-null path. Expected first output:
> `unknown city`. After the assignment and check: `Utrecht`.

---

[Previous: Conversion](basics_conversion.md) · [Next: Expressing success and failure](basics_outcomes.md)