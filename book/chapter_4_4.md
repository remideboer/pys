# 5.5. Traits

A **trait** is a **bolt-on piece of gearing** — a part-machine you mount
onto a class with `uses`. It brings methods (gears) you want to reuse,
and it may expose those methods through the host’s outside channels.

But the trait is not free-standing. It often has a **socket that only
works when certain wires are connected**: `requires` lists what the host
must supply (fields or methods) before the gearing can run. Without those
wires, the part cannot be used.

A trait is **not** a type — you cannot write `Printable p = …` or
`implements Printable`. It is composition of behavior, not a new kind of
machine you plug a caller cable into.

Host state named in `requires` is accessed via `this`. All `requires`
come before methods in the trait body on purpose: every wire the trait
needs sits next to the gears that use it.

```pys
trait Printable {
    requires string name

    string label() {
        return "Item: " + this.name
    }
}

class Product uses Printable {
    private string name

    public Product(string name) {
        this.name = name
    }
}

Product p = Product("Mug")
print(p.label())
```

Output:

```text
Item: Mug
```


<figure class="concept-diagram" role="img" aria-label="Trait Printable as bolt-on gearing that requires a name wire; Product supplies the wire and gains label">
  <div class="iface-choice">
    <div class="trait-module">
      <div class="cls-head">
        <span class="trait-icon" aria-hidden="true">⚙</span>
        <code>Printable</code>
        <span class="cls-tag">trait · bolt-on gearing</span>
      </div>
      <div class="cls-columns">
        <div class="cls-section">
          <div class="cls-section-label">needs wires</div>
          <div class="trait-wire">
            <span class="trait-wire-jack" aria-hidden="true"></span>
            <code>requires string name</code>
            <span class="cls-note">host must connect</span>
          </div>
        </div>
        <div class="cls-section">
          <div class="cls-section-label">offers gears</div>
          <div class="cls-member is-public">
            <span class="fn-gear" aria-hidden="true">⚙</span>
            <code>label()</code>
            <span class="cls-note">uses this.name</span>
          </div>
        </div>
      </div>
      <p class="iface-empty">not a type — no <code>Printable p = …</code></p>
    </div>

    <div class="iface-plug iface-plug-down" aria-hidden="true">
      <span class="iface-plug-arrow">↓</span>
      <span class="iface-plug-label">uses · mount + wire</span>
    </div>

    <div class="cls-machine">
      <div class="cls-head">
        <span class="cls-icon" aria-hidden="true">⚙⚙</span>
        <code>Product</code>
        <span class="cls-tag">host machine</span>
      </div>
      <div class="cls-columns">
        <div class="cls-section">
          <div class="cls-section-label">supplies the wire</div>
          <div class="cls-member is-private">
            <span class="cls-lock" aria-hidden="true">🔒</span>
            <code>private string name</code>
            <span class="cls-note">→ requires name</span>
          </div>
        </div>
        <div class="cls-section">
          <div class="cls-section-label">mounted gearing</div>
          <div class="cls-member is-public cls-slot-filled">
            <span class="fn-gear" aria-hidden="true">⚙</span>
            <code>label()</code>
            <span class="cls-note">from Printable</span>
          </div>
        </div>
      </div>
      <div class="cls-channels">
        <span class="cls-channels-label">outside channels</span>
        <code>Product(…)</code>
        <code>label()</code>
      </div>
    </div>
  </div>
  <figcaption>
    The trait is a part with its own gears and a hungry socket:
    <code>requires</code> are the wires it needs. The host connects those
    wires (<code>name</code>) and mounts the part (<code>uses</code>).
    Callers talk to <code>Product</code> — never to the trait as a type.
  </figcaption>
</figure>

## Remapping host names

Traits stay reusable when the host uses different field names. Remap only
`requires` entries — the trait’s **methods** keep the same name on every host:

```pys
trait Printable {
    requires string name

    string label() {
        return "Item: " + this.name
    }
}

class CatalogItem uses Printable(name: title) {
    private string title

    public CatalogItem(string title) {
        this.title = title
    }
}

CatalogItem item = CatalogItem("widget")
print(item.label())
```

Output:

```text
Item: widget
```


Same bolt-on gearing, different wire label on the host: the trait still
asks for `name` inside its methods; `uses Printable(name: title)` is the
adapter that connects the host’s `title` drawer to that required wire.

