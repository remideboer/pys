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

Output:

```text
Hello, world!
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

Output:

```text
Hello, Ada!
```


Think of the computer’s memory as a cabinet full of drawers. Each drawer
has a **number** (its address). A variable is one drawer; its name —
`firstName` — is a label that points at that number so you can find it
again.

On each drawer you can also read **what kind of data** lives there — the
*type*. Address on the left, type on the right (here drawer **5** is a
`string` drawer holding text).

Here is a tiny map of memory: sixteen drawers in a 4×4 grid, numbered
**0 through 15**. Most are empty. Drawer **5** holds `"Ada"` and wears
the name `firstName`:

<figure class="concept-diagram" role="img" aria-label="Four by four memory drawers numbered 0 to 15; firstName labels string drawer 5 which holds Ada">
  <div class="memory-legend">
    <span class="memory-name-tag">firstName</span>
    <span aria-hidden="true">→</span>
    <span>drawer <strong>5</strong> <code>string</code></span>
  </div>
  <div class="memory-grid">
    <div class="memory-cell"><span class="addr">0</span></div>
    <div class="memory-cell"><span class="addr">1</span></div>
    <div class="memory-cell"><span class="addr">2</span></div>
    <div class="memory-cell"><span class="addr">3</span></div>
    <div class="memory-cell"><span class="addr">4</span></div>
    <div class="memory-cell named">
      <div class="memory-meta"><span class="addr">5</span><span class="type">string</span></div>
      <span class="varname">firstName</span>
      <span class="val">"Ada"</span>
    </div>
    <div class="memory-cell"><span class="addr">6</span></div>
    <div class="memory-cell"><span class="addr">7</span></div>
    <div class="memory-cell"><span class="addr">8</span></div>
    <div class="memory-cell"><span class="addr">9</span></div>
    <div class="memory-cell"><span class="addr">10</span></div>
    <div class="memory-cell"><span class="addr">11</span></div>
    <div class="memory-cell"><span class="addr">12</span></div>
    <div class="memory-cell"><span class="addr">13</span></div>
    <div class="memory-cell"><span class="addr">14</span></div>
    <div class="memory-cell"><span class="addr">15</span></div>
  </div>
  <figcaption>
    Simplified teaching map — real machines use many more addresses.
    The name points at a drawer number; the type says what kind of value
    fits; the value lives in that drawer.
  </figcaption>
</figure>

`var firstName = "Ada"` does two things:

1. Labels a new drawer (here, drawer **5**) with the name `firstName`
   and remembers its type is `string` (text in quotes).
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

Output:

```text
Hello, Ada!
Greetings, Tom!
```


After the first print, we open the `firstName` drawer, remove `"Ada"`, and
put `"Tom"` in. We do **not** write `var` again — the drawer already
exists; we only change its contents. The type stays `string`. The second
print shows `Greetings, Tom!`.

Same drawer number and type, new contents:

<div class="memory-compare">
<figure class="concept-diagram" role="img" aria-label="Memory before reassignment: string drawer 5 firstName holds Ada">
  <div class="memory-legend"><strong>Before</strong> — after <code>var firstName = "Ada"</code></div>
  <div class="memory-grid">
    <div class="memory-cell"><span class="addr">0</span></div>
    <div class="memory-cell"><span class="addr">1</span></div>
    <div class="memory-cell"><span class="addr">2</span></div>
    <div class="memory-cell"><span class="addr">3</span></div>
    <div class="memory-cell"><span class="addr">4</span></div>
    <div class="memory-cell named">
      <div class="memory-meta"><span class="addr">5</span><span class="type">string</span></div>
      <span class="varname">firstName</span>
      <span class="val">"Ada"</span>
    </div>
    <div class="memory-cell"><span class="addr">6</span></div>
    <div class="memory-cell"><span class="addr">7</span></div>
    <div class="memory-cell"><span class="addr">8</span></div>
    <div class="memory-cell"><span class="addr">9</span></div>
    <div class="memory-cell"><span class="addr">10</span></div>
    <div class="memory-cell"><span class="addr">11</span></div>
    <div class="memory-cell"><span class="addr">12</span></div>
    <div class="memory-cell"><span class="addr">13</span></div>
    <div class="memory-cell"><span class="addr">14</span></div>
    <div class="memory-cell"><span class="addr">15</span></div>
  </div>
</figure>
<p class="memory-compare-arrow" aria-hidden="true">→</p>
<figure class="concept-diagram" role="img" aria-label="Memory after reassignment: string drawer 5 firstName now holds Tom">
  <div class="memory-legend"><strong>After</strong> — <code>firstName = "Tom"</code></div>
  <div class="memory-grid">
    <div class="memory-cell"><span class="addr">0</span></div>
    <div class="memory-cell"><span class="addr">1</span></div>
    <div class="memory-cell"><span class="addr">2</span></div>
    <div class="memory-cell"><span class="addr">3</span></div>
    <div class="memory-cell"><span class="addr">4</span></div>
    <div class="memory-cell named changed">
      <div class="memory-meta"><span class="addr">5</span><span class="type">string</span></div>
      <span class="varname">firstName</span>
      <span class="val">"Tom"</span>
    </div>
    <div class="memory-cell"><span class="addr">6</span></div>
    <div class="memory-cell"><span class="addr">7</span></div>
    <div class="memory-cell"><span class="addr">8</span></div>
    <div class="memory-cell"><span class="addr">9</span></div>
    <div class="memory-cell"><span class="addr">10</span></div>
    <div class="memory-cell"><span class="addr">11</span></div>
    <div class="memory-cell"><span class="addr">12</span></div>
    <div class="memory-cell"><span class="addr">13</span></div>
    <div class="memory-cell"><span class="addr">14</span></div>
    <div class="memory-cell"><span class="addr">15</span></div>
  </div>
</figure>
</div>

### A drawer that can’t be swapped: `fix`

Keep building on the same program. `firstName` is still a normal `var`
drawer (we left it holding `"Tom"`). Add a second drawer that must not
change later — PYS uses `fix` for that. A year is a whole number, so this
drawer’s type is `int`, not `string`:

```pys
var firstName = "Ada"
print("Hello, " + firstName + "!")

