# 2.9. Structuring code

One giant file becomes hard to read. PYS lets you split code across
`.pys` files and **import** names you mark as visible.

## Visibility in one sentence

| Keyword | Who can import it |
|---------|-------------------|
| (omit) | Nobody outside this file |
| `package` | Other files in the **same package** (same folder for now) |
| `global` | Any importer |

> **Sidebar — source roots (later)**
>
> Larger projects can mirror `src/` and `tests/` with a `pys.toml`
> `[source_roots]` table so the same package path exists in both trees.
> That is Session 6: [Packages and source roots](chapter_7_3_packages_source_roots.md).

> **Sidebar — `global` in one line**
>
> `global function void hello() { … }` can be imported from any file.
> Prefer `package` when only same-folder teammates should see the name.

## Two files

`greetings.pys`:

```pys
package function void greet(string name) {
    print("Hello, " + name + "!")
}
```

*Compiles; no output.*



`app.pys` in the **same folder**:

```pys
import greet from greetings

greet("Ada")
```

*Needs the companion `.pys` file from the same section; then prints the call result.*



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
