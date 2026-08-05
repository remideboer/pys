## PYS Language Specification — Optional Statement Terminator, Revised `loop` Header Separator, Comma-Delimited Enums, and Multi-Label/Block `switch` Arms

**Status:** Implemented — [ADR-022](../docs/adr/ADR-022-optional-terminators-grammar.md) / [CER-026](../docs/evolution/CER-026-optional-terminators-grammar.md).

### 1. Overview

Four related grammar changes, motivated by the same underlying concern: PYS currently relies entirely on the newline as the only statement boundary, which breaks down the moment several short, related declarations are written on one line — a common and often legitimate pattern (e.g. loop counters, small groups of related constants) that PYS's current grammar cannot express without forcing one declaration per line regardless of how tightly related they are.

1. An optional statement terminator `;` is introduced, required only when two or more statements share a single physical line, so a reader is never left inferring a statement boundary from spacing alone.
2. `c_for_loop`'s header separator changes from `,` to `;`, for internal consistency with (1) and for direct alignment with C#/Java's identical for-loop syntax.
3. `enum` member lists become comma-delimited, with an optional trailing comma, decoupling member layout from any particular line-wrapping convention.
4. `switch` statement arms gain comma-separated multiple case labels (already present in `switch_expr_arm` but missing from `switch_stmt_arm`) and may use either a bare statement sequence or an explicit `block` as the arm body.

### 2. Grammar

```ebnf
(* ------------------------- Statement termination ------------------------- *)

statement_terminator = ";" ;

statement         = ( declaration_stmt
                    | assignment
                    | expression_stmt
                    | if_stmt
                    | unless_stmt
                    | switch_stmt
                    | loop_stmt
                    | tasks_stmt
                    | await_stmt
                    | return_stmt
                    | print_stmt
                    | "break"
                    | "continue"
                    | "pass" ) ,
                   [ statement_terminator ] ;
(* A newline still always ends a statement, exactly as before this change.
   ";" is never required when a statement is alone on its own line — it
   remains fully optional there. It becomes MANDATORY only between two
   statements that share one physical source line, where it is the sole
   marker of the boundary between them. A trailing ";" after the last
   statement on a line is always permitted, whether or not further
   statements follow. *)

(* ------------------------- C-style for loop ------------------------- *)

c_for_loop        = "loop" , "(" , for_init , ";" , for_cond , ";" , for_step , ")" , block ;
(* Separator changed from "," to ";". Init, condition, and step must
   still refer to the same loop variable, which remains immutable inside
   the loop body — unchanged from the existing rule. *)

(* ------------------------- Enums ------------------------- *)

enum_decl         = [ top_visibility ] , "enum" , identifier ,
                    "{" , enum_member_list , "}" ;

enum_member_list  = enum_member , { "," , enum_member } , [ "," ] ;
(* Comma is now the sole separator between members. Newlines carry no
   grammatical meaning inside the member list: all members on one line,
   several per line, or one per line are equally valid, since layout no
   longer affects parsing. A trailing comma after the final member is
   permitted and has no effect other than being a valid position to stop
   the list. *)

enum_member       = identifier , [ "=" , ( integer | string_literal ) ] ;
(* Unchanged. All-or-nothing explicit values, homogeneous and unique,
   per existing semantics. *)

(* ------------------------- Switch statement ------------------------- *)

switch_stmt       = "switch" , "(" , expression , ")" ,
                    "{" , switch_stmt_arm , { switch_stmt_arm } , "}" ;

switch_stmt_arm   = "case" , case_label , { "," , case_label } , ":" , switch_stmt_body
                   | "default" , ":" , switch_stmt_body ;
(* Multiple comma-separated case_labels are now legal on a statement arm,
   matching switch_expr_arm's existing form. *)

switch_stmt_body  = block
                   | { statement } ;
(* Two equivalent forms for an arm's body:
     - block: an explicit "{" ... "}" grouping, useful for visually
       bundling several statements under one case, and the natural place
       to use the new same-line ";" terminator for compactness.
     - a bare statement sequence: zero or more statements, each on its
       own line (or sharing lines via ";" per the statement_terminator
       rule), continuing until the next "case", "default", or the
       switch's closing "}".
   No fall-through occurs at the end of either form unless the arm's
   last statement is "continue", per existing switch semantics. *)
```

