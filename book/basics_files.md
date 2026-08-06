# 2.10. Files

Saving data between runs means talking to the **filesystem**. PYS reaches
Python’s `pathlib.Path` through an import (the same pattern real examples
in this repo use).

> **Sidebar — import spellings**
>
> `input` and `print` are built-in — no import. For libraries such as
> `pathlib`, use `from pathlib import Path` (Python-shaped form some modules
> expect). All imports must stay at the **top** of the file.
```pys
from pathlib import Path

Path path = Path("note.txt")
path.write_text("Hello from PYS\n", encoding="utf-8")
string text = path.read_text(encoding="utf-8")
print(text)
```

Output:

```text
Hello from PYS
```


- `Path("note.txt")` — a path relative to where you run the command.
- `write_text` — create or overwrite the file with a string.
- `read_text` — read the whole file back as a `string`.

Keep paths simple while learning. You can grow into folders and JSON later
the same way.

> Spoiler solution: [Files](basics_spoilers_files.md).

### Exercise

> Write your name to `me.txt` with `write_text`, read it back with
> `read_text`, and print the result.

---

[Previous: Structuring code](basics_structuring.md) · [Next: A small contact book](basics_project.md)
