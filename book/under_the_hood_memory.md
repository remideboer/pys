# 10.2. Processes, calls, and memory

> **Optional background.** This chapter gives you a useful mental model, not a
> promise about the exact byte address of every PYS value. PYS currently emits
> Python, so Python and the operating system decide many physical storage
> details.

## A process sees a private address space

RAM is physical storage made from addressable bytes. A modern operating system
normally gives each process a **virtual address space**: addresses that look
private and continuous to that process while the OS and hardware map them to
physical memory.

This isolation is why two programs can use the same-looking virtual address
without sharing a variable. Normal code in one process cannot accidentally
read an unrelated process's memory.

Operating systems and runtimes commonly organize process memory into areas
with roles such as:

- executable machine code;
- static or global runtime data;
- dynamically managed memory, commonly called the **heap**;
- one **call stack** per thread.

Real layouts vary by operating system, CPU, runtime, and optimization. Treat
these names as a map for reasoning, not as a PYS storage guarantee.

## Function calls form a stack

When one function calls another, the runtime must remember where to return,
which arguments were passed, and which local names belong to that call. This
record is a **stack frame**. A later call sits above its caller and finishes
first: last in, first out.

```pys
function int addOne(int number) {
    int result = number + 1
    return result
}

function int doubledAfterAddingOne(int number) {
    int changed = addOne(number)
    return changed * 2
}

print(doubledAfterAddingOne(5))
```

Output:

```text
12
```

Conceptually, the active calls are:

```text
top-level entrypoint
└─ doubledAfterAddingOne(number = 5)
   └─ addOne(number = 5)
```

`addOne` returns first, then `doubledAfterAddingOne`, then control returns to
the entrypoint. Debugger stack views show this same relationship, even though
the emitted Python runtime controls the concrete frame representation.

Uncontrolled recursion keeps adding frames until the runtime refuses another
one. That failure is called a **stack overflow** (or, in Python, may first
appear as a recursion-depth error).

## The heap and reachability

Data often needs to outlive the function that created it or have a size that
is known only while the program runs. Runtimes commonly manage such data in
heap storage.

Python—and therefore the current PYS backend—uses automatic memory
management. When an object is no longer reachable, the runtime may reclaim
its storage. You do not write `free(...)` in PYS.

Garbage collection prevents common manual-memory mistakes such as using an
object after freeing it, but it does not make memory unlimited. A program can
still retain too much reachable data and run out of memory.

## Language meaning is not physical location

It is tempting to teach “local means stack” and “object means heap” as an
absolute rule. That shortcut breaks under optimization, managed runtimes,
closures, and captured variables. PYS specifies how values behave; it does
not currently promise where each value is physically stored.

For example, class variables share an object reference, while structs have
copy-on-assignment value behavior:

```pys
class Counter {
    private int value

    public Counter(int value) {
        this.value = value
    }

    public increment() {
        this.value = this.value + 1
    }

    public int current() {
        return this.value
    }
}

struct Point {
    int x
    int y
}

Counter firstCounter = Counter(1)
Counter secondCounter = firstCounter
secondCounter.increment()
print(firstCounter.current())

Point firstPoint = Point(1, 2)
Point secondPoint = firstPoint
secondPoint.x = 9
print(firstPoint.x)
print(secondPoint.x)
```

Output:

```text
2
1
9
```

Both counter names reach the same class instance, so mutation through one name
is visible through the other. Assigning the struct creates an independent
value, so changing `secondPoint` leaves `firstPoint` unchanged.

This is a **semantic** distinction. The Python emitter may represent both with
Python objects internally while preserving PYS's different assignment rules.
Likewise:

- `data` is an immutable value object with all-fields equality;
- `entity` is a reference-like domain object whose declared identity fields
  determine equality;
- `class` has ordinary object identity and mutable encapsulated state;
- `struct` is an identity-free copied value.

Choose among them for those language meanings, not because you are guessing a
stack or heap address.

## A process can contain several threads

A process owns an address space. A **thread** is one flow of execution inside
that process. Each thread has its own instruction position and call stack, but
threads in the same process can reach shared runtime data.

That shared reachability creates races: two flows can read and update the same
state in an unsafe order. PYS makes the intent visible:

- `tasks` / `task` describe concurrent work;
- `shared` says state is deliberately reachable from concurrent work;
- `atomic` provides indivisible operations for supported primitive counters
  and flags;
- `await` expresses dependencies between tasks.

The current backend may implement these constructs with Python runtime
facilities, but the PYS contract is higher-level. Code should rely on PYS's
`shared`, `atomic`, and `await` rules rather than on backend accidents such as
one particular Python implementation's scheduling.

## Failure modes now have a mechanical meaning

- **Stack overflow:** too many unfinished nested calls.
- **Out of memory:** the process cannot obtain more memory.
- **Race condition:** concurrent behavior depends on an unsafe ordering.
- **Panic:** a PYS error outcome reached the entrypoint; this is a language
  boundary outcome, not a memory failure.

Keeping these categories separate makes diagnostics easier to understand. A
panic is not automatically a crash caused by corrupt memory, and a stack
overflow is not a recoverable `result<T,E>` business error.

## Check your understanding

> Without running code, explain why `secondCounter.increment()` changes what
> `firstCounter.current()` returns, while changing `secondPoint.x` does not
> change `firstPoint.x`. Then name the resource exhausted by uncontrolled
> recursion and the concurrency problem prevented by a suitable atomic
> update.

---

[Previous: From source file to running process](under_the_hood_entrypoint.md) · [Next: Exercise — Contact book](exercises_contact_book.md)
