## PYS Language Specification — `result<T, E>` and the `propagate` Operator

> **Absorbed into permanent docs.** Canonical decisions + references [1]–[9]:
> [ADR-021](../docs/adr/ADR-021-result-propagate-panic.md). This file is a
> historical draft only.

> Status: resolved by [ADR-021](../docs/adr/ADR-021-result-propagate-panic.md).
> The exact-error, result-pattern, and runtime-panic choices below are the
> accepted contract.

### 1. Overview

`result<T, E>` is a built-in, lowercase generic type representing the outcome of an operation that can either succeed with a value of type `T` or fail with an error of type `E`. It is the sole mechanism PYS provides for *recoverable* errors — errors the caller can reasonably be expected to react to (a malformed file, a failed network request, invalid user input). PYS deliberately has no `try`/`catch` construct; this specification, together with the earlier evaluation of that decision, replaces it.

Consistent with `int`, `list<T>`, and `lambda<T -> R>` being lowercase built-in types, `result<T,E>`'s constructors are also lowercase — `ok(...)` and `error(...)` — rather than the PascalCase `Ok`/`Err` used in the earlier informal examples. This keeps the signal consistent: a capitalized identifier in PYS always denotes a user-defined type or constructor; a lowercase one always denotes a language-level construct or literal, matching `true`/`false`/`null`.

### 2. Grammar

```ebnf
(* ------------------------- Result type ------------------------- *)

result_type       = "result" , "<" , result_value_type , "," , type_expr , ">" ;
result_value_type = type_expr | "void" ;
(* The first type is the success type and may be void. The second is a
   concrete error type and may not be void. *)

(* Amendment to type_expr *)
type_expr         = primitive_type
                 | collection_type , [ type_args ]
                 | named_type , [ type_args ]
                 | array_type
                 | lambda_type
                 | result_type ;

(* ------------------------- Result construction ------------------------- *)

result_ctor_call  = ( "ok" | "error" ) , "(" , [ expression ] , ")" ;
(* ok(expr) and error(expr) are built-in constructors, not user-callable
   identifiers — analogous to true/false/null, not to a class constructor.
   ok() with no argument is valid only when the success type is inferred
   as void. *)

(* Amendment to primary *)
primary           = identifier
                 | "this"
                 | "super"
                 | literal
                 | array_literal
                 | "(" , expression , ")"
                 | constructor_call
                 | switch_expr
                 | lambda_expr
                 | result_ctor_call ;

(* ------------------------- Result matching ------------------------- *)

result_pattern    = "ok" , "(" , [ identifier ] , ")"
                  | "error" , "(" , identifier , ")" ;

(* Amendment to case_label *)
case_label        = result_pattern
                  | identifier
                  | identifier , "." , identifier
                  | integer | string_lit | char_lit | boolean | null_lit ;

(* ------------------------- Propagation ------------------------- *)

(* Amendment to postfix_expr *)
postfix_expr      = primary ,
                    { "." , identifier , [ call_suffix ]
                    | "[" , slice_or_index , "]"
                    | call_suffix
                    | "++"
                    | "--"
                    | "propagate" } ;
```

### 3. Static semantics

1. **`propagate` is only legal on an expression of type `result<T, E>`.** Using it on any other type is a compile-time error.
2. **`propagate` is only legal inside a function whose own return type is `result<T', E>`**, where the error type `E` matches exactly. Using it inside a function that does not return `result<...>` is a compile-time error — there is nowhere for the error to propagate *to*.
3. **Evaluation**: `expr propagate` evaluates `expr`. If the result is `error(e)`, the enclosing function immediately returns `error(e)` — no further statements in that function execute. If the result is `ok(v)`, the expression evaluates to `v`, and execution continues normally.
4. **`ok`/`error` are not user-declarable identifiers** — redeclaring either as a variable, function, or type name is a compile-time error, the same restriction already applied to other language-reserved words.
5. **No implicit conversion between `result<T,E>` and `T`.** A `result<T,E>` value must be explicitly unwrapped — via `propagate`, or via exhaustive `switch` patterns `case ok(v)` / `case error(e)` — before its success value can be used as a plain `T`. This is the structural mechanism preventing the "forgot to handle the error" class of bug this construct exists to eliminate.
6. **Error types match exactly.** There is no implicit compatibility or
   conversion rule for `E`; an author converts an error explicitly before
   returning it.

