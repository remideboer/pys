"""Migrate C-for `,`→`;` and enum juxtaposition→commas in teaching corpus."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_LOOP_HEADER = re.compile(r"\bloop\s*\(([^)]*)\)", re.MULTILINE)
_ENUM_BLOCK = re.compile(
    r"(\benum\s+[A-Za-z_][A-Za-z0-9_]*\s*\{)(.*?)(\})",
    re.DOTALL,
)


def _migrate_c_for(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        if re.search(r"\bin\b", inner):
            return m.group(0)
        if inner.count(";") >= 2:
            return m.group(0)
        depth = 0
        commas = 0
        for ch in inner:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == "," and depth == 0:
                commas += 1
        if commas < 2:
            return m.group(0)
        out: list[str] = []
        depth = 0
        for ch in inner:
            if ch in "([{":
                depth += 1
                out.append(ch)
            elif ch in ")]}":
                depth -= 1
                out.append(ch)
            elif ch == "," and depth == 0:
                out.append(";")
            else:
                out.append(ch)
        return f"loop ({''.join(out)})"

    return _LOOP_HEADER.sub(repl, text)


def _migrate_enum_body(body: str) -> str:
    pieces: list[tuple[str, str]] = []
    i = 0
    n = len(body)
    while i < n:
        if body[i].isspace():
            j = i
            while j < n and body[j].isspace():
                j += 1
            pieces.append(("ws", body[i:j]))
            i = j
            continue
        if body[i] == "#":
            j = i
            while j < n and body[j] != "\n":
                j += 1
            pieces.append(("comment", body[i:j]))
            i = j
            continue
        if body[i] == ",":
            pieces.append(("comma", ","))
            i += 1
            continue
        m = re.match(
            r"([A-Za-z_][A-Za-z0-9_]*)(\s*=\s*(?:0[xXbB][0-9A-Fa-f_]+|\d[\d_]*|\"(?:\\.|[^\"])*\"|'[^']*'))?",
            body[i:],
        )
        if m:
            pieces.append(("member", m.group(0)))
            i += len(m.group(0))
            continue
        pieces.append(("raw", body[i]))
        i += 1

    out: list[str] = []
    last_was_member = False
    for kind, val in pieces:
        if kind == "member":
            if last_was_member:
                for k in range(len(out) - 1, -1, -1):
                    if out[k].strip() == "":
                        continue
                    if out[k] != ",":
                        out.insert(k + 1, ",")
                    break
            out.append(val)
            last_was_member = True
        elif kind == "comma":
            out.append(val)
            last_was_member = False
        else:
            out.append(val)
    return "".join(out)


def _migrate_enums(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        return m.group(1) + _migrate_enum_body(m.group(2)) + m.group(3)

    return _ENUM_BLOCK.sub(repl, text)


def migrate_text(text: str) -> str:
    return _migrate_enums(_migrate_c_for(text))


def main() -> None:
    roots = [
        ROOT / "examples",
        ROOT / "book",
        ROOT / "tutorials",
        ROOT / "docs",
        ROOT / "tests" / "golden",
        ROOT / "requirements",
    ]
    changed = 0
    for base in roots:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if "html" in path.parts and "book" in path.parts:
                continue
            if path.suffix not in {".pys", ".md", ".ebnf", ".txt", ".py"}:
                continue
            original = path.read_text(encoding="utf-8")
            updated = migrate_text(original)
            if updated != original:
                path.write_text(updated, encoding="utf-8", newline="\n")
                changed += 1
                print(path.relative_to(ROOT))
    print(f"updated {changed} files")


if __name__ == "__main__":
    main()
