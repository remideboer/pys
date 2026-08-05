# ADR-021: Result, propagation, panic, and project entrypoints

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-04 |
| Code detail | [CER-025](../evolution/CER-025-result-propagate-panic.md) |
| Requirement | [Propagate and panic](../../requirements/propagate_panic.md) |

## Context

Recoverable failure previously needed ad-hoc sentinel values or an enum plus
manual payload storage. PYS source has no exception surface. The language also
lacked one project-level definition of the program entrypoint, so CLI and IDE
actions could disagree about which file was allowed to terminate the process.

Propagation needs a boundary. Ordinary functions can return a failure to their
caller, but a failure reaching the program entrypoint must become a controlled
runtime outcome. Giving imported top-level code the same privilege would make
behavior depend on import position.

## Decision

1. `result<T,E>` is the recoverable-error type. `ok(value)` and `err(error)`
   are contextually typed constructors. `ok()` is limited to `result<void,E>`;
   `err` always has a payload. Result values never implicitly unwrap.
2. Postfix `expr propagate` yields `T` for `ok(T)` and immediately returns the
   unchanged `err(E)` from a result-returning function or lambda. Error types
   match exactly. Propagation cannot cross a `task` boundary.
3. A result switch uses scoped `ok(value)` / `err(error)` patterns and is
   exhaustive through both patterns or `default`. Literal result cases and
   pattern fallthrough are rejected.
4. The emitter uses private tagged result values and a private propagation
   signal. Generated result boundaries catch only that signal; PYS gains no
   general exception syntax.
5. `[project].main` in `pys.toml` is authoritative for Run, Debug, CLI, and IDE.
   A selected conflicting file is rejected with an actionable Set as
   entrypoint action. Direct-file fallback applies only when no manifest main
   exists; a directory run requires a manifest main.
6. Entrypoint paths must be existing `.pys` files contained by the manifest
   directory after path resolution. Project manifests cannot select an
   interpreter.
7. Only the resolved entrypoint may propagate at top level. An unhandled error
   becomes a panic: deterministic PYS propagation sites on stderr and non-zero
   exit. Imported top-level code never acquires entrypoint semantics.
8. `panic` is a runtime outcome, not a source keyword or callable construct.

## Consequences

- APIs advertise recoverable errors and callers must handle or propagate them.
- The same manifest value drives Run, Debug, Run Main, and source analysis.
- Generated Python uses an internal exception for lowering, but arbitrary
  Python exceptions are neither caught nor exposed as PYS results.
- Panic chains contain PYS file, line, and function sites rather than generated
  implementation frames.
- ADR-001 remains unchanged: manifest parsing is passive and contained; only
  explicit trusted Run/Debug executes generated code or dependencies.
- More syntax, semantic, emitter, refactor, IDE, and teaching surfaces must
  evolve together for each future result-model change.

## Rejected alternatives

### General `try` / `catch` syntax

This would expose backend exceptions, blur recoverable API contracts, and add
a substantially larger control-flow surface. Empirical work on Java exception
anti-patterns (catch-and-ignore, overly broad `catch(Exception)`) and
checked-exception workarounds motivates keeping failure in the type rather
than in an invisible control-flow channel ([6]–[9]).

### Symbol operators `?` / `?=>` and a `try(...)` sugar

| Candidate | Why rejected |
| --- | --- |
| Postfix `?` | Too cheap to type for a deliberate failure edge; mirrors Swift force-unwrap `!` / `try!` misuse documented as avoidable production crashes ([1]–[5]) |
| `?=>` | Grammatical collision with `=>` already used by switch expression arms and lambdas |
| `try(...)` | Semantic collision with exception `try`/`catch` already rejected — wrong transfer when students meet C#/Java |

A full keyword (`propagate`) keeps ceremony intentional, introduces no ambiguous
token, and does not reuse a rejected exception keyword — same “prefer explicit
ceremony over terse footguns” pattern as `requires`, `identity(...)`, and
`atomic`.

Comparative summary:

| Mechanism | Failure visible in signature? | Ceremony | Reflexive-misuse risk |
| --- | --- | --- | --- |
| C#/Java unchecked `try`/`catch` | No | Low at call site | High (ignore / broad catch) |
| Java checked exceptions | `throws` | High; often routed around | High |
| Swift `!` / `try!` | Present but bypassable | Minimal | High |
| PYS `result` + `propagate` | Always in return type | Moderate by design | Low |

### Implicit result-to-success conversion

It hides failure handling at assignments and calls. Explicit `switch` or
`propagate` keeps the control-flow edge visible.

### Compatible or converted error types during propagation

Exact `E` matching avoids implicit error erasure and undocumented conversion
rules. Callers may convert errors explicitly before returning.

### A source-level `panic`

The requirement is specifically the terminal outcome of an unhandled
entrypoint result. A callable panic would add an unrelated escape hatch.

### Selected-file entrypoint precedence

Silently overriding `[project].main` would make editor actions, CLI runs, and
debug sessions execute different programs.

## References

[1] Bugfender, “iOS Crash Debugging: How to Find and Fix App Crashes,” Bugfender Blog. https://bugfender.com/blog/ios-crash-debugging/

[2] G. Miller, “When should you force unwrap optionals in Swift?,” *Hacking with Swift*. https://www.hackingwithswift.com/quick-start/understanding-swift/when-should-you-force-unwrap-optionals-in-swift

[3] Apple Developer Forums, thread 652630 (stable code beginning to crash). https://developer.apple.com/forums/thread/652630

[4] W. McNally, “Force-Unwrapping in Swift is NOT a Bad Thing,” Feb. 19, 2018. https://wolfmcnally.com/82/force-unwrapping-swift-not-bad-thing/

[5] P. Hudson, “Force unwrapping,” *Hacking with Swift*. https://www.hackingwithswift.com/sixty/10/4/force-unwrapping

[6] D. Sena et al., “Understanding the Exception Handling Strategies of Java Libraries: An Empirical Study,” MSR 2016, doi: 10.1145/2901739.2901757

[7] A. Nakshatri et al., “Analysis of Exception Handling Patterns in Java Projects: An Empirical Study,” MSR 2016, doi: 10.1109/MSR.2016.062

[8] T. Nguyen et al., “Studying the Prevalence of Exception Handling Anti-Patterns,” ICPC 2017, doi: 10.1109/ICPC.2017.36

[9] J. Bloch, *Effective Java*, 3rd ed. Addison-Wesley, 2018.