### 4. Worked example

```pys
function result<Config, string> loadConfig(string path) {
    string contents = readFile(path) propagate
    Config parsed = parseToml(contents) propagate
    validate(parsed) propagate
    return ok(parsed)
}
```

Each `propagate` reads, left to right: *evaluate this; if it failed, stop and hand the failure straight to my own caller; otherwise, give me the value and let me continue.* No line hides the possibility of failure — every point where the function can stop early is marked at exactly the place where the failure-prone call happens, not buried in an unrelated `catch` block elsewhere in the file.

### 5. Rationale for `propagate` over a symbol operator

The candidates considered — `?`, `?=>`, `try(...)` — were rejected for three independent reasons, summarized here for the specification record:

- **`?`** is too cheap to type to serve its intended purpose: forcing deliberate engagement with the possibility of failure at each use site. Swift's structurally similar force-unwrap operator `!` is widely documented as a source of avoidable production crashes precisely because its low keystroke cost invites reflexive use to silence a compiler complaint rather than considered handling of the absent case [1]–[4]; Swift's own developer-facing material explicitly refers to `!` as "the crash operator" for this reason [5]. `?` in a propagation role risks the identical failure mode.
- **`?=>`** creates a grammatical collision with the `=>` token already used for `switch_expr_arm` and `lambda_expr` in this grammar, risking a different kind of error: not under-consideration of failure handling, but genuine ambiguity about what the token sequence means at a glance.
- **`try(...)`** creates a semantic collision with the exception-based `try`/`catch` mechanism explicitly rejected earlier in this specification. Reusing the keyword for an unrelated mechanism (`result` propagation, not stack-unwinding) risks exactly the wrong transfer effect when students later encounter genuine `try`/`catch` in C# or Java — they would carry an incorrect prior association into a language where the keyword means something structurally different.

A full keyword (`propagate`) avoids all three problems: it costs enough keystrokes to discourage reflexive use, it introduces no new token that could be confused with existing grammar, and it does not borrow a keyword already carrying a different, previously-rejected meaning. This is consistent with the general design pattern already established in this specification (`requires`, `identity(...)`, `shared`, `atomic`): where PYS could offer a terse, easily-misused shorthand, it instead asks for a small amount of extra, self-explanatory ceremony.

### 6. Comparative summary