firstName = "Tom"
print("Greetings, " + firstName + "!")

fix int birthYear = 1990
print(firstName + " was born in " + str(birthYear))

# birthYear = 1991     # does not compile — the drawer is locked
# firstName = "Sam"    # this would still be allowed — var is not locked
```

Output:

```text
Hello, Ada!
Greetings, Tom!
Tom was born in 1990
```

*Compile error if the `birthYear = …` line is uncommented.*

`str(birthYear)` turns the number into text so it can be glued into the
print string. The drawer itself still holds an `int` — look at the type
on the right of the address.

`fix` locks **that** drawer after the first value is placed. Trying to
reopen it is a **compile error**, not a silent bug later. Prefer `fix`
when the value should stay put; use `var` when you already know it must
change.

Memory now has **two** named drawers. Read each label: address on the
left, type on the right — `5 string` versus `9 int`.

<figure class="concept-diagram" role="img" aria-label="Memory with string firstName in drawer 5 holding Tom and fix int birthYear locked in drawer 9 holding 1990">
  <div class="memory-legend">
    <span class="memory-name-tag">firstName</span>
    <span aria-hidden="true">→</span>
    <span>5 <code>string</code></span>
    <span aria-hidden="true">·</span>
    <span class="memory-name-tag">birthYear</span>
    <span aria-hidden="true">→</span>
    <span>9 <code>int</code></span>
    <span aria-hidden="true">🔒</span>
    <span><code>fix</code></span>
  </div>
  <div class="memory-grid">
    <div class="memory-cell"><span class="addr">0</span></div>
    <div class="memory-cell"><span class="addr">1</span></div>
    <div class="memory-cell"><span class="addr">2</span></div>
    <div class="memory-cell"><span class="addr">3</span></div>
    <div class="memory-cell"><span class="addr">4</span></div>
    <div class="memory-cell named">
      <div class="memory-meta"><span class="addr">5</span><span class="type">string</span></div>
      <span class="varname">firstName</span>
      <span class="val">"Tom"</span>
    </div>
    <div class="memory-cell"><span class="addr">6</span></div>
    <div class="memory-cell"><span class="addr">7</span></div>
    <div class="memory-cell"><span class="addr">8</span></div>
    <div class="memory-cell named locked">
      <span class="lock" title="fix — locked" aria-hidden="true">🔒</span>
      <div class="memory-meta"><span class="addr">9</span><span class="type">int</span></div>
      <span class="varname">birthYear</span>
      <span class="val">1990</span>
    </div>
    <div class="memory-cell"><span class="addr">10</span></div>
    <div class="memory-cell"><span class="addr">11</span></div>
    <div class="memory-cell"><span class="addr">12</span></div>
    <div class="memory-cell"><span class="addr">13</span></div>
    <div class="memory-cell"><span class="addr">14</span></div>
    <div class="memory-cell"><span class="addr">15</span></div>
  </div>
  <figcaption>
    Growing example: a <code>string</code> drawer and an <code>int</code>
    drawer. The <code>var</code> can still change; the <code>fix</code>
    stays locked.
  </figcaption>
</figure>

### Memory slowly fills up

Add one more fact — place of birth — without throwing away what you
already have. Another `fix` drawer opens (a `string` again); more of the
map lights up:

```pys
var firstName = "Ada"
print("Hello, " + firstName + "!")

