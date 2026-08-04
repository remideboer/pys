# 2.12.2. Spoiler — Structuring code

`mathUtils.pys`:

```pys
package function int double(int n) {
    return n * 2
}
```

*Declaration only — runs when another file imports and calls it.*



`app.pys` (same folder):

```pys
import double from mathUtils

print(double(21))
```

*Needs the companion `.pys` file from the same section; then prints the call result.*



---

[Previous: Spoiler — input](basics_spoilers_input.md) · [Next: Spoiler — files](basics_spoilers_files.md)
