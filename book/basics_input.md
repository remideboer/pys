# 2.2. Processing input

Programs become useful when they react to **you**. Keyboard input is not
a built-in PYS keyword the way `print` is — it comes from Python’s standard
library. You import it once at the top of the file.

> All `import` lines must appear **before** other declarations and
> statements in the file.

```pys
import input from builtins

string name = input("What is your name? ")
print("Hello, " + name + "!")
```

*Sample session (your answers may differ):*

```text
What is your name? Ada
Hello, Ada!
```



What happens:

1. `import input from builtins` — make Python’s `input` available.
2. `input("What is your name? ")` — show the prompt, wait for Enter, return
   the typed text as a `string`.
3. We store that string in `name` and print a greeting.

Run the file, type a name, press Enter.

## Numbers from text

What you type is always text first. To use it as a number, convert it
(see also [Conversion](basics_conversion.md)):

```pys
import input from builtins

string raw = input("How old are you? ")
int age = int(raw)
print("Next year you will be " + str(age + 1))
```

*Interactive — type answers at the prompts; output depends on your input.*



> **Sidebar — typed declarations**
>
> `string name = …` and `int age = …` name the type on the left. That is
> the usual PYS style (more in [Session 1 — Variables](chapter_2_2.md)).
> `var` still works when the right-hand side makes the type obvious.

`int(raw)` asks PYS/Python to parse the string as an integer. If the text
is not a number, the program fails at that line — we will learn gentler
patterns in [Expressing success and failure](basics_outcomes.md).

### Exercise

> Ask for a first name and a favorite number. Print a sentence that uses
> both. Keep imports at the top of the file.

> Stuck? See [Spoiler: Processing input](basics_spoilers_input.md).

---

[Previous: Functions](basics_functions.md) · [Next: Making choices](basics_choices.md)
