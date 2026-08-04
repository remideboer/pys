# Back to the basics

> This section is for people with **0%** programming experience. If you
> already know what a variable is, skip ahead to
> [Session 1](chapter_2.md).

The other day someone asked: “Can you teach me how software works — from
scratch?” This chapter is that answer for **PYS**: small steps, plain
language, and examples you can run yourself.

## Hello World

To write software you need:

1. A **compiler** that turns your text into something the computer can run.
2. An **editor** to write that text in.

Complete [Getting ready](chapter_1_1.md) first. Then create `main.pys`:

```pys
print("Hello, world!")
```

Run it:

```shell
python -m transpiler run main.pys
```

You should see `Hello, world!`.

### Exploring Hello World

PYS executes the file **from top to bottom**. Each complete line is a
*statement* — one instruction. Here there is only one: `print(...)`.

- `print` — a built-in that sends a value to the screen.
- `"Hello, world!"` — a *string*: text in double quotes.
- There is **no** semicolon at the end. In PYS a statement ends at the
  newline. Braces `{` `}` group blocks later; they are not decoration.

## Expanding Hello World

Introduce a **variable** — a labeled place to keep a value while the
program runs:

```pys
var firstName = "Ada"
print("Hello, " + firstName + "!")
```

Think of the computer’s memory as a cabinet full of drawers. A variable
is one drawer. Its name — `firstName` — is the label on the drawer so you
can find it again.

`var firstName = "Ada"` does two things:

1. Labels a new drawer `firstName`.
2. Puts `"Ada"` inside it.

> By convention PYS variables use **camelCase**: no spaces, no
> underscores between words; each new word after the first starts with a
> capital letter (`firstName`, not `first_name` or `FirstName`). That matches
> C# and Java, so the habit transfers later.

The `+` between strings *concatenates* them — glues them into one string.
Run the program; you should see `Hello, Ada!`.

### Changing what’s in the drawer

```pys
var firstName = "Ada"
print("Hello, " + firstName + "!")

firstName = "Tom"
print("Greetings, " + firstName + "!")
```

After the first print, we open the `firstName` drawer, remove `"Ada"`, and
put `"Tom"` in. We do **not** write `var` again — the drawer already
exists; we only change its contents. The second print shows
`Greetings, Tom!`.

### A drawer that can’t be swapped: `fix`

Sometimes you want a value that must not change later. PYS has `fix` for
that:

```pys
fix string birthYear = "1990"
print("Born in " + birthYear)

# birthYear = "1991"   # does not compile — the drawer is locked
```

`fix` locks the drawer after the first value is placed. Trying to reopen
it is a **compile error**, not a silent bug later. Prefer `fix` when the
value should stay put; use `var` when you already know it must change.

You will also meet `const` later — a compile-time constant, usually in
`SCREAMING_SNAKE_CASE`. Details: [Variables: var, fix, and const](chapter_2_2.md).

> **Sidebar — typed drawers**
>
> Writing `string label = "hi"` or `int n = 3` declares a reassignable
> binding with an explicit type. Prefer that form once you know the type;
> keep `var` for obvious initializers. Session 1 goes deeper.

### Exercise

> Modify the changing-drawer example so it greets three different people
> in a row, reusing the same `firstName` variable each time. Then try the
> same idea with `fix` for the first name and attempt a second assignment —
> read the error in your own words.

---

[Previous: Getting ready](chapter_1_1.md) · [Next: Functions](basics_functions.md)
