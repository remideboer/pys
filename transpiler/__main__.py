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

    install_parser = subparsers.add_parser(
        "install",
        help="Install local PYS tooling (contributor helpers)",
    )
    install_sub = install_parser.add_subparsers(dest="install_target", required=True)
    ext_parser = install_sub.add_parser(
        "extension",
        help="Build and install the latest pys-language VSIX into Cursor/VS Code",
    )
    ext_parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip npm run package; install the newest existing VSIX only",
    )
    ext_parser.add_argument(
        "--editor",
        choices=("auto", "cursor", "code"),
        default="auto",
        help="Editor CLI (default: prefer cursor, then code)",
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
    elif args.command == "install" and args.install_target == "extension":
        import subprocess

        from .ext_install import install_extension

        try:
            vsix = install_extension(
                build=not args.no_build,
                editor=args.editor,
            )
        except (FileNotFoundError, ValueError, OSError, subprocess.CalledProcessError) as exc:
            parser.error(str(exc))
        print(f"Installed {vsix.name}")
        print("Reload Cursor/VS Code from the Command Palette when ready.")
    else:
        parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
