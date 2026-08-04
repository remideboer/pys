# 2.9. Structuring code

One giant file becomes hard to read. PYS lets you split code across
`.pys` files and **import** names you mark as visible.

## Visibility in one sentence

| Keyword | Who can import it |
|---------|-------------------|
| (omit) | Nobody outside this file |
| `package` | Other files in the **same package** (same folder, or mirrored under `pys.toml` source roots) |
| `global` | Any importer |

## Two files

`greetings.pys`:

```pys
package function void greet(string name) {
    print("Hello, " + name + "!")
}
```

`app.pys` in the **same folder**:

```pys
import greet from greetings

greet("Ada")
```

Rules that bite beginners:

1. Imports must be at the **top** of the file.
2. You can only import names marked `package` or `global`.
3. The module name in `from greetings` matches the file `greetings.pys`
   (without the extension), for same-folder imports.

> Stuck? See [Spoiler: Structuring code](basics_spoilers_structuring.md).

### Exercise

> Create `mathUtils.pys` with `package function int double(int n)` that
> returns `n * 2`. From `app.pys` in the same folder, import and print
> `double(21)`.

---

[Previous: Expressing success and failure](basics_outcomes.md) · [Next: Files](basics_files.md)
