from __future__ import annotations

import argparse
from pathlib import Path
from .transpiler import TranspileError, transpile_path, run_source


def main() -> None:
    parser = argparse.ArgumentParser(description="Python student-language transpiler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    transpile_parser = subparsers.add_parser("transpile", help="Transpile a source file")
    transpile_parser.add_argument("source", type=Path, help="Source file path (.pys or .py)")
    transpile_parser.add_argument(
        "output",
        type=Path,
        help="Output file path (.py or .mjs)",
    )
    transpile_parser.add_argument(
        "--target",
        choices=("python", "javascript"),
        default="python",
        help="Emit backend (default: python)",
    )

    run_parser = subparsers.add_parser("run", help="Transpile and execute a source file")
    run_parser.add_argument("source", type=Path, help="Source file path (.pys or .py)")
    run_parser.add_argument(
        "--target",
        choices=("python", "javascript"),
        default=None,
        help=(
            "Emit backend / runtime (default: [project].target in pys.toml, "
            "else python)"
        ),
    )

    deps_parser = subparsers.add_parser("deps", help="Manage locked Python dependencies")
    deps_subparsers = deps_parser.add_subparsers(dest="deps_command", required=True)
    lock_parser = deps_subparsers.add_parser("lock", help="Resolve and hash dependencies")
    lock_parser.add_argument(
        "deps_file",
        type=Path,
        nargs="?",
        default=None,
        help="Path to pys.toml or legacy pys.deps (default: ./pys.toml, else ./pys.deps)",
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
        try:
            transpile_path(args.source, args.output, target=args.target)
        except TranspileError as exc:
            parser.error(str(exc))
        print(f"Transpiled {args.source} -> {args.output} (target={args.target})")
    elif args.command == "run":
        try:
            raise SystemExit(run_source(args.source, target=args.target))
        except TranspileError as exc:
            parser.error(str(exc))
    elif args.command == "deps" and args.deps_command == "lock":
        from .deps import DEPS_FILENAME, MANIFEST_FILENAME, DepsError, generate_lock, load_deps
        from .npm_deps import parse_npm_from_toml

        if args.deps_file is None:
            if Path(MANIFEST_FILENAME).is_file():
                deps_file = Path(MANIFEST_FILENAME).resolve()
            elif Path(DEPS_FILENAME).is_file():
                deps_file = Path(DEPS_FILENAME).resolve()
            else:
                parser.error(
                    f"No {MANIFEST_FILENAME} or {DEPS_FILENAME} in the current directory"
                )
                return
        else:
            deps_file = args.deps_file.resolve()
        try:
            if not deps_file.is_file():
                raise DepsError(f"Dependency file not found: {deps_file}")
            config = load_deps(deps_file, stop_at=deps_file.parent)
            if config is None or config.source_path is None:
                if deps_file.name == MANIFEST_FILENAME:
                    npm = parse_npm_from_toml(
                        deps_file.read_text(encoding="utf-8"),
                        source_path=deps_file,
                    )
                    if npm is not None:
                        print(
                            f"{deps_file}: [dependencies.npm] only - no pys.lock. "
                            "npm packages install on Run into ~/.pys/repository/npm/ "
                            "(PYS_REPO override). Use Run Project / "
                            "`python -m transpiler run` instead of deps lock."
                        )
                        return
                raise DepsError(
                    f"No Python [dependencies] / [interpreter] in {deps_file} "
                    "(deps lock writes pys.lock for Python packages only)."
                )
            if config.source_path.resolve() != deps_file:
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
