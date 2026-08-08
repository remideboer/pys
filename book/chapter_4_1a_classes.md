# 5.1. Classes and member order

A **class** is a **machine designed for one clear purpose** — here,
counting. It keeps the **state** that purpose needs (fields — drawers that
remember values) and the **parts** that do the jobs (methods).

A **method** is like a function, but it is a *part of that machine*: each
one has a **specific job** inside the purpose (`bump` advances the count;
`getValue` reports it). Alone, a free function is a single reusable gear;
inside a class, those gears work together on the same state toward the
same goal.

The class text is the *blueprint*; each time you call the constructor you
get a new *object* — its own running copy of the machine.

```pys
class Counter {
    public const int DEFAULT_STEP = 1
    private fix string label
    private int value

    public constructor(string label) {
        this.label = label
        this.value = 0
    }

    public bump() {
        this.value = this.value + Counter.DEFAULT_STEP
    }

    public int getValue() {
        return this.value
    }
}

Counter c = Counter("demo")
c.bump()
print(c.getValue())
```

Output:

```text
1
```


Breakdown:

- `class Counter { … }` — blueprint for a machine whose purpose is
  counting.
- Fields (`label`, `value`) — **per-instance state** that purpose needs;
  lives with each object.
- `public const DEFAULT_STEP` — a **class-wide** constant (one value for the
  type, not a drawer on each object). Read it as `Counter.DEFAULT_STEP`.
  Optional `static` on fields/methods marks the same class-wide idea for
  mutable helpers; see [Processes, calls, and memory](under_the_hood_memory.md)
  (*Class-wide vs per-instance*).
- `public constructor(...)` — the **constructor** (see below): assembles one
  object and fills its drawers.
- Methods (`bump`, `getValue`) — **parts with a job** in that machine;
  call them on an object (`c.bump()`).
- No return type on `bump` — that job does not hand a value back (same
  idea as a procedure). You *may* write `void` explicitly; the grammar
  allows omitting it. When something *is* returned, write the type
  (`public int getValue()`).

<figure class="concept-diagram" role="img" aria-label="Counter class as a machine: private state inside, public methods and const as channels to the outside">
  <div class="cls-machine">
    <div class="cls-head">
      <span class="cls-icon" title="class machine" aria-hidden="true">⚙⚙</span>
      <code>Counter</code>
      <span class="cls-tag">purpose: counting</span>
    </div>
    <div class="cls-columns">
      <div class="cls-section">
        <div class="cls-section-label">state</div>
        <div class="cls-member is-public" title="reachable from outside">
          <span class="cls-channel" aria-hidden="true">↕</span>
          <code>public const DEFAULT_STEP</code>
        </div>
        <div class="cls-member is-private" title="not reachable from outside">
          <span class="cls-lock" aria-hidden="true">🔒</span>
          <code>private fix label</code>
        </div>
        <div class="cls-member is-private" title="not reachable from outside">
          <span class="cls-lock" aria-hidden="true">🔒</span>
          <code>private int value</code>
        </div>
      </div>
      <div class="cls-section">
        <div class="cls-section-label">methods</div>
        <div class="cls-member is-public" title="reachable from outside">
          <span class="fn-gear" aria-hidden="true">⚙</span>
          <code>public bump()</code>
          <span class="cls-note">no return value</span>
        </div>
        <div class="cls-member is-public" title="reachable from outside">
          <span class="fn-gear" aria-hidden="true">⚙</span>
          <code>public int getValue()</code>
          <span class="cls-note">returns int</span>
        </div>
      </div>
    </div>
    <div class="cls-channels">
      <span class="cls-channels-label">outside channels</span>
      <code>Counter(…)</code>
      <code>DEFAULT_STEP</code>
      <code>bump()</code>
      <code>getValue()</code>
    </div>
  </div>
  <figcaption>
    One purpose, many parts: <code>bump</code> and <code>getValue</code>
    each do one job for the counting machine.
    <strong>Public</strong> members are communication channels;
    <strong>private</strong> state stays sealed — only the machine’s own
    methods may touch <code>label</code> and <code>value</code>. Callers
    use <code>c.bump()</code> / <code>c.getValue()</code> instead of
    writing to <code>value</code> directly.
  </figcaption>
</figure>

Try the contrast mentally: after `Counter c = Counter("demo")`, the
outside world can call `c.bump()` and read `c.getValue()`, but
`c.value = 99` is not allowed — there is no channel for that field.

## The constructor: assembling the machine

The **constructor** is a special part whose job is not the day-to-day
purpose (counting), but **building** a ready-to-use machine.

- It is written with the **`constructor` keyword**:
  `public constructor(...)` (not the class name).
- Creating an object looks like a call: `Counter("demo")`. That call
  **runs the constructor once**. The parameter (`label`) is material the
  assembly needs — a name plate for this counter.
- Inside the body, `this.field = …` fills the drawers so the object
  starts in a **valid state** (`value` at `0`, `label` set). Until the
  constructor finishes, the machine is not ready for `bump` / `getValue`.
  Bare field names are not allowed — always write `this.label`, not
  `label`, when you mean the field.
