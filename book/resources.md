# Resources

## In this repository

- Language reference: [`docs/LANGUAGE.md`](../docs/LANGUAGE.md)
- Grammar (EBNF): [`docs/language.ebnf`](../docs/language.ebnf)
- Railroad diagrams: [`docs/language-railroad.html`](../docs/language-railroad.html)
- Concurrency: [`docs/CONCURRENCY.md`](../docs/CONCURRENCY.md)
- `data` / `entity`: [`docs/DATA_ENTITY.md`](../docs/DATA_ENTITY.md)
- Casing decision: [`docs/pys-casing-convention-advisory.md`](../docs/pys-casing-convention-advisory.md)
- JIT tutorials: [`tutorials/`](../tutorials/)
- Runnable examples: [`examples/`](../examples/)
- Patterns corpus (GoF + architecture / resilience / …): [`examples/patterns/`](../examples/patterns/)
- Book session: [Patterns you name to build](chapter_9_session_patterns.md)

## How the computer runs your code

These optional book chapters explain the machinery without interrupting the
core language path:

- [From source file to running process](under_the_hood_entrypoint.md)
- [Processes, calls, and memory](under_the_hood_memory.md)

## Tooling

- Editor extension: `pys-language/` (install via `python -m transpiler install extension`)
- Run a file: `python -m transpiler run path/to/file.pys`
- Rebuild this HTML locally: `python book/build_html.py` (from `book/`)

## Online copy (GitHub Pages)

After Pages is set to **GitHub Actions** in the repo settings, the beginner
book is published from `book/html` by `.github/workflows/pages-book.yml`:

- https://remideboer.github.io/pys/

## Pedagogical model (credit)

Structure and beginner tone adapted from
**[Rust Development Classes](https://rust-classes.com/)** by
**Marcel Ibes** — see especially
[Back to the basics](https://rust-classes.com/basics).

## What to learn next

After this book: C# or Java with the Session 7 transfer sheet open, plus
the JIT tutorials for any PYS topic you want to drill.

---

[Previous: Exercise — Contact book](exercises_contact_book.md) · [Back to Summary](SUMMARY.md)
