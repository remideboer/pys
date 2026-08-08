"""Interface method return types may be nominal (not only builtins).

BDD:
- Given an interface method `Button createButton()`, When parsing,
  Then analysis succeeds and implementing classes can return Button.
- Given a bare `createButton()`, When parsing, Then it still works (no return type).
"""

from __future__ import annotations

from transpiler.transpiler import transpile


def test_interface_nominal_return_type_parses_and_emits() -> None:
    """Scenario: GUIFactory declares Button/Checkbox return types."""
    py = transpile(
        "interface Button {\n"
        "    string paint()\n"
        "}\n"
        "interface Checkbox {\n"
        "    string paint()\n"
        "}\n"
        "interface GUIFactory {\n"
        "    Button createButton()\n"
        "    Checkbox createCheckbox()\n"
        "}\n"
        "class WinButton implements Button {\n"
        "    public constructor() {}\n"
        "    public string paint() { return \"win-button\" }\n"
        "}\n"
        "class WinCheckbox implements Checkbox {\n"
        "    public constructor() {}\n"
        "    public string paint() { return \"win-checkbox\" }\n"
        "}\n"
        "class WinFactory implements GUIFactory {\n"
        "    public constructor() {}\n"
        "    public Button createButton() { return WinButton() }\n"
        "    public Checkbox createCheckbox() { return WinCheckbox() }\n"
        "}\n"
        'print(WinFactory().createButton().paint())\n'
    )
    assert "createButton" in py
    assert "WinButton" in py


def test_interface_self_return_type_for_clone() -> None:
    py = transpile(
        "interface Shape {\n"
        "    Shape clone()\n"
        "    string describe()\n"
        "}\n"
        "class Dot implements Shape {\n"
        "    private int x\n"
        "    public constructor(int x) { this.x = x }\n"
        "    public Shape clone() { return Dot(this.x) }\n"
        "    public string describe() { return \"dot\" }\n"
        "}\n"
        "print(Dot(1).clone().describe())\n"
    )
    assert "clone" in py


def test_interface_generic_return_type_parses() -> None:
    py = transpile(
        "interface Bag {\n"
        "    list<string> items()\n"
        "}\n"
        "class StringBag implements Bag {\n"
        "    public constructor() {}\n"
        "    public list<string> items() { return [\"a\"] }\n"
        "}\n"
        "print(len(StringBag().items()))\n"
    )
    assert "items" in py
