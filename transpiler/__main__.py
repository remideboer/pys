from __future__ import annotations

import argparse
from pathlib import Path
from .transpiler import transpile_path, run_source


def main() -> None:
    parser = argparse.ArgumentParser(description="Python student-language transpiler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    transpile_parser = subparsers.add_parser("transpile", help="Transpile a source file to Python")
    transpile_parser.add_argument("source", type=Path, help="Source file path (.pys or .py)")
    transpile_parser.add_argument("target", type=Path, help="Target Python file path")

    run_parser = subparsers.add_parser("run", help="Transpile and execute a source file")
    run_parser.add_argument("source", type=Path, help="Source file path (.pys or .py)")

    args = parser.parse_args()

    if args.command == "transpile":
        transpile_path(args.source, args.target)
        print(f"Transpiled {args.source} -> {args.target}")
    elif args.command == "run":
        run_source(args.source)
