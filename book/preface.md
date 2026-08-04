# Preface

Welcome to the PYS beginner book.

PYS is a statically typed teaching language that compiles (transpiles) to
Python. It is built for first-year HBO-ICT students who will move on to
**C#** and **Java**. The habits you form here — explicit types, clear
visibility, ordered class members, camelCase names — are meant to transfer
straight into those languages.

## How this book is organized

1. **Preparation** — install the tools and run your first program.
2. **Back to the basics** — for readers with *zero* programming experience.
   Analogies first, jargon second. Skip ahead if you already know what a
   variable is.
3. **Sessions** — deeper PYS topics in class-sized chunks.
4. **Spoilers** — worked solutions for selected basics exercises (try first!).
5. **Under the hood (optional)** — how entrypoints, processes, calls, memory,
   and threads connect the language to the computer running it.
6. **Exercises** and **Resources** — practice and where to go next.

Each section usually follows the same rhythm: a short explanation, a
concrete analogy when it helps, a small runnable example, a line-by-line
walkthrough, and a short hands-on exercise.

## About this book’s shape and tone

The overall structure, warm second-person voice, and progressive
disclosure of this book are modeled on
**[Rust Development Classes](https://rust-classes.com/)** by
**Marcel Ibes** — especially the
[Back to the basics](https://rust-classes.com/basics) section and the
book’s [table of contents](https://rust-classes.com/).

That book teaches Rust. This one teaches PYS. We keep the pedagogical
pattern (gentle basics → numbered sessions → spoilers → exercises →
resources) and replace Rust-specific material — ownership, Axum, embedded
targets, “migrate from C/C++/Go/Java” — with PYS’s own model: `var` /
`fix` / `const`, classes and composition, `tasks` / `shared` / `atomic`,
and a substantial closing session that maps everything you learned to
**C# and Java**.

Thank you, Marcel, for showing how kind and concrete a zero-experience
chapter can be.

## Specs and truth

Every code example in this book is meant to be **valid PYS**. When in
doubt, the language surface in [`docs/LANGUAGE.md`](../docs/LANGUAGE.md)
and the grammar in [`docs/language.ebnf`](../docs/language.ebnf) win over
memory or guesswork.

---

Continue to [Getting ready](chapter_1_1.md).
