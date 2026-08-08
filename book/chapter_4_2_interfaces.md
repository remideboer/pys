# 5.3. Interfaces

If a class is a machine full of state and gears, an **interface** is only
the **socket on the front**: a faceplate that lists openings (method
signatures) and has **no mechanics inside** — no fields, no method
bodies.

The class that `implements` the interface does the **wiring**: it plugs
real public methods into those openings so current can flow. Different
machines may wire the same socket in different ways. A **caller** only
needs a **fitting cable** — a variable typed as the interface — and calls
through the socket. The caller does not need to know how the insides work,
or even which machine is plugged in.

Omit access modifiers on the interface signatures — they are always
public and abstract. Omit a return type when the method returns nothing
(same rule as classes: `void` is allowed but not required). When a method
returns a value, write the type before the name — builtins (`int`,
`string`, …) **or** another type you defined (`Button`, `Shape`, …).

```pys
interface Greeter {
    greet(string name)
}

class ConsoleGreeter implements Greeter {
    public greet(string name) {
        print("Hello, " + name)
    }
}

class LoudGreeter implements Greeter {
    public greet(string name) {
        print("HEY " + name + "!!!")
    }
}

Greeter g = ConsoleGreeter()
g.greet("Ada")

g = LoudGreeter()
g.greet("Ada")
```

Output:

```text
Hello, Ada
HEY Ada!!!
```


Same cable both times: `g` is a `Greeter`, and `g.greet("Ada")` is the
only shape the caller cares about. First the quiet machine is plugged in;
then the loud one. The socket stayed the same — only the wiring behind it
changed.

### Return types on the socket

Openings may name **what comes out** of the socket — including a type that
is itself another interface. The factory below promises a `Button`; callers
only need `GUIFactory`, not `WinFactory`.

```pys
interface Button {
    string label()
}

interface GUIFactory {
    Button createButton()
}

class OkButton implements Button {
    public constructor() {
    }

    public string label() {
        return "OK"
    }
}

class WinFactory implements GUIFactory {
    public constructor() {
    }

    public Button createButton() {
        return OkButton()
    }
}

GUIFactory factory = WinFactory()
Button b = factory.createButton()
print(b.label())
```

Output:

```text
OK
```

If you only needed a builtin result, write that the same way:
`int capacity()` on the interface and `public int capacity() { … }` on the
class.

<figure class="concept-diagram" role="img" aria-label="Greeter socket with two implementing machines side by side; caller cable connects only to the socket">
  <div class="iface-choice">
    <div class="iface-caller">
      <div class="iface-caller-label">caller · fitting cable</div>
      <code>Greeter g</code>
      <span class="cls-note">does not know the internals</span>
      <div class="iface-cable" aria-hidden="true">
        <span class="iface-cable-line"></span>
        <span class="iface-cable-tip">g.greet("Ada")</span>
      </div>
    </div>

    <div class="iface-socket iface-socket-wide">
      <div class="iface-head">
        <span class="iface-icon" title="socket / contract" aria-hidden="true">⬡</span>
        <code>Greeter</code>
        <span class="cls-tag">interface · socket</span>
      </div>
      <div class="iface-slot">
        <span class="iface-hole" aria-hidden="true"></span>
        <code>greet(string name)</code>
        <span class="cls-note">opening only</span>
      </div>
      <p class="iface-empty">no state · no gears · no body — plug any fitting machine</p>
    </div>

    <div class="iface-impls">
      <div class="iface-plug iface-plug-down" aria-hidden="true">
        <span class="iface-plug-arrow">↓</span>
        <span class="iface-plug-label">wiring A</span>
      </div>
      <div class="iface-plug iface-plug-down" aria-hidden="true">
        <span class="iface-plug-arrow">↓</span>
        <span class="iface-plug-label">wiring B</span>
      </div>
    </div>

    <div class="iface-impls">
      <div class="cls-machine cls-machine-sm">
        <div class="cls-head">
          <span class="cls-icon" aria-hidden="true">⚙⚙</span>
          <code>ConsoleGreeter</code>
          <span class="cls-tag">implementer</span>
        </div>
        <div class="cls-section">
          <div class="cls-section-label">wires the socket</div>
          <div class="cls-member is-public">
            <span class="fn-gear" aria-hidden="true">⚙</span>
            <code>public greet(...)</code>
            <span class="cls-note">prints Hello</span>
          </div>
        </div>
      </div>
      <div class="cls-machine cls-machine-sm">
        <div class="cls-head">
          <span class="cls-icon" aria-hidden="true">⚙⚙</span>
          <code>LoudGreeter</code>
          <span class="cls-tag">implementer</span>
        </div>
        <div class="cls-section">
          <div class="cls-section-label">wires the socket</div>
          <div class="cls-member is-public">
            <span class="fn-gear" aria-hidden="true">⚙</span>
            <code>public greet(...)</code>
            <span class="cls-note">prints HEY!!!</span>
          </div>
        </div>
      </div>
    </div>
  </div>
  <figcaption>
    One socket, two machines side by side. The caller’s cable fits the
    <code>Greeter</code> opening; each implementer does its own wiring
    behind that opening. Swap the plug — the cable and the call stay the
    same.
  </figcaption>
</figure>

`Greeter` is a **type**: you can declare variables of that type and store
any implementing object. The channel you use is still `g.greet(...)` —
the interface listed that opening; the class made it real.

### Exercise

> Add `farewell(string name)` to the interface and implement it on
> **both** `ConsoleGreeter` and `LoudGreeter`. Call each through a
> `Greeter` variable.
>
> Stretch: add `string motto()` to `Greeter` (a builtin return) and print
> each greeter’s motto through the same `Greeter` cable.

---

[Previous: Inheritance and subclasses](chapter_4_1b_inheriting_classes.md) · [Next: Abstract classes](chapter_4_3_abstract_classes.md)
