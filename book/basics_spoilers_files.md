# 2.12.3. Spoiler — Files

Exercise: write your name to `me.txt`, read it back, print it.

```pys
from pathlib import Path

Path path = Path("me.txt")
path.write_text("Ada\n", encoding="utf-8")
string text = path.read_text(encoding="utf-8")
print(text)
```

Output:

```text
Ada
```


---

[Previous: Spoiler — structuring](basics_spoilers_structuring.md) · [Next: Formatting output](chapter_2_1_formatting_output.md)