### 3. Static semantics

1. **Same-line statement boundary rule.** If the parser detects two statements on one physical source line with no `;` between them, this is a compile-time error, not a warning or a silently-resolved ambiguity:
   ```
   Error: Two statements on the same line must be separated by ';'.
   Found 'int y = 20' immediately after 'int x = 10' with no separator.
   Insert ';' between them, or put each statement on its own line.
   ```
2. **`;` is purely a same-line disambiguator, never a requirement of a well-formed program otherwise.** A file using `;` nowhere at all remains entirely valid, provided no line contains more than one statement.
3. **Scope of a block-form `switch_stmt_body`.** An explicit `block` used as a case's body introduces its own nested lexical scope, exactly as `block` does everywhere else in the grammar (function bodies, `if`, loops) — a `var`/`fix` declared inside it is not visible in a sibling case or after the switch. A bare statement-sequence body does **not** introduce a new scope beyond the switch statement's own — a distinction worth flagging explicitly to students, since it is easy to assume the two forms are purely cosmetic.
4. **Enum member list layout carries no semantic meaning.** Whether all members appear on one line, are wrapped across several, or are one-per-line, the resulting declaration is identical — this is now purely a formatting choice, unlike before, where the grammar gave no explicit separator at all.

### 4. The submitted example, verified against this grammar

```pys
int x = 10; int y = 20;

# revised c-loop separator
loop (int x = 0; x < 10; x++) {

}

# all three enum forms are equivalent under the new grammar
enum Day {
    MONDAY, TUESDAY, WEDNESDAY, THURSDAY,
    FRIDAY, SATURDAY, SUNDAY
}

enum Day {
    MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY
}

enum Day {
    MONDAY,
    TUESDAY,
    WEDNESDAY,
    THURSDAY,
    FRIDAY,
    SATURDAY,
    SUNDAY,
}

Day day = Day.WEDNESDAY

switch (day) {
    case MONDAY, SUNDAY, FRIDAY: print(6)
    case WEDNESDAY: { print(9); print("anything else?") }
    default: {
        print(0)
        print("Invalid day")
    }
}
```

All four constructs shown are now valid PYS under this grammar: the multi-statement first line via `;`, the semicolon-separated `for`-loop header, all three `enum` layouts (comma is now the only required separator, trailing comma optional as shown in the third form), and the mixed bare/block/multi-label `switch` arms.

### 5. Rationale, per change

| Change | Problem it solves | Why this specific form |
|---|---|---|
| Optional `;` terminator | Related short declarations (e.g. a pair of loop bounds) previously had to sit on separate lines regardless of how tightly coupled they were, or the grammar had no way to express intent to keep them visually together | Kept strictly optional and single-purpose (same-line disambiguation only), rather than a universal terminator — avoids reintroducing the "must remember it everywhere" ceremony PYS deliberately avoided by making newlines statement-ending in the first place. A same-line group of declarations is also a useful visual signal worth flagging to students as a possible code smell: several unrelated `;`-joined declarations on one line often indicates the data belongs together in a `struct`/`data` type instead |
| `,` → `;` in `c_for_loop` | Using `,` inside the for-header while introducing `;` as PYS's own statement separator elsewhere would leave two different tokens doing the same conceptual job ("separate these clauses") in the same language | Direct alignment with C#/Java's identical `for (init; cond; step)` form — this is a pure transfer win with no offsetting cost, unlike most of PYS's other deliberate C#/Java deviations |
| Comma-delimited `enum` | The previous grammar specified no separator at all between members, leaving layout implicit and undocumented | Comma is the near-universal enum/list-separator convention (C#, Java, Rust, Kotlin, TypeScript); optional trailing comma is a deliberate, now-common convention (Rust, Kotlin, Python) that keeps version-control diffs minimal when a member is appended — adding a new last member no longer requires editing the previous line just to add a comma |
| Multi-label + block `switch_stmt_arm` | `switch_stmt_arm` was inconsistent with `switch_expr_arm`, which already allowed comma-separated labels — statement arms had no equivalent, forcing repeated `case` lines for shared behavior | Reuses the existing `block` production rather than inventing new grouping syntax — one fewer new grammar concept, and gives case bodies the same optional-`;`-compaction benefit as any other block |