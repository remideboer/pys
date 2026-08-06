# 5.2. Interfaces

If a class is a machine full of state and gears, an **interface** is only
the **socket on the front**: a faceplate that lists openings (method
signatures) and has **no mechanics inside** — no fields, no method
bodies. Any class that `implements` the interface must wire real public
methods into those openings.

Omit access modifiers on the interface signatures — they are always
public and abstract. Omit a return type when the method returns nothing
(same rule as classes: `void` is allowed but not required).

```pys
interface Greeter {
    greet(string name)
}

class ConsoleGreeter implements Greeter {
    public greet(string name) {
        print("Hello, " + name)
    }
}

Greeter g = ConsoleGreeter()
g.greet("Ada")
```

Output:

```text
Hello, Ada
```


<figure class="concept-diagram" role="img" aria-label="Interface Greeter as a hollow socket; ConsoleGreeter machine plugs public greet into that opening">
  <div class="iface-pair">
    <div class="iface-socket">
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
      <p class="iface-empty">no state · no gears · no body</p>
    </div>
    <div class="iface-plug" aria-hidden="true">
      <span class="iface-plug-arrow">→</span>
      <span class="iface-plug-label">implements</span>
    </div>
    <div class="cls-machine cls-machine-sm">
      <div class="cls-head">
        <span class="cls-icon" aria-hidden="true">⚙⚙</span>
        <code>ConsoleGreeter</code>
        <span class="cls-tag">class machine</span>
      </div>
      <div class="cls-section">
        <div class="cls-section-label">wired to the socket</div>
        <div class="cls-member is-public">
          <span class="fn-gear" aria-hidden="true">⚙</span>
          <code>public greet(string name)</code>
          <span class="cls-note">real body</span>
        </div>
      </div>
      <div class="cls-channels">
        <span class="cls-channels-label">outside channel</span>
        <code>greet(…)</code>
      </div>
    </div>
  </div>
  <figcaption>
    The socket promises <code>greet</code> exists. The class supplies the
    working gear. Callers can depend on the socket type
    (<code>Greeter g</code>) without caring which machine is plugged in.
  </figcaption>
</figure>

`Greeter` is a **type**: you can declare variables of that type and store
any implementing object. The channel you use is still `g.greet(...)` —
the interface listed that opening; the class made it real.

### Exercise

> Add `farewell(string name)` to the interface and implement it on
> `ConsoleGreeter`.

---

[Previous: Classes](chapter_4_1.md) · [Next: Abstract classes](chapter_4_3.md)
