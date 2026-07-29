# PYS language documentation

Formal grammar: [`language.ebnf`](language.ebnf) (EBNF).
Visual railroad diagrams: [`language-railroad.html`](language-railroad.html) (open in a browser).

PYS is a typed teaching language that transpiles to Python. Prefer **brace style**
(`{` ... `}`) as in `examples/main.pys`. Indentation style and legacy `then:` / `do:`
forms remain for compatibility (see Appendix A in the EBNF).

## Quick examples

```pys
import vehicles
import mysql.connector

global const float PI = 3.14159

int x = 10
var z = x + 1
fix int locked = x + z

list<tuple<string, string>> rows = mycursor.fetchall()
loop (tuple<string, string> row in rows) {
    print(row)
}

package class Car inherits Vehicle implements Drivable {
    private string color
    public Car(string make, string model, int year, string color) {
        super(make, model, year)
        this.color = color
    }
    public start() {
        print("vroom")
    }
}
```

## Related project files

| File | Role |
|------|------|
| `docs/language.ebnf` | Formal EBNF |
| `docs/language-railroad.html` | Railroad diagram visuals |
| `examples/main.pys` | Feature showcase |
| `transpiler/language_spec.py` | Line translation rules |
| `pys.deps` | External Python dependencies (not language syntax) |
