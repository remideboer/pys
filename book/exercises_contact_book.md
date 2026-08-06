# Exercise: Contact book

Build a small contact book as a capstone for the basics and early
sessions.

## Requirements

1. Store contacts as a `list<string>` (names only is enough).
2. Provide functions to:
   - add a name,
   - print all names,
   - (optional) remove a name if it exists.
3. Drive the program from keyboard input (`input("…")`, built-in like
   `print`) with a simple menu: `add` / `list` / `quit`.
4. (Stretch) Persist names to `contacts.txt` between runs using
   `from pathlib import Path` and `write_text` / `read_text`.
5. (Stretch) Move pure helpers into a `package` module and keep the menu
   in `app.pys`.

## Acceptance checks

- Adding two names and choosing `list` shows both.
- Choosing `quit` ends the program cleanly.
- Invalid menu input prints a short message and shows the menu again.

## Design notes

- Prefer `fix` for paths and menu prompt strings.
- Keep imports at the top of each file.
- If you introduce a `class ContactBook`, obey member order:
  const → fix → fields → constructors → methods.

---

[Previous (optional): Processes, calls, and memory](under_the_hood_memory.md) · [Next: Resources](resources.md)