- After creation you use the other channels (`c.bump()`). You rarely call
  the constructor again on the same object — assembly already happened.

| If you already know… | How `constructor` maps |
| --- | --- |
| JavaScript | Same word — `constructor(...)` is reserved there too |
| C# / Java | Drop the keyword; the method is named like the class |

Think of it as the **startup / assembly step** on the factory floor: bolt
the parts on, set the dials, then hand the finished machine to the caller.

## Machines that work together

Real programs are seldom one lonely machine. A class with a small purpose
often becomes a **station on a larger assembly line** — a bigger apparatus
whose purpose needs counting as a *sub-task*.

Here a `ScoreBoard` keeps a team’s score. It does **not** re-implement
counting; it **owns** a `Counter` and talks to it through that machine’s
public channels.

```pys
class Counter {
    public const int DEFAULT_STEP = 1
    private fix string label
    private int value

    public constructor(string label) {
        this.label = label
        this.value = 0
    }

    public bump() {
        this.value = this.value + Counter.DEFAULT_STEP
    }

    public int getValue() {
        return this.value
    }
}

class ScoreBoard {
    private fix string team
    private Counter goals

    public constructor(string team) {
        this.team = team
        this.goals = Counter(team + " goals")
    }

    public score() {
        this.goals.bump()
    }

    public int getScore() {
        return this.goals.getValue()
    }
}

ScoreBoard board = ScoreBoard("Home")
board.score()
board.score()
print(board.getScore())
```

Output:

```text
2
```


Notice the **constructor collaboration**: `ScoreBoard(...)` assembles the
big apparatus *and* builds the smaller counting station
(`this.goals = Counter(...)`). The outside world only talks to the
scoreboard; counting stays a sealed sub-task inside.

<figure class="concept-diagram" role="img" aria-label="ScoreBoard apparatus containing a Counter station; score calls bump on the nested counter">
  <div class="cls-factory">
    <div class="cls-factory-head">
      <span class="cls-factory-icon" aria-hidden="true">🏭</span>
      <span>larger apparatus</span>
      <span class="cls-tag">assembly line</span>
    </div>
    <div class="cls-machine">
      <div class="cls-head">
        <span class="cls-icon" aria-hidden="true">⚙⚙</span>
        <code>ScoreBoard</code>
        <span class="cls-tag">purpose: team score</span>
      </div>
      <div class="cls-columns">
        <div class="cls-section">
          <div class="cls-section-label">own state</div>
          <div class="cls-member is-private">
            <span class="cls-lock" aria-hidden="true">🔒</span>
            <code>private fix team</code>
          </div>
        </div>
        <div class="cls-section cls-station">
          <div class="cls-section-label">sub-station</div>
          <div class="cls-machine cls-machine-nested">
            <div class="cls-head">
              <span class="cls-icon" aria-hidden="true">⚙⚙</span>
              <code>Counter</code>
              <span class="cls-tag">purpose: counting</span>
            </div>
            <p class="cls-station-note">
              Owned as <code>private Counter goals</code> —
              only <code>ScoreBoard</code> reaches its channels.
            </p>
            <div class="cls-channels">
              <span class="cls-channels-label">used internally</span>
              <code>bump()</code>
              <code>getValue()</code>
            </div>
          </div>
        </div>
      </div>
      <div class="cls-line">
        <span class="cls-line-label">collaboration flow</span>
        <div class="cls-line-steps">
          <code>board.score()</code>
          <span class="cls-line-arrow" aria-hidden="true">→</span>
          <code>goals.bump()</code>
          <span class="cls-line-arrow" aria-hidden="true">→</span>
          <span class="cls-note">count advances</span>
        </div>
      </div>
      <div class="cls-channels">
        <span class="cls-channels-label">outside channels (whole apparatus)</span>
        <code>ScoreBoard(…)</code>
        <code>score()</code>
        <code>getScore()</code>
      </div>
    </div>
  </div>
  <figcaption>
    Two purposes, nested: scoring is the factory’s job; counting is a
    dedicated station inside it. Each class stays a machine for
    <em>one</em> purpose — collaboration connects them instead of stuffing
    every job into one giant class.
  </figcaption>
</figure>

## Why member order is enforced

Inside a class body, PYS requires this **kind** order:

1. `const` fields  
2. `fix` fields  
3. mutable fields  
4. constructors  
5. methods  

Visibility (`public` / `private` / …) may vary within a section, but you
cannot put a method above a field or a mutable field above a `fix` field.
If the order is wrong, you get a **parse error**, not a polite lint.

Why? Good practice in C# and Java is the same order; PYS makes the habit
impossible to skip so you learn it once.

Constructor name equals the class name. Use `this.field` for members.

### Exercise

> Add `public string getLabel()` to `Counter` (still after the constructor).
> Intentionally move a method above a field and read the error.
> Then sketch (on paper or in code) a second apparatus that owns a
> `Counter` for a different purpose — for example a `Page` that counts
> visits.

---

[Previous: Enums and switch](chapter_3_5_enums_and_switch.md) · [Next: Inheritance and subclasses](chapter_4_1b_inheriting_classes.md)
