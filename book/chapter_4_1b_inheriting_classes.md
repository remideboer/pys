# 5.2. Inheritance and subclasses

You already built a **Counter** — a machine whose purpose is counting.
Sometimes you need **the same purpose with a special rule**. Tennis does
not count 1, 2, 3…; it jumps 0 → 15 → 30 → 40. That is still *counting
points*, just with a different gear for “advance.”

**Inheritance** lets you build a **subclass**: a specialized machine that
starts from an existing class (`inherits`) instead of reinventing the
whole chassis.

Two reasons this matters — both at once:

1. **Reuse** — keep the shared parts (state shape, `getValue`, assembly
   with `super()`). You only rewrite the part that must differ.
2. **Same kind of thing** — a `TennisCounter` *is still a* `Counter`.
   Code that expects a counting machine can use either; when it calls
   `bump()`, the **special rule of the plugged-in machine** runs.

```pys
class Counter {
    protected int value

    public constructor() {
        this.value = 0
    }

    public open bump() {
        this.value = this.value + 1
    }

    public int getValue() {
        return this.value
    }
}

class TennisCounter inherits Counter {
    public constructor() {
        super()
    }

    public override bump() {
        if (this.value == 0) {
            this.value = 15
        } else if (this.value == 15) {
            this.value = 30
        } else if (this.value == 30) {
            this.value = 40
        } else {
            this.value = this.value + 1
        }
    }
}

Counter ordinary = Counter()
ordinary.bump()
ordinary.bump()
print(ordinary.getValue())

TennisCounter tennis = TennisCounter()
tennis.bump()
tennis.bump()
print(tennis.getValue())

Counter either = tennis
either.bump()
print(either.getValue())
```

Output:

```text
2
30
40
```


Breakdown:

- `class TennisCounter inherits Counter` — specialize the counting
  machine; do not start from zero.
- `super()` in the constructor — run the parent assembly first so
  `value` starts at `0`.
- `protected int value` — subclasses may touch this drawer; unrelated
  code still cannot.
- `public open bump()` on the parent — deliberately opens an extension
  point; subclasses may replace it.
- `public override bump()` in the subclass **replaces** the parent’s bump gear
  with the tennis rule. `getValue` is reused as-is. Without `override` (and
  without `open` on the parent), the transpile fails — methods are closed by
  default.
- `Counter either = tennis` — the cable is typed as the general
  machine; the object on the other end is the tennis specialist. Calling
  `either.bump()` still runs the tennis rule.

<figure class="concept-diagram" role="img" aria-label="Counter base machine and TennisCounter specialization that reuses the chassis but replaces the bump gear">
  <div class="iface-choice">
    <div class="cls-machine">
      <div class="cls-head">
        <span class="cls-icon" aria-hidden="true">⚙⚙</span>
        <code>Counter</code>
        <span class="cls-tag">purpose: counting</span>
      </div>
      <div class="cls-columns">
        <div class="cls-section">
          <div class="cls-section-label">shared chassis</div>
          <div class="cls-member is-private">
            <span class="cls-lock" aria-hidden="true">🔒</span>
            <code>protected int value</code>
          </div>
          <div class="cls-member is-public">
            <span class="fn-gear" aria-hidden="true">⚙</span>
            <code>getValue()</code>
            <span class="cls-note">reused</span>
          </div>
        </div>
        <div class="cls-section">
          <div class="cls-section-label">default rule</div>
          <div class="cls-member is-public">
            <span class="fn-gear" aria-hidden="true">⚙</span>
            <code>bump()</code>
            <span class="cls-note">+1 each time</span>
          </div>
        </div>
      </div>
    </div>

    <div class="iface-plug iface-plug-down" aria-hidden="true">
      <span class="iface-plug-arrow">↓</span>
      <span class="iface-plug-label">inherits · specializes</span>
    </div>

    <div class="cls-machine cls-specialized">
      <div class="cls-head">
        <span class="cls-icon" aria-hidden="true">⚙⚙</span>
        <code>TennisCounter</code>
        <span class="cls-tag">same purpose · special rule</span>
      </div>
      <div class="cls-section cls-station">
        <div class="cls-section-label">keeps from Counter</div>
        <div class="cls-member is-private">
          <span class="cls-lock" aria-hidden="true">🔒</span>
          <code>value</code> · <code>getValue()</code> · <code>super()</code>
        </div>
      </div>
      <div class="cls-section">
        <div class="cls-section-label">replaced gear</div>
        <div class="cls-member is-public cls-slot-filled">
          <span class="fn-gear" aria-hidden="true">⚙</span>
          <code>bump()</code>
          <span class="cls-note">0→15→30→40</span>
        </div>
      </div>
    </div>
  </div>
  <figcaption>
    Specialization, not a brand-new factory: reuse the counting chassis,
    swap only the advance rule. That is inheritance for
    <strong>reuse</strong>.
  </figcaption>
</figure>

<figure class="concept-diagram" role="img" aria-label="Caller cable typed as Counter can plug into ordinary Counter or TennisCounter; bump runs the plugged-in rule">
  <div class="iface-choice">
    <div class="iface-caller">
      <div class="iface-caller-label">caller · general cable</div>
      <code>Counter either</code>
      <span class="cls-note">asks only for counting channels</span>
      <div class="iface-cable" aria-hidden="true">
        <span class="iface-cable-line"></span>
        <span class="iface-cable-tip">either.bump()</span>
      </div>
    </div>

    <div class="iface-impls">
      <div class="cls-machine cls-machine-sm">
        <div class="cls-head">
          <span class="cls-icon" aria-hidden="true">⚙⚙</span>
          <code>Counter</code>
          <span class="cls-tag">ordinary</span>
        </div>
        <div class="cls-member is-public">
          <span class="fn-gear" aria-hidden="true">⚙</span>
          <code>bump() → +1</code>
        </div>
      </div>
      <div class="cls-machine cls-machine-sm cls-specialized">
        <div class="cls-head">
          <span class="cls-icon" aria-hidden="true">⚙⚙</span>
          <code>TennisCounter</code>
          <span class="cls-tag">specialist</span>
        </div>
        <div class="cls-member is-public">
          <span class="fn-gear" aria-hidden="true">⚙</span>
          <code>bump() → tennis</code>
        </div>
      </div>
    </div>
  </div>
  <figcaption>
    Because the subclass <em>is a</em> Counter, the same cable fits both
    machines. The caller does not rewrite its call — yet the tennis
    specialist still answers with its own rule. That is inheritance for
    <strong>using specials through the general type</strong>.
  </figcaption>
</figure>

> **Sidebar — `protected`**
>
> `private` = only this class’s own methods. `protected` = this class
> **and** its subclasses. Tennis needs to update `value` inside its own
> `bump`, so the drawer is `protected`. Unrelated code still has no
> channel to `value`.

### Exercise

> Add a `TwoStepCounter` that `inherits Counter` and whose `bump`
> advances by 2. Store both a `TwoStepCounter` and a `TennisCounter` in
> `Counter` variables and call `bump()` on each.

---

[Previous: Classes and member order](chapter_4_1a_classes.md) · [Next: Interfaces](chapter_4_2_interfaces.md)
