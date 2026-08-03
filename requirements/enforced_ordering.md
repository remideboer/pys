## PYS Language Specification — Enforced Member Ordering

### 1. Overview

PYS enforces a canonical member order inside every multi-category body (`class_body`, `trait_body`, `entity_body`, `struct_body`) and a canonical position for imports at the top level. This is a grammar-level constraint, not a linter suggestion layered on top of a free-form grammar: an out-of-order declaration is a parse error, not a style warning. The ordering axis enforced is **kind** (what category of declaration something is) only — visibility (`public`/`private`/`protected`) is deliberately *not* used as a second ordering axis within a category, to keep the cognitive signal to one dimension.

This is a deliberate PYS-specific design choice, not a convention shared by other mainstream languages. Java, C#, Kotlin, and Python style guides (Checkstyle, StyleCop, PEP 8) recommend the same constants-fields-constructors-methods order but only as a linter warning; none of them reject out-of-order code at compile time. Student-facing material must state this explicitly: the discipline is expected to be internalized as a habit transferable across languages, even though only PYS enforces it structurally. Students should not assume Java or C# will reject a method declared before a field — they should instead carry the *habit* of ordering code this way regardless of whether the compiler in front of them demands it.

### 2. Rationale

1. **Reduced extraneous cognitive load** (Sweller): a fixed, predictable position for each kind of member means a reader does not need to scan an entire body to determine what category a given declaration belongs to — the structure itself carries information, freeing working memory for understanding what the code actually does.
2. **Consistent with PYS's existing "make the implicit explicit" philosophy**: the same movement already applied to `requires` in traits and `identity(...)` in entities — a convention experienced developers eventually adopt informally is instead compiler-enforced from the start.
3. **Refactoring is intended to require physical relocation.** Changing a field's role (e.g. from mutable to `fix`) or adding a constructor is expected to also move the declaration to its correct section — this is treated as a feature, not friction: the ordering in the refactored code should reflect the ordering rule, not merely the ordering rule being satisfied incidentally at the time the code was first written.

### 3. Grammar

Ordering is encoded directly in the production rules as an ordered sequence of repeated groups, rather than as a free repetition validated afterward by a separate semantic pass — this makes an incorrect order a grammatical impossibility, not a checked-after-the-fact error.

```ebnf
(* ------------------------- Classes ------------------------- *)

class_body        = "{" ,
                    { const_field_decl } ,
                    { fix_field_decl } ,
                    { field_decl } ,
                    { constructor_decl } ,
                    { method_decl } ,
                    "}" ;

const_field_decl  = member_access , "const" , primitive_type , identifier , "=" , expression ;
fix_field_decl    = member_access , "fix" , type_name , identifier , [ "=" , expression ] ;
field_decl        = member_access , type_name , identifier , [ "=" , expression ] ;
(* field_decl now denotes an ordinary mutable field only; "const" and
   "fix" fields are separate productions occupying their own,
   earlier, ordered sections. *)
method_decl       = member_access , [ return_type ] , identifier ,
                   "(" , [ parameter_list ] , ")" , block ;
constructor_decl  = member_access , identifier ,
                   "(" , [ parameter_list ] , ")" , block ;

(* ------------------------- Structs ------------------------- *)

struct_body       = "{" ,
                    { fix_struct_field_decl } ,
                    { struct_field_decl } ,
                    "}" ;

fix_struct_field_decl = "fix" , type_name , identifier , [ "=" , expression ] ;
struct_field_decl      = type_name , identifier , [ "=" , expression ] ;
(* Same rationale as class_body, reduced scope since structs carry
   no constructors or methods. *)

(* ------------------------- Traits ------------------------- *)

trait_body        = "{" ,
                    { trait_requires } ,
                    { trait_method_decl } ,
                    "}" ;
(* Dependencies a trait has on its host must be visible before its
   own implementation is read — mirrors declaring imports before use. *)

(* ------------------------- Entities ------------------------- *)

entity_body       = "{" ,
                    { identity_field_decl } ,
                    { fix_field_decl } ,
                    { field_decl } ,
                    { constructor_decl } ,
                    { method_decl } ,
                    "}" ;

identity_field_decl = member_access , "fix" , type_name , identifier ;
(* Every field named in this entity's own identity(...) clause must be
   declared here, in this leading section — the single most important
   structural fact about an entity (its key) is placed first, never
   buried among ordinary mutable fields. Any other "fix" field not
   named in identity(...) belongs in the next section, fix_field_decl. *)

(* ------------------------- Program (top level) ------------------------- *)

program           = { import_stmt } , { top_level } ;
top_level         = declaration | statement ;
(* All import_stmt occurrences must precede every declaration and
   statement in the file — imports scattered through a file are
   exactly the disorder this rule set exists to prevent elsewhere. *)
```

### 4. Deliberately not extended to `tasks_block`

Ordering of `tasks_item` within a `tasks_block` (e.g. requiring every `task` definition to precede its first use) is deliberately not enforced positionally. The existing DAG requirement on `await` dependencies already imposes a logical structure on task ordering; layering a second, purely positional rule on top of an existing semantic rule would serve the same underlying intent (readable, predictable order) through two different enforcement mechanisms, and risks confusing students about whether a given ordering requirement stems from the DAG constraint or from a style rule — added complexity without added clarity.

### 5. Educational compiler diagnostics

Every ordering violation must produce a diagnostic that states both *what* was found out of place and *why* the ordering is required — not a bare grammar/syntax error. This mirrors the diagnostic philosophy already specified for `requires` violations in traits and missing `identity(...)` fields in entities.

| Violation | Diagnostic message |
|---|---|
| Method before required field/constructor section | `Method 'x' found before the fields/constructor section. PYS requires class members in the order: const fields, fix fields, fields, constructors, methods — this fixed order lets a reader find any member category without scanning the whole class.` |
| Field after a constructor | `Field 'y' found after a constructor. Fields must be declared before any constructor, so a reader sees the full state shape before the code that initializes it.` |
| `const` field after a `fix` or mutable field | `Constant 'MAX' found after non-const fields. Constants must appear first, since they represent fixed, class-wide facts rather than per-instance state.` |
| Import after a declaration or statement | `Import statement found after other code. All imports must appear at the top of the file, before any declaration or statement, so a reader sees the file's full dependency surface before its content.` |
| Trait method before a `requires` clause | `Method 'print' found before trait Printable's 'requires' section. Declare everything the trait depends on its host for before defining methods that rely on it, so the dependency is visible first.` |
| Non-identity field before an identity field in `entity_body` | `Field 'name' found before identity field 'customerId'. An entity's identity field(s) must be declared first, since they are the single most important structural fact about the entity — its key.` |

### 6. Note for student-facing material

This must be taught as a two-part habit, not a single fact: (1) the concrete rule PYS enforces, and (2) the explicit expectation that the same discipline is worth carrying into languages that do not enforce it. The second part is the one likely to be lost if only the first is taught — a student who only experiences the rule as "the PYS compiler makes me do this" may not carry it forward the moment the compiler stops demanding it. The recommended framing: *"PYS enforces this because it is good practice everywhere; most other languages only recommend it."* This directly parallels the framing already used for lambda capture semantics and for the Hibernate `equals`/`hashCode` postmortems — in each case, the goal is a transferable insight that survives the switch away from PYS, not merely compliance with PYS's own compiler.