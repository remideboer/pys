# 5.4. Abstract classes

A full **class** is a finished machine. An **interface** is only a hollow
socket. An **abstract class** sits between them: a **partial machine** —
some state and gears are already built in, but it leaves **open slots**
that subclasses must **wire** before the apparatus can run.

You cannot construct an abstract class directly. There is no finished
product on the shelf until a concrete class fills every open slot.

> **Sidebar — `inherits` and `super`**
>
> Same tools as [Inheritance and subclasses](chapter_4_inherits.md):
> `inherits AbstractList` specializes that chassis, and `super()` runs the
> parent constructor first so inherited fields (like `size`) are set up.
> Pass arguments inside `super(...)` when the parent needs them.

> **Sidebar — `protected`**
>
> `protected` members are visible inside this class **and** its subclasses,
> but not to unrelated code. Compare: `private` = this class only;
> `public` = anyone.

```pys
abstract class AbstractList {
    protected int size

    public AbstractList() {
        this.size = 0
    }

    public bool isEmpty() {
        return this.size == 0
    }

    public abstract string get(int index)
    public abstract void add(string item)
}

class ArrayListPys inherits AbstractList {
    public ArrayListPys() {
        super()
    }

    public string get(int index) {
        return ""
    }

    public void add(string item) {
        this.size = this.size + 1
    }
}

AbstractList list = ArrayListPys()
list.add("x")
print(list.isEmpty())
```

Output:

```text
False
```


<figure class="concept-diagram" role="img" aria-label="AbstractList as a partial machine with built-in isEmpty and open slots for get and add; ArrayListPys wires those slots">
  <div class="iface-choice">
    <div class="cls-machine is-abstract">
      <div class="cls-head">
        <span class="cls-icon" aria-hidden="true">⚙⚙</span>
        <code>AbstractList</code>
        <span class="cls-tag">abstract · incomplete</span>
      </div>
      <div class="cls-columns">
        <div class="cls-section">
          <div class="cls-section-label">built in already</div>
          <div class="cls-member is-private">
            <span class="cls-lock" aria-hidden="true">🔒</span>
            <code>protected int size</code>
          </div>
          <div class="cls-member is-public">
            <span class="fn-gear" aria-hidden="true">⚙</span>
            <code>public bool isEmpty()</code>
            <span class="cls-note">real body</span>
          </div>
          <div class="cls-member is-public">
            <span class="fn-gear" aria-hidden="true">⚙</span>
            <code>AbstractList()</code>
            <span class="cls-note">assembly</span>
          </div>
        </div>
        <div class="cls-section">
          <div class="cls-section-label">open slots · must wire</div>
          <div class="cls-slot">
            <span class="iface-hole" aria-hidden="true"></span>
            <code>abstract get(index)</code>
            <span class="cls-note">no body yet</span>
          </div>
          <div class="cls-slot">
            <span class="iface-hole" aria-hidden="true"></span>
            <code>abstract add(item)</code>
            <span class="cls-note">no body yet</span>
          </div>
        </div>
      </div>
      <p class="iface-empty">cannot construct — machine not finished</p>
    </div>

    <div class="iface-plug iface-plug-down" aria-hidden="true">
      <span class="iface-plug-arrow">↓</span>
      <span class="iface-plug-label">inherits · wires slots</span>
    </div>

    <div class="cls-machine">
      <div class="cls-head">
        <span class="cls-icon" aria-hidden="true">⚙⚙</span>
        <code>ArrayListPys</code>
        <span class="cls-tag">concrete · complete</span>
      </div>
      <div class="cls-section">
        <div class="cls-section-label">fills the open slots</div>
        <div class="cls-member is-public cls-slot-filled">
          <span class="fn-gear" aria-hidden="true">⚙</span>
          <code>public string get(...)</code>
          <span class="cls-note">wired</span>
        </div>
        <div class="cls-member is-public cls-slot-filled">
          <span class="fn-gear" aria-hidden="true">⚙</span>
          <code>public void add(...)</code>
          <span class="cls-note">wired</span>
        </div>
      </div>
      <div class="cls-channels">
        <span class="cls-channels-label">outside channels (finished apparatus)</span>
        <code>ArrayListPys()</code>
        <code>isEmpty()</code>
        <code>get(…)</code>
        <code>add(…)</code>
      </div>
    </div>
  </div>
  <figcaption>
    Shared gears stay in the abstract chassis; variation points are open
    slots. The subclass does the wiring. Callers may still use an
    <code>AbstractList</code> cable (<code>AbstractList list = …</code>) —
    they talk to the finished plug without rebuilding the shared parts.
  </figcaption>
</figure>

Abstract method signatures need an explicit return type (including
`void` when nothing is returned) — the slot must say what shape of plug
fits. Concrete methods may omit `void` as usual.

**vs interface:** an interface is *only* openings (a socket with no
chassis). An abstract class already has state and working gears, plus
slots.  
**vs trait:** abstract classes **are** types; traits are not.

> **Sidebar — when inheritance is justified**
>
> Ask: does the shared method need to call back into something that *varies
> per subclass*? Here `isEmpty` only needs `size`, but a real `contains`
> would call abstract `get` — that callback is the template-method litmus.
> If you only need “also do X” on unrelated types, prefer a **trait**. If you
> only need a contract with no shared bodies, prefer an **interface**.

### Exercise

> Add `public abstract int count()` and implement it on `ArrayListPys`
> using `this.size`.

---

[Previous: Interfaces](chapter_4_2.md) · [Next: Traits](chapter_4_4.md)
