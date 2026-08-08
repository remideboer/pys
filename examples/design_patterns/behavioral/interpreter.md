# Interpreter

**Category:** Behavioral  
**Demo:** [interpreter.pys](interpreter.pys)  
**Wikipedia:** [Interpreter pattern](https://en.wikipedia.org/wiki/Interpreter_pattern) · [Design Patterns (book)](https://en.wikipedia.org/wiki/Design_Patterns)

## Intent

Given a language, define a representation for its grammar along with an interpreter that uses the representation to interpret sentences in the language.

## Explanation

Expression trees (`Number`, `Add`, `Mul`) implement `eval`. Good for tiny DSLs; for large languages use a real parser/generator instead of hand-built Interpreter trees.

## Classic structure (UML)

```mermaid
classDiagram
    class AbstractExpression {
        +interpret(context)
    }
    class TerminalExpression
    class NonterminalExpression
    AbstractExpression <|-- TerminalExpression
    AbstractExpression <|-- NonterminalExpression
    NonterminalExpression o-- AbstractExpression
```

## This demo

`Expr` is AbstractExpression; `Number` is terminal; `Add` / `Mul` are nonterminals holding child expressions.

```mermaid
classDiagram
    class Expr
    class Number
    class Add
    class Mul
    Expr <|-- Number
    Expr <|-- Add
    Expr <|-- Mul
    Add o-- Expr
    Mul o-- Expr
```

## Real-world use cases

- Simple rule engines or boolean filters built as expression trees.
- Regex engines (conceptually) and SQL WHERE clauses as AST walkers.
- Spreadsheet formula evaluation for a tiny operator set.

## Run

```text
python -m transpiler run examples/design_patterns/behavioral/interpreter.pys
```
