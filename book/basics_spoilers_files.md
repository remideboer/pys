# 2.12.3. Spoiler — Files

Exercise: write your name to `me.txt`, read it back, print it.

```pys
from pathlib import Path

Path path = Path("me.txt")
path.write_text("Ada\n", encoding="utf-8")
string text = path.read_text(encoding="utf-8")
print(text)
```

---

[Previous: Spoiler — structuring](basics_spoilers_structuring.md) · [Next: Session 1](chapter_2.md)
