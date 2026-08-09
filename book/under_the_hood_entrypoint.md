# 11.1. From source file to running process

> **Optional background.** You do not need this chapter to write PYS. Read it
> when you want to understand what Run actually starts and why a project needs
> one unambiguous entrypoint.

## A file is not yet a running program

Source code on disk is passive text. When you run a program, the operating
system creates a **process**: a running environment with memory, resources, and
an exit status. The CPU must receive one initial machine-code address. It
cannot inspect all your source files and guess which line looks most important.

There are several layers between a PYS file and that first CPU instruction:

1. The operating system starts the Python executable at Python's native
   machine-code entrypoint.
2. The PYS toolchain parses your source and emits Python.
3. Python executes the generated entrypoint module from its first statement.
4. Imported modules provide declarations and initialization, but they do not
   become the application's entrypoint.

<figure class="concept-diagram" role="img" aria-label="The operating system starts Python, which runs the generated PYS entrypoint and loads imported modules">
  <div class="diagram-flow">
    <div class="diagram-box"><strong>Operating system</strong><span>creates a process</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>Python runtime</strong><span>starts at native machine code</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>PYS entrypoint</strong><span>generated module runs top to bottom</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>Imported modules</strong><span>supply declarations and initialization</span></div>
  </div>
  <figcaption>The OS-level and PYS-level entrypoints are different layers.</figcaption>
</figure>

This distinction matters: the OS-level entrypoint belongs to the Python
executable, while the **PYS project entrypoint** answers which `.pys` file is
the application boundary.

## The smallest PYS entrypoint

For a single-file program, the file named in the Run command is the entrypoint:

```pys
print("program started")
```

Run it as `hello.pys`:

```shell
python -m transpiler run hello.pys
```

Output:

```text
program started
```

PYS does not require a `main()` function. Top-level statements in the resolved
entrypoint file are the program body. The word **main** is still often used as
a role—“the main file”—not as required PYS function syntax.

## A project records the choice

Once a project contains several files, selecting one explicitly prevents Run,
Debug, and the editor from making different guesses:

```toml
[project]
main = "src/app.pys"
# Optional: target = "javascript"  # default is python (Run Project / bare run)

[source_roots]
main = "src"
test = "tests"
```

With this manifest, `src/app.pys` is authoritative. **Run Project** (right-click
`pys.toml`) executes that file. Trying to run another file as though it were the
application is rejected; the editor can update the choice with **Set as
entrypoint**.

The configured path must:

- name an existing `.pys` file;
- stay inside the project directory, including after path resolution;
- be the same choice used by Run and Debug.

These rules make the starting boundary a project fact instead of an editor
preference.

## Entry files and imported files have different jobs

Suppose `app.pys` imports a function from `prices.pys`. Both files may contain
code, but only `app.pys` is where the application hands its final outcome to
the runtime.

That is why top-level `propagate` is legal only in the resolved entrypoint. In
an imported file, put recoverable work in a `result<T,E>` function and let its
caller handle or propagate the result. Importing a helper must not silently
turn that helper into a second application boundary.

## What an exit status communicates

A process reports a small integer when it finishes:

- `0` conventionally means successful completion;
- a non-zero value means the program did not complete successfully.

When an `error` reaches the PYS entrypoint through `propagate`, the runtime
reports a panic on stderr and exits non-zero. This is not a second entrypoint
or a `panic(...)` statement. It is the terminal outcome at the existing
application boundary.

Shells, test runners, IDEs, and deployment systems use the exit status even
when no person is watching the terminal. Program output explains what
happened; the status tells another program whether the run succeeded.

## Why some environments appear to have no entrypoint

A browser is already a running process before it loads your JavaScript. It
owns the event loop and calls your handlers after clicks, timers, and network
responses. A plugin, game script, or spreadsheet macro is similar: a **host**
already controls execution.

<figure class="concept-diagram" role="img" aria-label="A browser host loads a script and its event loop invokes registered handlers">
  <div class="diagram-flow">
    <div class="diagram-box"><strong>Browser host</strong><span>process and event loop already running</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>Load script</strong><span>evaluate once and register callbacks</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>Event loop</strong><span>wait for work</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>Your handlers</strong><span>click, timer, or network response</span></div>
  </div>
  <figcaption>Hosted code joins control flow that already exists.</figcaption>
</figure>

Those environments still have a starting boundary, but it belongs partly to
the host. A standalone C, C#, Java, Dart, or PYS application makes its own
application boundary more visible.

The useful question is therefore not “does this language have `main`?” Ask:

> Who creates the process, and who chooses the first piece of my application
> code that runs?

## Check your understanding

> A project contains `src/app.pys` and `src/report.pys`; `pys.toml` selects
> `src/app.pys`. Explain why opening `report.pys` in the editor does not make
> it the entrypoint. Then name the successful and unsuccessful exit-status
> categories.

---

[Previous: What has no direct twin](chapter_8_4_no_direct_twin.md) · [Next: Processes, calls, and memory](under_the_hood_memory.md)
