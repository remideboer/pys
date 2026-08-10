"""Teaching metadata for educational refactors (Fowler-aligned names)."""
from __future__ import annotations

from typing import Any

CATALOG: dict[str, dict[str, Any]] = {
    "rename-symbol": {
        "title": "Rename Symbol",
        "fowler": "Rename Variable / Rename Field / Rename Function",
        "summary": "Change a name everywhere it refers to the same declaration.",
        "why": (
            "Clear names reduce scanning load. PYS renames binding-aware sites "
            "only — same text in another scope is left alone (unlike a find-replace)."
        ),
    },
    "extract-variable": {
        "title": "Extract Variable",
        "fowler": "Extract Variable",
        "summary": "Replace an expression with a named local initialized to that expression.",
        "why": (
            "Names document intent and let you reuse the value without duplicating "
            "the expression."
        ),
    },
    "extract-function": {
        "title": "Extract Function / Method",
        "fowler": "Extract Function",
        "summary": "Move selected statements into a new function or method and call it.",
        "why": (
            "Smaller units are easier to name, test, and reuse. Inside a class, "
            "the new method is placed in the methods section (member kind order)."
        ),
    },
    "inline-variable": {
        "title": "Inline Variable",
        "fowler": "Inline Variable",
        "summary": "Replace uses of a single-assignment local with its initializer and remove the decl.",
        "why": "Remove a name that no longer clarifies intent.",
    },
    "inline-function": {
        "title": "Inline Function",
        "fowler": "Inline Function",
        "summary": "Replace calls with the function body and remove the definition when safe.",
        "why": "Undo an extract that added more noise than clarity.",
    },
    "safe-delete": {
        "title": "Safe Delete",
        "fowler": "Remove Dead Code",
        "summary": "Delete a declaration only when no other binding-aware references remain.",
        "why": "Avoid breaking callers; conflicts list remaining usages like IntelliJ Safe Delete.",
    },
    "introduce-parameter": {
        "title": "Introduce Parameter",
        "fowler": "Add Parameter / Change Function Declaration",
        "summary": "Add a parameter and thread a local or expression through call sites.",
        "why": "Make a dependency explicit at the API boundary instead of closing over hidden state.",
    },
    "create-class": {
        "title": "Create Class",
        "fowler": "Introduce Class (generation)",
        "summary": "Generate a class with fields and constructor from a named-argument constructor call.",
        "why": (
            "When a type is used before it exists, scaffold a matching class so students "
            "can iterate on design without typing boilerplate first."
        ),
    },
}


def catalog_entry(catalog_id: str) -> dict[str, Any]:
    return dict(CATALOG.get(catalog_id) or {"title": catalog_id, "summary": "", "why": ""})
