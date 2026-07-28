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
        self.declared_variables: set[str] = set()
        self.variable_types: dict[str, str] = {}
        self.class_members: dict[str, dict[str, str]] = {}
        self.class_parents: dict[str, str | None] = {}
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
            except TranspileError as exc:
                raise TranspileError(
                    str(exc),
                    exc.line_number or original_line_number,
                    exc.column,
                    exc.code_line or raw_line.rstrip(),
                ) from exc
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
        python_text = self._rewrite_overloaded_methods(python_text)
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

    def _rewrite_overloaded_methods(self, python_text: str) -> str:
        lines = python_text.splitlines()
        rewritten: List[str] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            if re.match(r"^class\s+([A-Za-z_]\w*)\s*:", line):
                rewritten.append(line)
                index += 1
                class_lines: List[str] = []
                while index < len(lines):
                    current_line = lines[index]
                    if current_line.strip() and len(current_line) - len(current_line.lstrip(" ")) == 0:
                        break
                    class_lines.append(current_line)
                    index += 1

                transformed_class_lines = self._transform_class_body(class_lines)
                rewritten.extend(transformed_class_lines)
                continue

            rewritten.append(line)
            index += 1
        return "\n".join(rewritten) + "\n"

    def _transform_class_body(self, class_lines: List[str]) -> List[str]:
        segments: List[tuple[str, List[str]]] = []
        index = 0
        while index < len(class_lines):
            line = class_lines[index]
            if line.strip() and re.match(r"^    def\s+([A-Za-z_]\w*)\s*\((.*?)\)\s*:\s*$", line):
                method_lines = [line]
                index += 1
                while index < len(class_lines):
                    next_line = class_lines[index]
                    if next_line.strip() and len(next_line) - len(next_line.lstrip(" ")) <= 4:
                        break
                    method_lines.append(next_line)
                    index += 1
                segments.append(("method", method_lines))
                continue
            segment: List[str] = []
            while index < len(class_lines):
                current = class_lines[index]
                if current.strip() and re.match(r"^    def\s+([A-Za-z_]\w*)\s*\((.*?)\)\s*:\s*$", current):
                    break
                segment.append(current)
                index += 1
            segments.append(("text", segment))

        method_groups: dict[str, List[List[str]]] = {}
        transformed: List[str] = []
        for kind, payload in segments:
            if kind == "text":
                transformed.extend(payload)
                continue
            method_lines = payload
            method_name_match = re.match(r"^    def\s+([A-Za-z_]\w*)\s*\((.*?)\)\s*:\s*$", method_lines[0])
            if not method_name_match:
                transformed.extend(method_lines)
                continue
            method_name = method_name_match.group(1)
            method_groups.setdefault(method_name, []).append(method_lines)

        for kind, payload in segments:
            if kind == "text":
                continue
            method_lines = payload
            method_name_match = re.match(r"^    def\s+([A-Za-z_]\w*)\s*\((.*?)\)\s*:\s*$", method_lines[0])
            if not method_name_match:
                transformed.extend(method_lines)
                continue
            method_name = method_name_match.group(1)
            overloads = method_groups[method_name]
            if len(overloads) == 1:
                transformed.extend(method_lines)
                continue
            overload_index = overloads.index(method_lines)
            if overload_index == 0:
                dispatcher = f"    def {method_name}(self, *args):\n"
                for idx, _ in enumerate(overloads):
                    dispatcher += f"        if len(args) == {idx}:\n"
                    if idx == 0:
                        dispatcher += f"            return self._{method_name}_{idx}()\n"
                    else:
                        dispatcher += f"            return self._{method_name}_{idx}(args[0])\n"
                dispatcher += "        raise TypeError(f\"{method_name}() got an unexpected number of arguments\")\n"
                transformed.append(dispatcher.rstrip("\n"))
            helper_def = method_lines[0].replace(f"def {method_name}", f"def _{method_name}_{overload_index}", 1)
            helper_lines = [helper_def] + method_lines[1:]
            transformed.extend(helper_lines)

        return transformed

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
            # Skip empty lines and comment-only lines
            stripped = line.strip()
            if stripped == "" or stripped.startswith("#"):
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
            m = re.match(r"(?:function|func)\s+(?:(?:int|float|char|string|bool)\s+)?([A-Za-z_]\w*)", line)
            if m:
                self.pending_block_context = ("function", m.group(1))
            else:
                self.pending_block_context = ("function", "")
        elif re.match(
            r"(?:public|private|protected|module)\s+(?:(?:int|float|char|string|bool)\s+)?[A-Za-z_]\w*\s*\(",
            line,
        ):
            m = re.match(
                r"(?:public|private|protected|module)\s+(?:(?:int|float|char|string|bool)\s+)?([A-Za-z_]\w*)\s*\(",
                line,
            )
            self.pending_block_context = ("function", m.group(1) if m else "")
        else:
            self.pending_block_context = None

    def _inside_class(self) -> bool:
        return any(context is not None and context[0] == "class" for context in self.block_context)

    def _directly_inside_class(self) -> bool:
        if not self.block_context:
            return False
        top = self.block_context[-1]
        return top is not None and top[0] == "class"

    def _current_class_name(self) -> str | None:
        for ctx in reversed(self.block_context):
            if ctx is not None and ctx[0] == "class":
                return ctx[1]
        return None

    def _is_subtype(self, child: str, parent: str) -> bool:
        current: str | None = child
        seen: set[str] = set()
        while current:
            if current == parent:
                return True
            if current in seen:
                break
            seen.add(current)
            current = self.class_parents.get(current)
        return False

    def _lookup_member(self, type_name: str, member: str) -> tuple[str | None, str | None]:
        current: str | None = type_name
        seen: set[str] = set()
        while current:
            members = self.class_members.get(current, {})
            if member in members:
                return current, members[member]
            if current in seen:
                break
            seen.add(current)
            current = self.class_parents.get(current)
        return None, None

    def _receiver_type(self, receiver: str) -> str | None:
        if receiver == "this":
            return self._current_class_name()
        if receiver == "super":
            current = self._current_class_name()
            if current is None:
                return None
            return self.class_parents.get(current)
        return self.variable_types.get(receiver)

    def _check_member_access(
        self,
        receiver: str,
        member: str,
        line_number: int,
        raw_line: str,
    ) -> None:
        recv_type = self._receiver_type(receiver)
        if not recv_type:
            return
        defining_cls, access = self._lookup_member(recv_type, member)
        if defining_cls is None or access is None:
            return

        current = self._current_class_name()
        allowed = False
        if access == "public":
            allowed = True
        elif access == "module":
            # Same-file visibility: this transpiler compiles one file at a time.
            allowed = True
        elif access == "private":
            allowed = current == defining_cls
        elif access == "protected":
            allowed = current is not None and self._is_subtype(current, defining_cls)

        if allowed:
            return

        token = f"{receiver}.{member}"
        column = raw_line.find(token) + 1 if token in raw_line else (raw_line.find(member) + 1 if raw_line else 1)
        self._error(
            f"Access denied: '{member}' is {access} in class {defining_cls}.",
            line_number,
            raw_line.rstrip(),
            column if column > 0 else 1,
        )

    def _enforce_expression_member_access(self, line: str, line_number: int, raw_line: str) -> None:
        for match in re.finditer(r"\b(this|super|[A-Za-z_]\w*)\.([A-Za-z_]\w*)\b", line):
            self._check_member_access(match.group(1), match.group(2), line_number, raw_line)

    def _record_class_declaration(self, line: str) -> None:
        inherits = re.match(
            r"class\s+(?P<name>[A-Za-z_]\w*)\s+(?:inherits|super)\s+(?P<parent>[A-Za-z_]\w*)",
            line,
        )
        if inherits:
            name = inherits.group("name")
            self.class_parents[name] = inherits.group("parent")
            self.class_members.setdefault(name, {})
            return
        simple = re.match(r"class\s+(?P<name>[A-Za-z_]\w*)", line)
        if simple:
            name = simple.group("name")
            self.class_parents.setdefault(name, None)
            self.class_members.setdefault(name, {})

    def _record_class_member(self, line: str) -> None:
        if not self._directly_inside_class():
            return
        cls_name = self._current_class_name()
        if not cls_name:
            return

        field = re.fullmatch(
            r"(?P<access>public|private|protected|module)\s+(?:int|float|char|string|bool)\s+(?P<name>[A-Za-z_]\w*)(?:\s*=\s*.+)?",
            line,
        )
        if field:
            self.class_members.setdefault(cls_name, {})[field.group("name")] = field.group("access")
            return

        method = re.fullmatch(
            r"(?P<access>public|private|protected|module)\s+(?:(?:int|float|char|string|bool)\s+)?(?P<name>[A-Za-z_]\w*)\s*\(.*\)",
            line,
        )
        if method and method.group("name") != cls_name:
            self.class_members.setdefault(cls_name, {})[method.group("name")] = method.group("access")

    def _enforce_class_member_access(self, line: str, line_number: int, raw_line: str) -> None:
        if not self._directly_inside_class():
            return
        if re.search(r"\bmethod\b", line):
            token_start = line.find("method")
            column = raw_line.find(line) + token_start + 1 if raw_line else 1
            raise TranspileError(
                "Remove `method`; use an access modifier and optional return type: `public name(args)` or `public string name(args)`.",
                line_number,
                column,
                raw_line.rstrip(),
            )
        if re.fullmatch(r"(?:int|float|char|string|bool)\s+[A-Za-z_]\w*(?:\s*=\s*.+)?", line):
            column = raw_line.find(line) + 1 if raw_line else 1
            raise TranspileError(
                "Class member declarations require an access modifier. Use public/private/protected/module.",
                line_number,
                column,
                raw_line.rstrip(),
            )
        # Methods are identified by parentheses; they still require an access modifier.
        if re.fullmatch(
            r"(?:(?:int|float|char|string|bool)\s+)?[A-Za-z_]\w*\s*\(.*\)\s*(?::\s*)?",
            line,
        ) and not re.match(r"^(?:public|private|protected|module)\b", line):
            column = raw_line.find(line) + 1 if raw_line else 1
            raise TranspileError(
                "Class member declarations require an access modifier. Use public/private/protected/module.",
                line_number,
                column,
                raw_line.rstrip(),
            )

    def _record_declared_variables(self, line: str) -> None:
        primitives = {"int", "float", "char", "string", "bool"}
        for pattern in [
            r"^(?:public|private|protected|module)\s+(?P<type>int|float|char|string|bool)\s+(?P<name>[A-Za-z_]\w*)(?:\s*=\s*.+)?$",
            r"^(?P<type>int|float|char|string|bool)\s+(?P<name>[A-Za-z_]\w*)(?:\s*=\s*.+)?$",
            r"^(?:public|private|protected|module)\s+(?P<type>[A-Za-z_]\w*)\s+(?P<name>[A-Za-z_]\w*)(?:\s*=\s*.+)?$",
            r"^(?P<type>[A-Za-z_]\w*)\s+(?P<name>[A-Za-z_]\w*)(?:\s*=\s*.+)?$",
        ]:
            match = re.fullmatch(pattern, line)
            if match:
                name = match.group("name")
                type_name = match.group("type")
                self.declared_variables.add(name)
                if type_name not in primitives:
                    self.variable_types[name] = type_name
                break

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
        self._record_class_declaration(line)
        self._record_class_member(line)
        self._record_declared_variables(line)
        self._enforce_class_member_access(line, line_number, raw_line)
        self._enforce_expression_member_access(line, line_number, raw_line)

        # Class members with parentheses are constructors/methods (access modifier required).
        if self._directly_inside_class():
            class_function_match = re.fullmatch(
                r"(?:public|private|protected|module)\s+function(?:\s+(?:(?P<rtype>int|float|char|string|bool)\s+))?\s*(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*?)\)\s*(?::\s*)?",
                line,
            )
            if class_function_match:
                token_start = line.find("function")
                column = raw_line.find(line) + token_start + 1 if raw_line else 1
                self._error(
                    "Class methods must not use `function`. Use an access modifier: `public name(args)`.",
                    line_number,
                    raw_line.rstrip(),
                    column,
                )

            plain_function_match = re.fullmatch(
                r"function(?:\s+(?:(?P<rtype>int|float|char|string|bool)\s+))?\s*(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*?)\)\s*(?::\s*)?",
                line,
            )
            if plain_function_match:
                token_start = line.find("function")
                column = raw_line.find(line) + token_start + 1 if raw_line else 1
                self._error(
                    "Class methods must not use `function`. Use an access modifier: `public name(args)`.",
                    line_number,
                    raw_line.rstrip(),
                    column,
                )

            member_fn_match = re.fullmatch(
                r"(?:public|private|protected|module)\s+(?:(?P<rtype>int|float|char|string|bool)\s+)?(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*)\)",
                line,
            )
            if member_fn_match:
                cls_name = self._current_class_name()
                name = member_fn_match.group("name")
                args_raw = member_fn_match.group("args").strip()
                if cls_name and name == cls_name:
                    if not args_raw:
                        return "def __init__(self):"
                    params = []
                    for part in [p.strip() for p in args_raw.split(",") if p.strip()]:
                        m = re.fullmatch(
                            r"(?:(?P<type>int|float|char|string|bool)\s+)?(?P<name>[A-Za-z_]\w*)(?:\s*=\s*(?P<default>.+))?",
                            part,
                        )
                        if not m:
                            pname = re.sub(r"^(int|float|char|string|bool)\s+", "", part).strip()
                            params.append(f"{pname}=None")
                            continue
                        ptype = m.group("type")
                        pname = m.group("name")
                        default = m.group("default")
                        if default is not None:
                            default_val = default.strip()
                        elif ptype:
                            default_val = _default_value_for_type(ptype)
                        else:
                            default_val = "None"
                        params.append(f"{pname}={default_val}")
                    args = "self, " + ", ".join(params)
                    return f"def __init__({args}):"

                args = _strip_type_annotation(args_raw)
                args = f"self, {args}" if args else "self"
                return f"def {name}({args}):"

        assignment_match = re.fullmatch(r"(?P<name>[A-Za-z_]\w*)\s*(?<![=!<>])=\s*(?P<expr>.+)", line)
        if assignment_match:
            name = assignment_match.group("name")
            if name not in self.declared_variables and name not in {"self", "True", "False", "None"}:
                self._error(
                    f"Undeclared variable '{name}'. Variables must be declared with a type before assignment.",
                    line_number,
                    raw_line.rstrip(),
                )

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