| Mechanism | Visibility of failure in signature | Ceremony cost | Risk of reflexive misuse | Transfer relevance to C#/Java |
|---|---|---|---|---|
| C#/Java `try`/`catch` (unchecked) | None — nothing in the signature indicates a call can fail [6]–[8] | Low at call site, cost deferred to whoever eventually catches (or fails to) | High — widely documented anti-patterns including catch-and-ignore and overly broad `catch(Exception e)` [2], [3], [6] | Direct — this is what students will actually use next, hence covered explicitly in the planned "From PYS to C#/Java" chapter |
| Java checked exceptions | Present in signature (`throws`) | High, but empirical studies show developers route around it rather than engage with it | Documented tendency for developers to ignore or blanket-catch checked exceptions rather than handle them meaningfully [3], [7], [8] | Present in Java, absent in C# — itself a documented source of cross-language confusion [8] |
| Swift `!` / `try!` | Present in type (`Optional`/`throws`), but bypassable with one character | Minimal — a single keystroke | High — extensively documented as a leading cause of avoidable runtime crashes [1]–[5] | Not directly applicable (PYS targets C#/Java) |
| PYS `result<T,E>` + `propagate` | Always present in the return type — cannot be silently ignored per §3.5 | Moderate, deliberately so | Low — the explicit keyword and the type-level requirement both work against reflexive use | Not directly present in C#/Java, but the covered chapter maps `result<T,E>` to `try`/`catch` explicitly, teaching the contrast rather than assuming equivalence |

### 7. Resolved design items

1. Propagation syntax: postfix `propagate`.
2. Panic modeling: runtime outcome when an `error` leaves the resolved
   entrypoint; no source-level panic construct.
3. Result matching: exhaustive `case ok(value)` / `case error(message)` patterns,
   or a `default` arm.
4. Propagated error compatibility: exact `E` equality.

## References

[1] Bugfender, "iOS Crash Debugging: How to Find and Fix App Crashes," Bugfender Blog. [Online]. Available: https://bugfender.com/blog/ios-crash-debugging/. [Accessed: Aug. 4, 2026].

[2] G. Miller, "When should you force unwrap optionals in Swift?," *Understanding Swift* (Hacking with Swift). [Online]. Available: https://www.hackingwithswift.com/quick-start/understanding-swift/when-should-you-force-unwrap-optionals-in-swift. [Accessed: Aug. 4, 2026].

[3] "Code that has been consistently stable for a long time now has begun crashing for unknown reasons," Apple Developer Forums, thread 652630. [Online]. Available: https://developer.apple.com/forums/thread/652630. [Accessed: Aug. 4, 2026].

[4] W. McNally, "Force-Unwrapping in Swift is NOT a Bad Thing," wolfmcnally.com, Feb. 19, 2018. [Online]. Available: https://wolfmcnally.com/82/force-unwrapping-swift-not-bad-thing/. [Accessed: Aug. 4, 2026].

[5] P. Hudson, "Force unwrapping," *Hacking with Swift*. [Online]. Available: https://www.hackingwithswift.com/sixty/10/4/force-unwrapping. [Accessed: Aug. 4, 2026].

[6] D. Sena, R. Coelho, U. Kulesza, and R. Bonifácio, "Understanding the Exception Handling Strategies of Java Libraries: An Empirical Study," in *Proc. IEEE/ACM 13th Working Conf. Mining Software Repositories (MSR)*, 2016, pp. 212–222, doi: 10.1145/2901739.2901757.

[7] A. Nakshatri, M. Hegde, and S. Thandra, "Analysis of Exception Handling Patterns in Java Projects: An Empirical Study," in *Proc. IEEE/ACM 13th Working Conf. Mining Software Repositories (MSR)*, 2016, pp. 500–503, doi: 10.1109/MSR.2016.062.

[8] T. Nguyen, H. Shang, and (et al.), "Studying the Prevalence of Exception Handling Anti-Patterns," in *Proc. IEEE 25th Int. Conf. Program Comprehension (ICPC)*, 2017, doi: 10.1109/ICPC.2017.36.

[9] J. Bloch, *Effective Java*, 3rd ed. Boston, MA, USA: Addison-Wesley, 2018. (Referenced as the best-practices baseline against which checked-exception usage was empirically compared in [7].)

## PYS Language Specification — Entrypoint Resolution, Top-Level `propagate`, and `panic`

### 1. Overview

This section formalizes Option B from the prior discussion: `propagate` retains exactly one meaning across every scope in PYS — *return the failure to whoever invoked this scope*. At the top level of an entrypoint file, "whoever invoked this scope" is the runtime itself, and returning a failure to the runtime is defined as a `panic`: the program halts, the error is reported, and the process exits with a non-zero status. This resolves the earlier open question about `panic` as a byproduct of a single, uniformly-applied rule, rather than as a separately invented mechanism.

Because this behavior must not silently apply to every file that happens to contain top-level code — only to the one file actually serving as the program's starting point — this section also formalizes how a PYS project designates its entrypoint.

### 2. Semantics of top-level `propagate`

1. A file's top-level statement sequence is treated as the body of an implicit function with return type `result<void, E>`, where `E` is inferred from the error types of any `result<T,E>` expressions the top level applies `propagate` to. If multiple such error types appear, they must match exactly or the file fails to compile.
2. `propagate` at the top level behaves exactly as specified for function bodies: on `error(e)`, execution of the top-level sequence stops immediately, exactly as a `return error(e)` would inside an ordinary function.
3. **This implicit wrapping, and its associated `propagate` behavior, applies only to a file resolved as the project's entrypoint** (§4). A file containing top-level code that is instead reached via `import` is not wrapped this way — see §5.

### 3. `panic`

`panic` is the observable outcome, not a separate keyword construct: when an `error(e)` reaches the outermost implicit scope of the entrypoint file (i.e., propagates past the last statement with nowhere further to go), the runtime:

1. Halts further execution immediately — no statements after the point of failure run.
2. Prints a diagnostic to standard error containing the error value `e` and, where available, the propagation chain (each `propagate` site that passed the error upward), analogous to a stack trace.
3. Terminates the process with a non-zero exit code.

This is PYS's sole mechanism for unrecoverable termination. There is no separate `panic(...)` statement to author manually in this revision — a deliberate choice, since introducing one would create two independent ways to reach the same outcome, reintroducing the kind of redundancy already rejected elsewhere in this specification (e.g. the rejected `atomic shared` combination). If a manual, explicit termination construct is later found necessary (e.g. for asserting an invariant that isn't naturally expressed as a `result<T,E>`), it should be proposed and evaluated as its own addition, not folded silently into this mechanism.

