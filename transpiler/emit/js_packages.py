"""npm package names recognized by the JavaScript emit target."""

from __future__ import annotations

# Bare / alias import names → npm package specifiers (ESM).
JS_PACKAGE_MAP: dict[str, str] = {
    "nodegui": "@nodegui/nodegui",
    "@nodegui/nodegui": "@nodegui/nodegui",
    "mysql2": "mysql2",
    "mysql": "mysql2",
}
