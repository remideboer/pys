## PYS Language Specification — Abstract Classes

### 1. EBNF extension

```ebnf
class_decl        = [ top_visibility ] , [ "sealed" | "abstract" ] , "class" , identifier ,
                    [ type_params ] ,
                    [ ( "inherits" | "super" ) , identifier ] ,
                    [ "uses" , identifier , { "," , identifier } ] ,
                    [ "implements" , identifier , { "," , identifier } ] ,
                    class_body ;
(* "sealed" and "abstract" are mutually exclusive on the same class. *)

class_member      = field_decl | method_decl | abstract_method_decl | constructor_decl ;

abstract_method_decl = member_access , "abstract" , return_type , identifier ,
                       "(" , [ parameter_list ] , ")" ;
(* No block. Only legal inside a class declared "abstract". *)
```

### 2. Static semantics

1. An `abstract_method_decl` may only appear inside a `class_decl` carrying the `abstract` modifier.
2. A non-abstract class that `inherits` an abstract class must implement every `abstract_method_decl` inherited and not yet implemented by an intermediate ancestor, or the compiler rejects it.
3. `abstract class` cannot appear in `constructor_call` — no direct instantiation.
4. An `abstract class` may declare a `constructor_decl`; it runs via `super(...)` from a concrete subclass, exactly as in a normal `inherits` chain.
5. Fields and concrete methods declared in the abstract class follow ordinary `member_access` visibility and are inherited normally — this is the mechanism distinguishing it from `interface_decl`, which permits neither.

### 3. Worked example — stripped-down `AbstractList<T>`

```pys
# AbstractList captures everything list implementations share:
# a running element count (size), a mutation counter (modCount, used
# elsewhere for fail-fast iteration), and two behaviors that are
# identical regardless of storage strategy (isEmpty, contains).
# What differs per storage strategy — how an element at index i is
# located, and how a new element is appended — is left abstract.
abstract class AbstractList<T> {
    protected int size
    protected int modCount

    AbstractList() {
        this.size = 0
        this.modCount = 0
    }

    # Concrete: works purely in terms of size, needs no knowledge
    # of how elements are actually stored.
    public bool isEmpty() {
        return this.size == 0
    }

    # Concrete: expressed in terms of the abstract get(), so it works
    # correctly for ANY subclass without being rewritten per subclass.
    public bool contains(T item) {
        loop (int i = 0, i < this.size, i++) {
            if (this.get(i) == item) {
                return true
            }
        }
        return false
    }

    # Abstract: array indexing and node-walking are fundamentally
    # different operations — no shared body is possible.
    public abstract T get(int index)
    public abstract void add(T item)
}

# Storage strategy 1: contiguous array — O(1) get, amortized O(1) add.
class ArrayListPys<T> inherits AbstractList<T> {
    private T[] items

    ArrayListPys() {
        super()
        this.items = []
    }

    public T get(int index) {
        return this.items[index]
    }

    public void add(T item) {
        this.items = this.items + [item]
        this.size++
        this.modCount++
    }
}

# Storage strategy 2: linked nodes — O(n) get, O(1) add at head.
struct Node<T> {
    T value
    Node<T> next
}

class LinkedListPys<T> inherits AbstractList<T> {
    private Node<T> head

    LinkedListPys() {
        super()
        this.head = null
    }

    public T get(int index) {
        Node<T> cur = this.head
        loop (int i = 0, i < index, i++) {
            cur = cur.next
        }
        return cur.value
    }

    public void add(T item) {
        this.head = Node(value = item, next = this.head)
        this.size++
        this.modCount++
    }
}
```

### 4. Didactic notes

**Why abstract class, not interface**: `isEmpty()` and `contains()` are not restatable per subclass — restating them in `ArrayListPys` and `LinkedListPys` would be literal code duplication of *identical* logic. An interface has no mechanism to share a body; only `size`/`get()` are exposed, forcing every implementer to reimplement `contains()` from scratch, with the accompanying risk that one implementation silently diverges (e.g. an off-by-one).

**Why abstract class, not trait**: `size` and `modCount` are not borrowed by unrelated classes — they are *intrinsic, owned* state of "being a list". `ArrayListPys` and `LinkedListPys` are ontologically `AbstractList`s: substitutable wherever an `AbstractList<T>` is expected. A trait's `uses` relation expresses "I happen to also do X" (horizontal, structural borrowing between otherwise-unrelated types, e.g. `Product uses Printable`); `inherits` here expresses "I fundamentally am a kind of X" (vertical, taxonomic, with polymorphic substitutability as the actual requirement — code calling `contains()` on an `AbstractList<T>` reference must work identically no matter which concrete subclass is behind it).

**The reuse-vs-polymorphism distinction, made concrete**: 
- If the only goal were code reuse, a free function `bool contains<T>(AbstractList<T> l, T item)` would suffice — no inheritance needed.
- Inheritance is justified here because `contains()` must dispatch to *the calling instance's own* `get()` — that's runtime polymorphism, not mere reuse. This is the litmus test worth giving students: ask "does the shared method need to call back into a method that varies per subclass?" If yes → abstract class is warranted (template method pattern). If the shared logic never needs to vary → prefer a trait or a plain utility function; inheritance would be over-engineering.

**Summary table for the four constructs, now complete**:

| Construct | Owns state | Provides bodies | Requires subtype relation | Typical use |
|---|---|---|---|---|
| Interface | No | No | Yes (nominal contract) | Polymorphism via pure contract |
| Trait | No (borrows host's) | Yes | No | Horizontal behavior reuse across unrelated types |
| Abstract class | Yes | Partial (mix) | Yes (taxonomic `is-a`) | Vertical reuse + enforced polymorphic variation point |
| Concrete class | Yes | Yes (all) | — | Instantiable end product |