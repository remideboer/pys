# 2.12.2. Spoiler — Structuring code

`mathUtils.pys`:

```pys
package function int double(int n) {
    return n * 2
}
```

`app.pys` (same folder):

```pys
import double from mathUtils

print(double(21))
```

---

[Previous: Spoiler — input](basics_spoilers_input.md) · [Next: Spoiler — files](basics_spoilers_files.md)
