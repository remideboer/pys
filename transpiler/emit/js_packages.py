"""npm package names recognized by the JavaScript emit target."""

from __future__ import annotations

# Bare / alias import names → npm / Node package specifiers (ESM).
JS_PACKAGE_MAP: dict[str, str] = {
    "nodegui": "@nodegui/nodegui",
    "@nodegui/nodegui": "@nodegui/nodegui",
    "mysql2": "mysql2",
    "mysql": "mysql2",
    "express": "express",
    "crypto": "node:crypto",
    "buffer": "node:buffer",
}

# Packages whose ESM default export is the callable/value students bind
# (`import express from "express"`), not a namespace object.
JS_DEFAULT_EXPORT_PACKAGES: frozenset[str] = frozenset({"express"})
