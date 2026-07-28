from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, NoReturn

from .language_spec import LANGUAGE, _strip_type_annotation, _default_value_for_type

INDENT_SIZE = 4


class TranspileError(ValueError):
    """Raised when source code cannot be transpiled."""

    def __init__(
        self,
        message: str,
        line_number: int | None = None,
        column: int | None = None,
        code_line: str | None = None,
    ) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.column = column
        self.code_line = code_line
    
    def __str__(self) -> str:  # include line/column in the message when available
        base = super().__str__()
        parts: list[str] = []
        if self.line_number is not None:
            parts.append(f"line {self.line_number}")
        if self.column is not None:
            parts.append(f"column {self.column}")
        if parts:
            return f"{base} ({', '.join(parts)})"
        return base


class Parser:
    def __init__(self, source: str) -> None:
        self.raw_lines = source.splitlines()
        self.source_lines = self._preprocess_source(source)
        self.output_lines: List[str] = []
        self.indent_stack: List[int] = [0]
        self.brace_mode = any(line.strip() in {"{", "}"} for line, _ in self.source_lines)
        # block_context holds tuples like ("class", "ClassName") or ("function", "name")
        self.block_context: List[tuple[str, str] | None] = [None]
        self.pending_block_context: tuple[str, str] | None = None
        # Enforce formatting rules early: tabs, trailing whitespace, and indentation multiples.
        self._enforce_formatting()

    def _preprocess_source(self, source: str) -> List[tuple[str, int]]:
        lines: List[tuple[str, int]] = []
        current = ""
        current_line_number = 1
        in_string = False
        string_quote = ""
        escape = False
        i = 0

        paren_depth = 0
        saw_blank_line = False
        while i < len(source):
            char = source[i]

            if escape:
                current += char
                escape = False
                i += 1
                continue

            if char == "\\" and in_string:
                current += char
                escape = True
                i += 1
                continue

            if char in {'"', "'"}:
                current += char
                if not in_string:
                    in_string = True
                    string_quote = char
                elif string_quote == char:
                    in_string = False
                i += 1
                continue

            if not in_string and char == "#":
                if current.strip():
                    lines.append((current.rstrip(), current_line_number))
                    current = ""
                comment = source[i:]
                end = comment.find("\n")
                if end == -1:
                    lines.append((comment.strip(), current_line_number))
                    break
                lines.append((comment[:end].strip(), current_line_number))
                i += end + 1
                current_line_number += 1
                continue

            if not in_string and char == ";":
                self._error(
                    "Formatting Error: semicolons are not allowed; use line breaks instead.",
                    current_line_number,
                    current + char,
                    1,
                )

            if not in_string and char == "(":
                paren_depth += 1
                current += char
                i += 1
                continue

            if not in_string and char == ")" and paren_depth > 0:
                paren_depth -= 1
                current += char
                i += 1
                continue

            if not in_string and char == "{":
                if current.strip():
                    lines.append((current, current_line_number))
                    current = ""
                    saw_blank_line = False
                lines.append(("{", current_line_number))
                saw_blank_line = False
                i += 1
                continue

            if not in_string and char == "}":
                if current.strip():
                    lines.append((current, current_line_number))
                    current = ""
                    saw_blank_line = False
                lines.append(("}", current_line_number))
                saw_blank_line = False
                i += 1
                continue

            if char == "\n":
                if current.strip():
                    lines.append((current, current_line_number))
                    current = ""
                    saw_blank_line = False
                elif saw_blank_line:
                    lines.append(("", current_line_number))
                    saw_blank_line = False
                else:
                    saw_blank_line = True
                in_string = False
                string_quote = ""
                escape = False
                paren_depth = 0
                i += 1
                current_line_number += 1
                continue

            current += char
            i += 1

        if current.strip():
            lines.append((current.strip(), current_line_number))
        return lines

    def parse(self) -> str:
        for raw_line, original_line_number in self.source_lines:
            if raw_line.strip() == "":
                self.output_lines.append("")
                continue

            if "\t" in raw_line:
                self._error("Tabs are not supported for indentation.", original_line_number, raw_line)

            if self.brace_mode and raw_line.strip() == "{":
                self._open_block(original_line_number)
                continue

            if self.brace_mode and raw_line.strip() == "}":
                self._close_block(original_line_number)
                continue

            if self.brace_mode:
                indent = self.indent_stack[-1]
                stripped = raw_line.strip()
            else:
                indent = len(raw_line) - len(raw_line.lstrip(" "))
                if indent % INDENT_SIZE != 0:
                    self._error(
                        f"Indentation must use multiples of {INDENT_SIZE} spaces.",
                        original_line_number,
                        raw_line,
                    )
                self._update_indent(indent, original_line_number)
                stripped = raw_line.strip()

            try:
                python_line = self._parse_line(stripped, original_line_number, raw_line=raw_line)
            except ValueError as exc:
                column = raw_line.find(stripped) + 1 if raw_line and stripped else 1
                raise TranspileError(str(exc), original_line_number, column, raw_line.rstrip()) from exc
            for output_line in python_line.splitlines():
                self.output_lines.append(" " * indent + output_line)

        if self.brace_mode and len(self.indent_stack) != 1:
            raise TranspileError("Unclosed block at end of file.")

        python_text = "\n".join(self.output_lines) + "\n"
        # Normalize common object references from source language to Python.
        python_text = python_text.replace("this.", "self.")
        try:
            ast.parse(python_text)
        except SyntaxError as exc:
            code_line = ""
            if exc.lineno is not None and 1 <= exc.lineno <= len(python_text.splitlines()):
                code_line = python_text.splitlines()[exc.lineno - 1]
            raise TranspileError(
                f"Generated Python is invalid: {exc.msg}",
                line_number=exc.lineno,
                column=exc.offset,
                code_line=code_line,
            ) from exc
        return python_text

    def _open_block(self, line_number: int) -> None:
        if not self.brace_mode:
            self._error("Unexpected opening brace.", line_number, "{")
        self.indent_stack.append(self.indent_stack[-1] + INDENT_SIZE)
        self.block_context.append(self.pending_block_context)
        self.pending_block_context = None

    def _close_block(self, line_number: int) -> None:
        if not self.brace_mode:
            self._error("Unexpected closing brace.", line_number, "}")
        if len(self.indent_stack) == 1:
            self._error("Unexpected closing brace.", line_number, "}")
        self.indent_stack.pop()
        if len(self.block_context) > 1:
            self.block_context.pop()

    def _error(self, message: str, line_number: int, line: str, column: int | None = None) -> NoReturn:
        snippet = line.rstrip()
        raise TranspileError(f"{message}", line_number, column, snippet)

    def _enforce_formatting(self) -> None:
        """Raise a Formatting Error if source contains tabs, trailing whitespace,
        or incorrect indentation (when not using brace style)."""
        # When using brace style we still require consistent indentation inside
        # each brace-delimited block. Track expected indent per brace depth.
        expected_indent_by_depth: dict[int, int | None] = {}
        depth = 0
        for idx, line in enumerate(self.raw_lines, start=1):
            # Skip empty lines
            if line.strip() == "":
                continue
            # Tabs are disallowed
            if "\t" in line:
                self._error(
                    "Formatting Error: tabs are not allowed; replace tabs with spaces.",
                    idx,
                    line,
                    1,
                )
            # Trailing whitespace is disallowed
            if len(line) != len(line.rstrip(" \t")):
                self._error(
                    "Formatting Error: trailing whitespace is not allowed; remove extra spaces at the end of the line.",
                    idx,
                    line,
                    len(line.rstrip(" \t")) + 1,
                )

            if self.brace_mode:
                # Determine the current depth for this line before applying braces on it.
                # Use a simple brace count (acceptable for teaching language).
                # Treat lines that are only braces specially.
                stripped = line.strip()
                is_open_only = stripped == "{"
                is_close_only = stripped == "}"

                # For lines that contain code possibly with trailing/leading braces,
                # we check the indentation at the current depth before updating depth.
                if not is_open_only and not is_close_only:
                    current_depth = depth
                    leading = len(line) - len(line.lstrip(" "))
                    if leading % INDENT_SIZE != 0:
                        self._error(
                            "Formatting Error: indentation must use the same number of spaces consistently.",
                            idx,
                            line,
                            1,
                        )
                    expected = expected_indent_by_depth.get(current_depth)
                    if expected is None:
                        expected_indent_by_depth[current_depth] = leading
                    elif expected != leading:
                        self._error(
                            f"Formatting Error: inconsistent indentation at brace depth {current_depth}; used {leading} spaces, while previous lines at this depth use {expected} spaces.",
                            idx,
                            line,
                            leading + 1,
                        )

                # Now update depth according to number of braces on this line
                opens = line.count("{")
                closes = line.count("}")
                depth += opens - closes
                if depth < 0:
                    depth = 0
            else:
                # If using indentation style (not brace_mode), leading spaces must be multiples of INDENT_SIZE
                leading = len(line) - len(line.lstrip(" "))
                if leading % INDENT_SIZE != 0:
                    self._error(
                        "Formatting Error: indentation must use the same number of spaces consistently.",
                        idx,
                        line,
                        1,
                    )

    def _set_pending_block_context(self, line: str) -> None:
        # Record the incoming block type and name so the open block can store it.
        if line.startswith("class "):
            m = re.match(r"class\s+([A-Za-z_]\w*)", line)
            if m:
                self.pending_block_context = ("class", m.group(1))
            else:
                self.pending_block_context = ("class", "")
        elif line.startswith("function ") or line.startswith("func "):
            m = re.match(r"(?:function|func)\s+([A-Za-z_]\w*)", line)
            if m:
                self.pending_block_context = ("function", m.group(1))
            else:
                self.pending_block_context = ("function", "")
        else:
            self.pending_block_context = None

    def _inside_class(self) -> bool:
        return any(context is not None and context[0] == "class" for context in self.block_context)

    def _current_class_name(self) -> str | None:
        for ctx in reversed(self.block_context):
            if ctx is not None and ctx[0] == "class":
                return ctx[1]
        return None

    def _enforce_class_member_access(self, line: str, line_number: int, raw_line: str) -> None:
        if not self._inside_class():
            return
        if re.fullmatch(r"(?:int|float|char|string|bool)\s+[A-Za-z_]\w*(?:\s*=\s*.+)?", line):
            column = raw_line.find(line) + 1 if raw_line else 1
            raise TranspileError(
                "Class member declarations require an access modifier. Use public/private/protected/module.",
                line_number,
                column,
                raw_line.rstrip(),
            )

    def _update_indent(self, indent: int, line_number: int) -> None:
        current = self.indent_stack[-1]
        if indent == current:
            return
        if indent > current:
            if indent - current != INDENT_SIZE:
                raise TranspileError(
                    f"Unexpected indent increase on line {line_number}."
                )
            self.indent_stack.append(indent)
            self.block_context.append(self.pending_block_context)
            self.pending_block_context = None
            return

        while self.indent_stack and indent < self.indent_stack[-1]:
            self.indent_stack.pop()
            if len(self.block_context) > 1:
                self.block_context.pop()

        if self.indent_stack[-1] != indent:
            raise TranspileError(
                f"Mismatch indentation on line {line_number}."
            )

    def _parse_line(self, line: str, line_number: int, raw_line: str) -> str:
        if line.startswith("#"):
            return line

        self._set_pending_block_context(line)
        self._enforce_class_member_access(line, line_number, raw_line)

        # Detect constructor-like method declarations inside a class and translate to __init__
        if self._inside_class():
            ctor_match = re.fullmatch(r"(?:public|private|protected|module)\s*(?:(?P<rtype>int|float|char|string)\s+)?(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*?)\)", line)
            if ctor_match:
                cls_name = self._current_class_name()
                if cls_name and ctor_match.group("name") == cls_name:
                    args_raw = ctor_match.group("args")
                    args_raw = args_raw.strip()
                    if not args_raw:
                        return "def __init__(self):"
                    params = []
                    for part in [p.strip() for p in args_raw.split(",") if p.strip()]:
                        m = re.fullmatch(r"(?:(?P<type>int|float|char|string|bool)\s+)?(?P<name>[A-Za-z_]\w*)(?:\s*=\s*(?P<default>.+))?", part)
                        if not m:
                            # fallback: strip type annotations and use None
                            name = re.sub(r"^(int|float|char|string|bool)\s+", "", part).strip()
                            params.append(f"{name}=None")
                            continue
                        ptype = m.group("type")
                        name = m.group("name")
                        default = m.group("default")
                        if default is not None:
                            default_val = default.strip()
                        elif ptype:
                            default_val = _default_value_for_type(ptype)
                        else:
                            default_val = "None"
                        params.append(f"{name}={default_val}")
                    args = "self, " + ", ".join(params)
                    return f"def __init__({args}):"
            # Methods with access modifiers that are not constructors should include `self`.
            method_match = re.fullmatch(r"(?:public|private|protected|module)\s*(?:(?P<rtype>int|float|char|string)\s+)?(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*?)\)", line)
            if method_match:
                name = method_match.group("name")
                cls_name = self._current_class_name()
                if not (cls_name and name == cls_name):
                    args = _strip_type_annotation(method_match.group("args"))
                    args = f"self, {args}" if args else "self"
                    return f"def {name}({args}):"
            # Plain `function` declarations inside a class should also get `self`.
            func_match = re.fullmatch(r"function(?:\s+(?:(?P<rtype>int|float|char|string)\s+))?\s*(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*?)\)\s*(?::\s*)?", line)
            if func_match:
                name = func_match.group("name")
                args = _strip_type_annotation(func_match.group("args"))
                args = f"self, {args}" if args else "self"
                return f"def {name}({args}):"

        transformed = LANGUAGE.translate_line(line)
        if transformed == line and line.strip() == "":
            return ""

        if transformed == line and line.startswith("let "):
            assignment = line[4:].strip()
            if "=" not in assignment:
                self._error(
                    "Invalid let statement; expected `let name = value`.",
                    line_number,
                    line,
                )
            return assignment

        if transformed == line and line.startswith("func "):
            match = re.fullmatch(r"func\s+([A-Za-z_]\w*)\s*\((.*?)\)\s*:\s*", line)
            if not match:
                self._error(
                    "Invalid function definition; expected `func name(args):`.",
                    line_number,
                    line,
                )
            name, args = match.groups()
            return f"def {name}({args}):"

        if transformed == line and line.startswith("print "):
            expression = line[6:].strip()
            if expression == "":
                self._error(
                    "Invalid print statement; expected `print expression`.",
                    line_number,
                    line,
                )
            return f"print({expression})"

        return transformed


def transpile(source_code: str) -> str:
    """Convert teaching language source into valid Python source."""
    parser = Parser(source_code)
    return parser.parse()


def transpile_path(source_path: Path, target_path: Path) -> None:
    """Transpile a file to Python and write the output."""
    source_text = source_path.read_text(encoding="utf-8")
    if source_path.suffix == ".pys":
        python_text = transpile(source_text)
    else:
        python_text = source_text

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(python_text, encoding="utf-8")


def run_source(source_path: Path) -> int:
    """Transpile a source file and execute it with the current Python interpreter."""
    if source_path.suffix == ".pys":
        python_text = transpile(source_path.read_text(encoding="utf-8"))
    else:
        python_text = source_path.read_text(encoding="utf-8")

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
        temp_file.write(python_text)
        temp_filename = temp_file.name

    process = subprocess.run([sys.executable, temp_filename], check=False)
    return process.returncode
