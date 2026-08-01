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

    deps_parser = subparsers.add_parser("deps", help="Manage locked Python dependencies")
    deps_subparsers = deps_parser.add_subparsers(dest="deps_command", required=True)
    lock_parser = deps_subparsers.add_parser("lock", help="Resolve and hash dependencies")
    lock_parser.add_argument(
        "deps_file",
        type=Path,
        nargs="?",
        default=Path("pys.deps"),
        help="Path to pys.deps (default: ./pys.deps)",
    )

    args = parser.parse_args()

    if args.command == "transpile":
        transpile_path(args.source, args.target)
        print(f"Transpiled {args.source} -> {args.target}")
    elif args.command == "run":
        raise SystemExit(run_source(args.source))
    elif args.command == "deps" and args.deps_command == "lock":
        from .deps import DepsError, generate_lock, load_deps

        deps_file = args.deps_file.resolve()
        try:
            config = load_deps(deps_file, stop_at=deps_file.parent)
            if config is None or config.source_path != deps_file:
                raise DepsError(f"Dependency file not found: {deps_file}")
            lock_path = generate_lock(config)
        except DepsError as exc:
            parser.error(str(exc))
        print(f"Locked dependencies -> {lock_path}")


if __name__ == "__main__":
    main()