### 4. Entrypoint resolution

Two resolution paths, in order of precedence:

1. **Explicit — `pys.toml` `main` field.** The project manifest may declare which file is the entrypoint:

   ```toml
   [project]
   main = "src/app.pys"
   ```

   This is the authoritative source when present, and is the field a tooling extension's "Set as entrypoint" action writes to — giving the IDE and the compiler a single, shared source of truth instead of each inferring it independently. This directly addresses the ambiguity Python projects are prone to, where "what actually runs" depends on how a file happens to be invoked (`python app.py` vs. `python -m package.app` vs. an entry inside `pyproject.toml`) rather than on one declared fact.
2. **Implicit — direct invocation.** In the absence of a `main` field (e.g. a single-file script with no project manifest at all, matching the earliest "Hello World" teaching examples), the entrypoint is the file passed directly to the compiler/runtime invocation (`pys run app.pys`). A file reached only via `import`, even transitively from the directly-invoked file, is never treated as the entrypoint by this path.

If neither is present — no `pys.toml` `main` field and no file directly named on invocation (e.g. invoking a bare directory) — this is a compile/run-time configuration error, not a silent fallback to some guessed file.

### 5. Import safety — why this cannot apply to every file with top-level code

If every file's top-level code implicitly panicked on `error(...)`, merely importing a module for its declarations could crash the importing program before it ever got a chance to handle anything — a well-documented nuisance in Python, where module-level code executes unconditionally on import and is commonly worked around with `if __name__ == "__main__":` guards [reference: Python's own documentation recommends this idiom specifically to prevent import-time side effects]. PYS avoids needing an equivalent workaround by making the distinction structural rather than conventional:

1. Only the file resolved as the entrypoint (§4) receives the implicit `result<void,E>` wrapping and associated panic-on-`error` behavior described in §2–3.
2. A non-entrypoint file's top-level code executes on import exactly as today's grammar already implies, with no additional implicit error-propagation semantics layered on top. If such a file's top-level code contains a `result<T,E>`-typed expression, `propagate` is illegal there under the existing rule (§3.2 of the prior specification: `propagate` requires an enclosing function or entrypoint scope) — the author must handle the result explicitly via `switch`/`ok`/`error`, exactly as inside any ordinary non-entrypoint function today.

This keeps the guarantee precise: **"top-level code can fail loudly and stop the program" is a property of the entrypoint, not a property of top-level code in general** — avoiding the Python pitfall by construction rather than by convention.

### 6. Worked example

```toml
# pys.toml
[project]
main = "src/app.pys"
```

```pys
# src/config_loader.pys — NOT the entrypoint, imported by app.pys
import config_loader from "config_loader"

function result<Config, string> loadConfig(string path) {
    string contents = readFile(path) propagate
    Config parsed = parseToml(contents) propagate
    return ok(parsed)
}
```

```pys
# src/app.pys — the entrypoint, per pys.toml
import loadConfig from "config_loader"

# Top-level propagate legal here ONLY because this file is the
# resolved entrypoint. A failure here halts the program (panic),
# per §2–3 — no wrapping function needed, and no separate keyword.
Config cfg = loadConfig("settings.toml") propagate
print("Loaded config for: " + cfg.name)
```

If `settings.toml` is missing, `loadConfig` returns `error("...")`, `propagate` at the top level of `app.pys` halts the script, prints the error and the propagation chain (`loadConfig` → top level), and exits non-zero — the exact behavior an uncaught exception would produce in C#/Java, reached here through the same single mechanism used throughout the rest of the language, rather than a second, separately-specified crash pathway.