firstName = "Tom"
print("Greetings, " + firstName + "!")

fix int birthYear = 1990
fix string placeOfBirth = "Utrecht"
print(firstName + " was born in " + str(birthYear) + " in " + placeOfBirth)
```

Output:

```text
Hello, Ada!
Greetings, Tom!
Tom was born in 1990 in Utrecht
```

Now **three** named drawers are in use — check the type on each label:

- `firstName` → drawer **5** `string` (`"Tom"`, unlocked `var`)
- `birthYear` → drawer **9** `int` (`1990`, 🔒 `fix`)
- `placeOfBirth` → drawer **12** `string` (`"Utrecht"`, 🔒 `fix`)

<figure class="concept-diagram" role="img" aria-label="Memory filling up: string firstName in drawer 5, fix int birthYear in drawer 9, fix string placeOfBirth in drawer 12">
  <div class="memory-legend">
    <span class="memory-name-tag">firstName</span>
    <span aria-hidden="true">→</span>
    <span>5 <code>string</code></span>
    <span aria-hidden="true">·</span>
    <span class="memory-name-tag">birthYear</span>
    <span aria-hidden="true">→</span>
    <span>9 <code>int</code></span>
    <span aria-hidden="true">🔒</span>
    <span aria-hidden="true">·</span>
    <span class="memory-name-tag">placeOfBirth</span>
    <span aria-hidden="true">→</span>
    <span>12 <code>string</code></span>
    <span aria-hidden="true">🔒</span>
  </div>
  <div class="memory-grid">
    <div class="memory-cell"><span class="addr">0</span></div>
    <div class="memory-cell"><span class="addr">1</span></div>
    <div class="memory-cell"><span class="addr">2</span></div>
    <div class="memory-cell"><span class="addr">3</span></div>
    <div class="memory-cell"><span class="addr">4</span></div>
    <div class="memory-cell named">
      <div class="memory-meta"><span class="addr">5</span><span class="type">string</span></div>
      <span class="varname">firstName</span>
      <span class="val">"Tom"</span>
    </div>
    <div class="memory-cell"><span class="addr">6</span></div>
    <div class="memory-cell"><span class="addr">7</span></div>
    <div class="memory-cell"><span class="addr">8</span></div>
    <div class="memory-cell named locked">
      <span class="lock" title="fix — locked" aria-hidden="true">🔒</span>
      <div class="memory-meta"><span class="addr">9</span><span class="type">int</span></div>
      <span class="varname">birthYear</span>
      <span class="val">1990</span>
    </div>
    <div class="memory-cell"><span class="addr">10</span></div>
    <div class="memory-cell"><span class="addr">11</span></div>
    <div class="memory-cell named locked">
      <span class="lock" title="fix — locked" aria-hidden="true">🔒</span>
      <div class="memory-meta"><span class="addr">12</span><span class="type">string</span></div>
      <span class="varname">placeOfBirth</span>
      <span class="val">"Utrecht"</span>
    </div>
    <div class="memory-cell"><span class="addr">13</span></div>
    <div class="memory-cell"><span class="addr">14</span></div>
    <div class="memory-cell"><span class="addr">15</span></div>
  </div>
  <figcaption>
    Same tiny cabinet, one more drawer occupied. The type on the right of
    each address tells you what kind of data belongs there.
  </figcaption>
</figure>

You will also meet `const` later — a compile-time constant, usually in
`SCREAMING_SNAKE_CASE`. Details: [Variables: var, fix, and const](chapter_2_2.md).

> **Sidebar — typed drawers**
>
> Writing `string label = "hi"` or `int n = 3` declares a reassignable
> binding with an explicit type — the same kind of label you see on the
> right of the drawer number in the maps above. Prefer that form once you
> know the type; keep `var` for obvious initializers. Session 1 goes deeper.

> **Sidebar — one drawer per declaration**
>
> Give every variable its own line: `int x = 10`, then `int y = 10`.
> PYS rejects `int x, y = 10` because it is unclear at a glance whether
> `10` belongs to `y` only or to both names. Separate lines keep one label,
> one drawer, and one starting value together.

### Exercise

> Modify the changing-drawer example so it greets three different people
> in a row, reusing the same `firstName` variable each time. Then try the
> same idea with `fix` for the first name and attempt a second assignment —
> read the error in your own words.

---

[Previous: Getting ready](chapter_1_1.md) · [Next: Functions](basics_functions.md)
