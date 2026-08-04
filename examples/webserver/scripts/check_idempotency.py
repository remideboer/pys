#!/usr/bin/env python3
"""CI gate (spec §5 PR1/PR4, testplan F2): every routed endpoint needs an idempotency.md row.

Project root: examples/webserver/

  python examples/webserver/scripts/check_idempotency.py
  python examples/webserver/scripts/check_idempotency.py --root examples/webserver
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROUTE_RE = re.compile(
    r'req\.method\s*==\s*"(?P<method>[A-Z]+)"\s*&&\s*req\.path\s*==\s*"(?P<path>[^"]+)"'
)
TABLE_EP_RE = re.compile(r"\|\s*`(?P<ep>[A-Z]+\s+/[^`]+)`\s*\|")
CODE_KEY_RE = re.compile(r'key\s*==\s*"(?P<ep>[A-Z]+ /[^"]+)"')


def _endpoints_from_router(text: str) -> set[str]:
    return {f"{m.group('method')} {m.group('path')}" for m in ROUTE_RE.finditer(text)}


def _endpoints_from_table(text: str) -> set[str]:
    return {m.group("ep").strip() for m in TABLE_EP_RE.finditer(text)}


def _endpoints_from_idem_code(text: str) -> set[str]:
    return {m.group("ep").strip() for m in CODE_KEY_RE.finditer(text)}


def check(root: Path) -> list[str]:
    errors: list[str] = []
    src = root / "src"
    if (src / "router.pys").is_file():
        router_path = src / "router.pys"
        table_path = src / "idempotency.md"
        code_path = src / "idempotency.pys"
    else:
        # Flat layout (tests / older trees)
        router_path = root / "router.pys"
        table_path = root / "idempotency.md"
        code_path = root / "idempotency.pys"
    router = router_path.read_text(encoding="utf-8")
    table = table_path.read_text(encoding="utf-8")
    code = code_path.read_text(encoding="utf-8")

    routes = _endpoints_from_router(router)
    classified = _endpoints_from_table(table)
    coded = _endpoints_from_idem_code(code)

    if not routes:
        errors.append("No routes found in router.pys (expected req.method == ... && req.path == ...).")

    missing_table = sorted(routes - classified)
    if missing_table:
        errors.append(
            "Routes missing from idempotency.md: " + ", ".join(f"`{e}`" for e in missing_table)
        )

    missing_code = sorted(routes - coded)
    if missing_code:
        errors.append(
            "Routes missing explicit rows in idempotency.pys: "
            + ", ".join(f"`{e}`" for e in missing_code)
        )

    orphan_table = sorted(classified - routes)
    if orphan_table:
        errors.append(
            "idempotency.md entries with no router match: "
            + ", ".join(f"`{e}`" for e in orphan_table)
        )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="examples/webserver directory (default: parent of scripts/)",
    )
    args = parser.parse_args(argv)
    root = args.root
    if root is None:
        root = Path(__file__).resolve().parent.parent
    root = root.resolve()
    errs = check(root)
    if errs:
        print(f"idempotency check FAILED ({root})")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"idempotency check OK ({root})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