<figure class="concept-diagram" role="img" aria-label="Requires remapping: trait wire name connected to host field title">
  <div class="trait-remap">
    <div class="trait-wire">
      <span class="trait-wire-jack" aria-hidden="true"></span>
      <code>requires name</code>
      <span class="cls-note">inside trait</span>
    </div>
    <div class="iface-plug" aria-hidden="true">
      <span class="iface-plug-arrow">↔</span>
      <span class="iface-plug-label">name: title</span>
    </div>
    <div class="cls-member is-private">
      <span class="cls-lock" aria-hidden="true">🔒</span>
      <code>private string title</code>
      <span class="cls-note">on CatalogItem</span>
    </div>
  </div>
  <figcaption>
    Remap the <em>wire</em>, not the offered gear. <code>label()</code>
    keeps its name on every host.
  </figcaption>
</figure>

> **Sidebar — dependency vs offered surface**
>
> `requires` is what the trait *needs* from the host (remappable). The
> trait’s own methods are what it *offers* (fixed names, not remappable).

## When two traits collide

If two traits define the same method name, the host class **must** override
it. Call `TraitName.method(this)` to pick a side — or combine both:

```pys
trait Loud {
    string greet() {
        return "HEY"
    }
}

trait Soft {
    string greet() {
        return "hi"
    }
}

class Greeter uses Loud, Soft {
    public Greeter() {
    }

    public string greet() {
        return Loud.greet(this) + "/" + Soft.greet(this)
    }
}

Greeter g = Greeter()
print(g.greet())
```

Output:

```text
HEY/hi
```


<figure class="concept-diagram" role="img" aria-label="Greeter host directs greet wires to Loud and Soft trait gears after a name collision">
  <div class="iface-choice">
    <div class="cls-machine">
      <div class="cls-head">
        <span class="cls-icon" aria-hidden="true">⚙⚙</span>
        <code>Greeter</code>
        <span class="cls-tag">host chooses the wiring</span>
      </div>
      <div class="cls-section">
        <div class="cls-section-label">override · directs the wires</div>
        <div class="cls-member is-public cls-slot-filled">
          <span class="fn-gear" aria-hidden="true">⚙</span>
          <code>public string greet()</code>
          <span class="cls-note">you pick the path</span>
        </div>
      </div>
      <div class="cls-channels">
        <span class="cls-channels-label">outside channel</span>
        <code>greet()</code>
      </div>
    </div>

    <div class="trait-collide-wires" aria-hidden="true">
      <div class="trait-collide-wire">
        <span class="iface-plug-label">Loud.greet(this)</span>
        <span class="cls-line-arrow">↓</span>
        <span class="trait-wire-jack"></span>
      </div>
      <div class="trait-collide-wire">
        <span class="iface-plug-label">Soft.greet(this)</span>
        <span class="cls-line-arrow">↓</span>
        <span class="trait-wire-jack"></span>
      </div>
    </div>

    <div class="iface-impls">
      <div class="trait-module">
        <div class="cls-head">
          <span class="trait-icon" aria-hidden="true">⚙</span>
          <code>Loud</code>
          <span class="cls-tag">bolt-on</span>
        </div>
        <div class="cls-member is-public">
          <span class="fn-gear" aria-hidden="true">⚙</span>
          <code>greet()</code>
          <span class="cls-note">→ HEY</span>
        </div>
      </div>
      <div class="trait-module">
        <div class="cls-head">
          <span class="trait-icon" aria-hidden="true">⚙</span>
          <code>Soft</code>
          <span class="cls-tag">bolt-on</span>
        </div>
        <div class="cls-member is-public">
          <span class="fn-gear" aria-hidden="true">⚙</span>
          <code>greet()</code>
          <span class="cls-note">→ hi</span>
        </div>
      </div>
    </div>
  </div>
  <figcaption>
    Both traits offer a gear named <code>greet</code> — collision. The host
    does not get both automatically. Its override
    <strong>directs wires</strong> to the gearing it wants
    (<code>Loud.greet(this)</code>, <code>Soft.greet(this)</code>, or only
    one side). Callers still use a single <code>greet()</code> on
    <code>Greeter</code>.
  </figcaption>
</figure>
Without the override, the transpile fails: two traits both want to own
`greet`. The override is where *you* decide the story — which wires to
connect.

### Exercise

> Add `requires int priceCents` and a method `string priceTag()` that
> returns a short string including the price. Supply the field on
> `Product`.

---

[Previous: Abstract classes](chapter_4_3.md) · [Next: Structs, data, and entity](chapter_4_5.md)
