from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import List, NoReturn

from .language_spec import LANGUAGE, _strip_type_annotation, _default_value_for_type

INDENT_SIZE = 4
TOP_LEVEL_VISIBILITY = ("global", "package", "module")


@dataclass
class ModuleInfo:
    path: Path
    python: str
    exports: dict[str, str]
    constants: set[str]
    types: dict[str, str]
    class_parents: dict[str, str | None]
    class_implements: dict[str, list[str]]
    interfaces: set[str]
    class_members: dict[str, dict[str, str]]
    class_methods: dict[str, dict[str, int]]


class TranspileError(ValueError):
    """Raised when source code cannot be transpiled."""

    def __init__(
        self,
        message: str,
        line_number: int | None = None,
        column: int | None = None,
        code_line: str | None = None,
        source_file: Path | None = None,
    ) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.column = column
        self.code_line = code_line
        self.source_file = source_file

    def __str__(self) -> str:
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
    def __init__(
        self,
        source: str,
        *,
        source_path: Path | None = None,
        module_cache: dict[Path, "ModuleInfo"] | None = None,
        transpiling: set[Path] | None = None,
    ) -> None:
        self.source_path = source_path.resolve() if source_path is not None else None
        self.module_cache = module_cache if module_cache is not None else {}
        self.transpiling = transpiling if transpiling is not None else set()
        self.exports: dict[str, str] = {}
        # Names declared with const (immutable after declaration).
        self.constants: set[str] = set()
        # Names brought into scope by import.
        self.imported_names: set[str] = set()
        # Names seen via imported modules but not in scope here:
        # name -> (module_file, visibility, accessible_if_imported)
        self.seen_module_names: dict[str, tuple[str, str, bool]] = {}
        self.raw_lines = source.splitlines()
        self.source_lines = self._preprocess_source(source)
        self.output_lines: List[str] = []
        self.indent_stack: List[int] = [0]
        self.declared_variables: set[str] = set()
        self.variable_types: dict[str, str] = {}
        self.class_members: dict[str, dict[str, str]] = {}
        self.class_parents: dict[str, str | None] = {}
        self.class_methods: dict[str, dict[str, int]] = {}
        self.interface_methods: dict[str, dict[str, int]] = {}
        self.class_implements: dict[str, list[str]] = {}
        self.interfaces: set[str] = set()
        self.generic_type_params: dict[str, list[str]] = {}
        self.needs_abc_import = False
        self.needs_array_import = False
        self.brace_mode = any(line.strip() in {"{", "}"} for line, _ in self.source_lines)
        # block_context holds tuples like ("class", "ClassName"), ("interface", "Name"), or ("function", "name")
        self.block_context: List[tuple[str, str] | None] = [None]
        self.pending_block_context: tuple[str, str] | None = None
        self.loop_counters: list[set[str]] = []
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
                if i + 1 < len(source) and source[i + 1] == "#":
                    # Multiline comment: ## ... /#
                    if current.strip():
                        lines.append((current.rstrip(), current_line_number))
                        current = ""
                    end = source.find("/#", i + 2)
                    if end == -1:
                        self._error(
                            "Unterminated multiline comment. Close with /#.",
                            current_line_number,
                            source[i:].split("\n")[0],
                        )
                    block = source[i:end + 2]
                    current_line_number += block.count("\n")
                    i = end + 2
                    continue
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
                    exc.args[0] if exc.args else str(exc),
                    exc.line_number or original_line_number,
                    exc.column,
                    exc.code_line or raw_line.rstrip(),
                    source_file=exc.source_file or self.source_path,
                ) from exc
            except ValueError as exc:
                column = raw_line.find(stripped) + 1 if raw_line and stripped else 1
                raise TranspileError(str(exc), original_line_number, column, raw_line.rstrip()) from exc
            for output_line in python_line.splitlines():
                self.output_lines.append(" " * indent + output_line)

        if self.brace_mode and len(self.indent_stack) != 1:
            raise TranspileError("Unclosed block at end of file.")

        self._enforce_interface_implementations()

        python_text = "\n".join(self.output_lines) + "\n"
        # Normalize common object references from source language to Python.
        python_text = python_text.replace("this.", "self.")
        python_text = re.sub(r"\btrue\b", "True", python_text)
        python_text = re.sub(r"\bfalse\b", "False", python_text)
        python_text = re.sub(r"\bnull\b", "None", python_text)
        python_text = self._inject_generic_type_assignments(python_text)
        python_text = self._rewrite_overloaded_methods(python_text)
        if self.needs_abc_import:
            python_text = "from abc import ABC, abstractmethod\n" + python_text
        if self.needs_array_import:
            python_text = "from array import array\n" + python_text
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

    def _inject_generic_type_assignments(self, python_text: str) -> str:
        lines = python_text.split("\n")
        result: list[str] = []
        for line in lines:
            result.append(line)
            m = re.match(r"^(\s*)def __init__\(self,.*(__\w+__=object).*\):", line)
            if m:
                indent = m.group(1) + " " * INDENT_SIZE
                kwargs = re.findall(r"__([A-Za-z_]\w*)__=object", line)
                for param in kwargs:
                    result.append(f"{indent}{param} = __{param}__")
        return "\n".join(result)

    def _rewrite_overloaded_methods(self, python_text: str) -> str:
        lines = python_text.splitlines()
        rewritten: List[str] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            if re.match(r"^class\s+([A-Za-z_]\w*)\s*(?:\([^)]*\))?\s*:", line):
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
                has_type_kwargs = any(
                    re.search(r"__\w+__=object", ol[0]) for ol in overloads
                )
                if has_type_kwargs:
                    dispatcher = f"    def {method_name}(self, *args, **kwargs):\n"
                else:
                    dispatcher = f"    def {method_name}(self, *args):\n"
                for idx, overload in enumerate(overloads):
                    header_match = re.match(r"^    def\s+[A-Za-z_]\w*\s*\(self(?:,\s*(?P<params>.*))?\)\s*:", overload[0])
                    param_count = 0
                    if header_match and header_match.group("params"):
                        positional = [p for p in header_match.group("params").split(",")
                                      if p.strip() and "__" not in p]
                        param_count = len(positional)
                    dispatcher += f"        if len(args) == {param_count}:\n"
                    if param_count == 0:
                        fwd = "**kwargs" if has_type_kwargs else ""
                        dispatcher += f"            return self._{method_name}_{idx}({fwd})\n"
                    else:
                        arg_refs = ", ".join(f"args[{j}]" for j in range(param_count))
                        if has_type_kwargs:
                            arg_refs += ", **kwargs"
                        dispatcher += f"            return self._{method_name}_{idx}({arg_refs})\n"
                dispatcher += "        raise TypeError(f\"{method_name}() got an unexpected number of arguments\")\n"
                transformed.append(dispatcher.rstrip("\n"))
            helper_def = method_lines[0].replace(f"def {method_name}", f"def _{method_name}_{overload_index}", 1)
            helper_lines = [helper_def] + method_lines[1:]
            transformed.extend(helper_lines)

        return transformed

    def _open_block(self, line_number: int) -> None:
        if not self.brace_mode:
            self._error("Unexpected opening brace.", line_number, "{")
        if self._directly_inside_interface():
            self._error(
                "Interface methods are abstract and cannot have a body.",
                line_number,
                "{",
            )
        self.indent_stack.append(self.indent_stack[-1] + INDENT_SIZE)
        ctx = self.pending_block_context
        self.block_context.append(ctx)
        self.pending_block_context = None
        if ctx is not None and ctx[0] == "loop":
            self.loop_counters.append({ctx[1]})
        else:
            self.loop_counters.append(set())

    def _close_block(self, line_number: int) -> None:
        if not self.brace_mode:
            self._error("Unexpected closing brace.", line_number, "}")
        if len(self.indent_stack) == 1:
            self._error("Unexpected closing brace.", line_number, "}")
        self.indent_stack.pop()
        if self.loop_counters:
            self.loop_counters.pop()
        if len(self.block_context) > 1:
            self.block_context.pop()

    def _error(self, message: str, line_number: int, line: str, column: int | None = None) -> NoReturn:
        snippet = line.rstrip()
        raise TranspileError(message, line_number, column, snippet, source_file=self.source_path)

    def _enforce_formatting(self) -> None:
        """Raise a Formatting Error if source contains tabs, trailing whitespace,
        or incorrect indentation (when not using brace style)."""
        # When using brace style we still require consistent indentation inside
        # each brace-delimited block. Track expected indent per brace depth.
        expected_indent_by_depth: dict[int, int | None] = {}
        depth = 0
        in_multiline_comment = False
        for idx, line in enumerate(self.raw_lines, start=1):
            stripped = line.strip()
            if in_multiline_comment:
                if "/#" in stripped:
                    in_multiline_comment = False
                continue
            if stripped.startswith("##"):
                if "/#" not in stripped[2:]:
                    in_multiline_comment = True
                continue
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

    def _at_module_level(self) -> bool:
        return len(self.block_context) == 1

    def _split_list_elements(self, literal: str) -> list[str]:
        text = literal.strip()
        if not (text.startswith("[") and text.endswith("]")):
            return []
        inner = text[1:-1].strip()
        if not inner:
            return []
        parts: list[str] = []
        current: list[str] = []
        depth = 0
        in_string = False
        quote = ""
        i = 0
        while i < len(inner):
            ch = inner[i]
            if in_string:
                current.append(ch)
                if ch == "\\" and i + 1 < len(inner):
                    current.append(inner[i + 1])
                    i += 2
                    continue
                if ch == quote:
                    in_string = False
                i += 1
                continue
            if ch in {'"', "'"}:
                in_string = True
                quote = ch
                current.append(ch)
                i += 1
                continue
            if ch in "([{":
                depth += 1
                current.append(ch)
                i += 1
                continue
            if ch in ")]}":
                depth = max(depth - 1, 0)
                current.append(ch)
                i += 1
                continue
            if ch == "," and depth == 0:
                parts.append("".join(current).strip())
                current = []
                i += 1
                continue
            current.append(ch)
            i += 1
        tail = "".join(current).strip()
        if tail:
            parts.append(tail)
        return parts

    def _translate_array_element(self, element_type: str, element: str) -> str:
        value = element.strip()
        if element_type == "bool":
            if value in {"true", "True"}:
                return "1"
            if value in {"false", "False"}:
                return "0"
            raise TranspileError(f"Bool array elements must be true or false, got '{value}'.")
        if element_type == "string":
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                return value
            raise TranspileError(f"String array elements must be string literals, got '{value}'.")
        if element_type == "char":
            if value.startswith("'") and value.endswith("'") and len(value) >= 3:
                return value
            if value.startswith('"') and value.endswith('"') and len(value) == 3:
                return f"'{value[1]}'"
            raise TranspileError(f"Char array elements must be single characters, got '{value}'.")
        if element_type == "int":
            if re.fullmatch(r"-?\d+", value):
                return value
            raise TranspileError(f"Int array elements must be integers, got '{value}'.")
        if element_type == "float":
            if re.fullmatch(r"-?\d+(?:\.\d+)?", value):
                return value
            raise TranspileError(f"Float array elements must be numbers, got '{value}'.")
        raise TranspileError(f"Unsupported array element type '{element_type}'.")

    def _translate_array_declaration(
        self, line: str, line_number: int, raw_line: str
    ) -> str | None:
        match = re.fullmatch(
            r"(?P<type>int|float|char|string|bool)\[(?P<size>\d*)\]\s+"
            r"(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)",
            line,
        )
        if not match:
            return None

        element_type = match.group("type")
        size_text = match.group("size")
        name = match.group("name")
        expr = match.group("expr").strip()
        if not expr.startswith("[") or not expr.endswith("]"):
            self._error(
                f"Array '{name}' must be initialized with a list literal like `[{element_type} values...]`.",
                line_number,
                raw_line.rstrip(),
            )
        elements = self._split_list_elements(expr)

        if size_text:
            expected = int(size_text)
            if len(elements) > expected:
                self._error(
                    "Array index out of bounds, trying to place a value outside the array "
                    f"(capacity {expected}, got {len(elements)} values).",
                    line_number,
                    raw_line.rstrip(),
                )
            if len(elements) != expected:
                self._error(
                    f"Array '{name}' expects exactly {expected} elements, got {len(elements)}.",
                    line_number,
                    raw_line.rstrip(),
                )

        translated_elements: list[str] = []
        for element in elements:
            try:
                translated_elements.append(self._translate_array_element(element_type, element))
            except TranspileError as exc:
                self._error(exc.args[0] if exc.args else str(exc), line_number, raw_line.rstrip())

        self.declared_variables.add(name)
        self.variable_types[name] = f"{element_type}[]"

        # string[] cannot use array.array (elements are objects); numeric/bool/char use stdlib array.
        if element_type == "string":
            return f"{name} = [{', '.join(translated_elements)}]"

        typecodes = {"int": "i", "float": "d", "bool": "b", "char": "u"}
        typecode = typecodes[element_type]
        self.needs_array_import = True
        if translated_elements:
            return f"{name} = array('{typecode}', [{', '.join(translated_elements)}])"
        return f"{name} = array('{typecode}')"

    def _strip_top_level_visibility(self, line: str) -> tuple[str | None, str]:
        match = re.match(
            r"^(?P<vis>global|package|module)\s+(?=function\b|func\b|class\b|interface\b|const\b)",
            line,
        )
        if not match:
            return None, line
        return match.group("vis"), line[match.end() :].lstrip()

    def _record_top_level_export(self, line: str) -> None:
        if not self._at_module_level():
            return
        visibility, rest = self._strip_top_level_visibility(line)
        if visibility is None:
            rest = line
            visibility = "module"
        match = re.match(
            r"(?:function|func)\s+(?:(?:int|float|char|string|bool)\s+)?(?P<name>[A-Za-z_]\w*)\s*\(",
            rest,
        )
        if not match:
            match = re.match(r"(?:class|interface)\s+(?P<name>[A-Za-z_]\w*)\b", rest)
        if not match:
            match = re.match(
                r"const\s+(?:int|float|char|string|bool)\s+(?P<name>[A-Za-z_]\w*)\s*=",
                rest,
            )
        if match:
            self.exports[match.group("name")] = visibility

    def _resolve_module_path(self, module_ref: str, line_number: int, raw_line: str) -> Path:
        ref = module_ref.strip().strip("\"'")
        if not ref:
            self._error("Import module path is empty.", line_number, raw_line.rstrip())
        path = Path(ref)
        if path.suffix.lower() != ".pys":
            path = path.with_suffix(".pys")
        if not path.is_absolute():
            base = self.source_path.parent if self.source_path is not None else Path.cwd()
            path = (base / path).resolve()
        else:
            path = path.resolve()
        if not path.exists():
            self._error(
                f"Cannot find module '{module_ref}'. Expected file: {path}",
                line_number,
                raw_line.rstrip(),
            )
        return path

    def _same_package(self, other: Path) -> bool:
        if self.source_path is None:
            return False
        return self.source_path.parent.resolve() == other.parent.resolve()

    def _load_module(self, module_path: Path) -> ModuleInfo:
        path = module_path.resolve()
        if path in self.module_cache:
            return self.module_cache[path]
        if path in self.transpiling:
            raise TranspileError(f"Circular import involving '{path.name}'.")
        self.transpiling.add(path)
        try:
            source = path.read_text(encoding="utf-8")
            child = Parser(
                source,
                source_path=path,
                module_cache=self.module_cache,
                transpiling=self.transpiling,
            )
            python = child.parse()
            info = ModuleInfo(
                path=path,
                python=python,
                exports=dict(child.exports),
                constants=set(child.constants),
                types={
                    name: child.variable_types[name]
                    for name in child.exports
                    if name in child.variable_types
                },
                class_parents=dict(child.class_parents),
                class_implements=dict(child.class_implements),
                interfaces=set(child.interfaces),
                class_members=dict(child.class_members),
                class_methods=dict(child.class_methods),
            )
            self.module_cache[path] = info
            return info
        finally:
            self.transpiling.discard(path)

    def _visible_exports_for_import(self, info: ModuleInfo) -> list[str]:
        names: list[str] = []
        for name, visibility in info.exports.items():
            if visibility == "module":
                continue
            if visibility == "package" and not self._same_package(info.path):
                continue
            if visibility in {"package", "global"}:
                names.append(name)
        return sorted(names)

    def _record_seen_module_exports(
        self,
        info: ModuleInfo,
        imported: list[str],
    ) -> None:
        visible = set(self._visible_exports_for_import(info))
        imported_set = set(imported)
        for name in imported_set:
            self.imported_names.add(name)
            self.declared_variables.add(name)
            if name in info.types:
                self.variable_types[name] = info.types[name]
            if name in info.constants:
                self.constants.add(name)
            self.seen_module_names.pop(name, None)
        for name, visibility in info.exports.items():
            accessible = name in visible
            if name in imported_set:
                continue
            # Prefer keeping an existing "more useful" record (already inaccessible from another module).
            if name in self.imported_names or name in self.exports:
                continue
            self.seen_module_names[name] = (info.path.name, visibility, accessible)
        # Merge class hierarchy so polymorphism checks work across modules.
        # Transitively include parents and interfaces referenced by imported names.
        to_merge: set[str] = set(imported_set)
        merged: set[str] = set()
        while to_merge:
            name = to_merge.pop()
            if name in merged:
                continue
            merged.add(name)
            if name in info.class_parents:
                self.class_parents[name] = info.class_parents[name]
                parent = info.class_parents[name]
                if parent and parent not in merged:
                    to_merge.add(parent)
            if name in info.class_implements:
                self.class_implements[name] = info.class_implements[name]
                for iface in info.class_implements[name]:
                    if iface not in merged:
                        to_merge.add(iface)
            if name in info.interfaces:
                self.interfaces.add(name)
            if name in info.class_members:
                self.class_members[name] = info.class_members[name]
            if name in info.class_methods:
                self.class_methods[name] = info.class_methods[name]

    def _enforce_seen_name_access(self, line: str, line_number: int, raw_line: str) -> None:
        builtins = {
            "print",
            "str",
            "int",
            "float",
            "bool",
            "len",
            "range",
            "super",
            "ABC",
            "abstractmethod",
        }
        for match in re.finditer(r"(?<!\.)\b([A-Za-z_]\w*)\s*\(", line):
            name = match.group(1)
            if name in builtins:
                continue
            if name in self.imported_names or name in self.exports:
                continue
            if name in self.declared_variables:
                continue
            if name in self.class_parents or name in self.interfaces:
                continue
            if name not in self.seen_module_names:
                continue
            module_file, visibility, accessible = self.seen_module_names[name]
            column = raw_line.find(name) + 1 if raw_line else 1
            if accessible:
                self._error(
                    f"'{name}' is defined in {module_file} but was not imported. "
                    f"Import it with `import {name} from {module_file}` or `import all from {module_file}`.",
                    line_number,
                    raw_line.rstrip(),
                    column,
                )
            where = {
                "module": "only within its own module",
                "package": "only within its package (same folder)",
                "global": "across the whole project",
            }.get(visibility, f"as {visibility}")
            self._error(
                f"Access denied: '{name}' is defined in {module_file} but is not accessible here "
                f"({visibility}-scoped, visible {where}).",
                line_number,
                raw_line.rstrip(),
                column,
            )

    def _translate_import_statement(self, line: str, line_number: int, raw_line: str) -> str | None:
        import_all = re.fullmatch(r"import\s+all\s+from\s+(?P<module>.+)", line)
        import_name = re.fullmatch(r"import\s+(?P<name>[A-Za-z_]\w*)\s+from\s+(?P<module>.+)", line)
        import_module = re.fullmatch(r"import\s+(?P<module>.+)", line)
        if not (import_all or import_name or import_module):
            return None

        if self.source_path is None:
            # Keep naive translation for string-only transpile calls/tests.
            return None

        if import_all:
            module_ref = import_all.group("module")
            names = None
        elif import_name and import_name.group("name") != "all":
            module_ref = import_name.group("module")
            names = [import_name.group("name")]
        elif import_module:
            module_ref = import_module.group("module")
            names = None
        else:
            return None

        module_path = self._resolve_module_path(module_ref, line_number, raw_line)
        info = self._load_module(module_path)
        visible = self._visible_exports_for_import(info)
        module_name = module_path.stem

        if names is None:
            if not visible:
                self._error(
                    f"Module '{module_path.name}' has no global/package exports visible here.",
                    line_number,
                    raw_line.rstrip(),
                )
            self._record_seen_module_exports(info, visible)
            return f"from {module_name} import {', '.join(visible)}"

        selected: list[str] = []
        for name in names:
            if name not in info.exports:
                self._error(
                    f"'{name}' is not defined in module '{module_path.name}'.",
                    line_number,
                    raw_line.rstrip(),
                )
            visibility = info.exports[name]
            if name not in visible:
                where = "this package" if visibility == "package" else "this module"
                self._error(
                    f"Cannot import '{name}' from '{module_path.name}': it is {visibility}-scoped "
                    f"(visible only in {where}).",
                    line_number,
                    raw_line.rstrip(),
                )
            selected.append(name)
        self._record_seen_module_exports(info, selected)
        return f"from {module_name} import {', '.join(selected)}"

    def _set_pending_block_context(self, line: str) -> None:
        # Record the incoming block type and name so the open block can store it.
        _, rest = self._strip_top_level_visibility(line)
        if rest.startswith("interface "):
            m = re.match(r"interface\s+([A-Za-z_]\w*)", rest)
            if m:
                self.pending_block_context = ("interface", m.group(1))
            else:
                self.pending_block_context = ("interface", "")
        elif rest.startswith("class "):
            m = re.match(r"class\s+([A-Za-z_]\w*)", rest)
            if m:
                self.pending_block_context = ("class", m.group(1))
            else:
                self.pending_block_context = ("class", "")
        elif rest.startswith("function ") or rest.startswith("func "):
            m = re.match(r"(?:function|func)\s+(?:(?:int|float|char|string|bool)\s+)?([A-Za-z_]\w*)", rest)
            if m:
                self.pending_block_context = ("function", m.group(1))
            else:
                self.pending_block_context = ("function", "")
        elif re.match(
            r"(?:public|private|protected|module)\s+(?:(?:int|float|char|string|bool)\s+)?[A-Za-z_]\w*\s*\(",
            line,
        ):
            # Abstract interface methods have no body block.
            if self._directly_inside_interface():
                self.pending_block_context = None
            else:
                m = re.match(
                    r"(?:public|private|protected|module)\s+(?:(?:int|float|char|string|bool)\s+)?([A-Za-z_]\w*)\s*\(",
                    line,
                )
                self.pending_block_context = ("function", m.group(1) if m else "")
        elif rest.startswith("loop"):
            m = re.match(
                r"loop\s*\(\s*(?:(?:int|float|char|string|bool)\s+)?(?P<var>[A-Za-z_]\w*)\s*=\s*[^,]+,",
                rest,
            )
            if m:
                self.pending_block_context = ("loop", m.group("var"))
            else:
                self.pending_block_context = None
        else:
            self.pending_block_context = None

    def _inside_class(self) -> bool:
        return any(context is not None and context[0] == "class" for context in self.block_context)

    def _directly_inside_class(self) -> bool:
        if not self.block_context:
            return False
        top = self.block_context[-1]
        return top is not None and top[0] == "class"

    def _directly_inside_interface(self) -> bool:
        if not self.block_context:
            return False
        top = self.block_context[-1]
        return top is not None and top[0] == "interface"

    def _current_class_name(self) -> str | None:
        for ctx in reversed(self.block_context):
            if ctx is not None and ctx[0] in {"class", "interface"}:
                return ctx[1]
        return None

    @staticmethod
    def _param_arity(args_raw: str) -> int:
        parts = [part.strip() for part in args_raw.split(",") if part.strip()]
        return len(parts)

    def _all_class_methods(self, class_name: str) -> dict[str, int]:
        methods: dict[str, int] = {}
        current: str | None = class_name
        seen: set[str] = set()
        chain: list[str] = []
        while current and current not in seen:
            chain.append(current)
            seen.add(current)
            current = self.class_parents.get(current)
        for name in reversed(chain):
            methods.update(self.class_methods.get(name, {}))
        return methods

    def _enforce_interface_implementations(self) -> None:
        for class_name, interfaces in self.class_implements.items():
            available = self._all_class_methods(class_name)
            for interface_name in interfaces:
                if interface_name not in self.interfaces:
                    raise TranspileError(
                        f"Unknown interface '{interface_name}' implemented by class {class_name}."
                    )
                required = self.interface_methods.get(interface_name, {})
                for method_name, arity in required.items():
                    if method_name not in available:
                        raise TranspileError(
                            f"Class {class_name} must implement abstract method "
                            f"'{method_name}' from interface {interface_name}."
                        )
                    if available[method_name] != arity:
                        raise TranspileError(
                            f"Class {class_name} method '{method_name}' does not match "
                            f"interface {interface_name} (expected {arity} parameter(s), "
                            f"found {available[method_name]})."
                        )

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

    def _type_implements(self, type_name: str, interface_name: str) -> bool:
        if interface_name not in self.interfaces:
            return False
        current: str | None = type_name
        seen: set[str] = set()
        while current and current not in seen:
            if interface_name in self.class_implements.get(current, []):
                return True
            seen.add(current)
            current = self.class_parents.get(current)
        return False

    def _is_assignable_to(self, actual: str, declared: str) -> bool:
        """Java-style: actual may be a subtype/implementer of declared."""
        if actual == declared:
            return True
        primitives = {"int", "float", "char", "string", "bool"}
        if declared in primitives or actual in primitives:
            return False
        if self._is_subtype(actual, declared):
            return True
        if self._type_implements(actual, declared):
            return True
        return False

    def _lookup_member(self, type_name: str, member: str) -> tuple[str | None, str | None]:
        current: str | None = type_name
        seen: set[str] = set()
        while current:
            members = self.class_members.get(current, {})
            if member in members:
                return current, members[member]
            # Interface members are also visible through the declared interface type.
            for iface in self.class_implements.get(current, []):
                iface_members = self.class_members.get(iface, {})
                if member in iface_members:
                    return iface, iface_members[member]
            if current in seen:
                break
            seen.add(current)
            current = self.class_parents.get(current)
        if type_name in self.interfaces:
            members = self.class_members.get(type_name, {})
            if member in members:
                return type_name, members[member]
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
        token = f"{receiver}.{member}"
        column = raw_line.find(token) + 1 if token in raw_line else (raw_line.find(member) + 1 if raw_line else 1)
        if defining_cls is None or access is None:
            known_type = (
                recv_type in self.class_members
                or recv_type in self.interfaces
                or recv_type in self.class_parents
            )
            if known_type:
                self._error(
                    f"'{member}' is not a member of declared type {recv_type}.",
                    line_number,
                    raw_line.rstrip(),
                    column if column > 0 else 1,
                )
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

        self._error(
            f"Access denied: '{member}' is {access} in class {defining_cls}.",
            line_number,
            raw_line.rstrip(),
            column if column > 0 else 1,
        )

    def _enforce_expression_member_access(self, line: str, line_number: int, raw_line: str) -> None:
        for match in re.finditer(r"\b(this|super|[A-Za-z_]\w*)\.([A-Za-z_]\w*)\b", line):
            self._check_member_access(match.group(1), match.group(2), line_number, raw_line)

    def _strip_generic_params(self, line: str) -> str:
        """Strip <T, U> from class declarations, recording type params."""
        m = re.match(r"((?:(?:global|package|module)\s+)?class\s+[A-Za-z_]\w*)\s*<([^>]+)>(.*)", line)
        if not m:
            return line
        class_match = re.match(r"(?:(?:global|package|module)\s+)?class\s+([A-Za-z_]\w*)", m.group(1))
        if class_match:
            class_name = class_match.group(1)
            params = [p.strip() for p in m.group(2).split(",") if p.strip()]
            self.generic_type_params[class_name] = params
        return m.group(1) + m.group(3)

    def _rewrite_generic_type_args(self, line: str) -> str:
        """Rewrite generic type args: strip from type positions, inject into constructor calls."""
        def _replace_constructor(m: re.Match[str]) -> str:
            class_name = m.group(1)
            type_args = [t.strip() for t in m.group(2).split(",")]
            rest = m.group(3) or ""
            params = self.generic_type_params.get(class_name, [])
            if params and rest.startswith("("):
                inner = rest[1:].rstrip(")")
                kwargs = ", ".join(f"__{p}__={a}" for p, a in zip(params, type_args))
                if inner.strip():
                    return f"{class_name}({inner}, {kwargs})"
                return f"{class_name}({kwargs})"
            return f"{class_name}{rest}"

        line = re.sub(
            r"\b([A-Za-z_]\w*)<([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)>(\(.*\))?",
            _replace_constructor,
            line,
        )
        # Strip any remaining generic type annotations (e.g. in type positions of declarations)
        line = re.sub(r"<[A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*>", "", line)
        return line

    def _is_type_param(self, type_name: str) -> bool:
        cls = self._current_class_name()
        if cls and cls in self.generic_type_params:
            return type_name in self.generic_type_params[cls]
        return False

    def _record_class_declaration(self, line: str) -> None:
        _, line = self._strip_top_level_visibility(line)
        interface = re.match(r"interface\s+(?P<name>[A-Za-z_]\w*)", line)
        if interface:
            name = interface.group("name")
            self.interfaces.add(name)
            self.interface_methods.setdefault(name, {})
            self.class_members.setdefault(name, {})
            self.needs_abc_import = True
            return

        inherits_implements = re.match(
            r"class\s+(?P<name>[A-Za-z_]\w*)\s+(?:inherits|super)\s+(?P<parent>[A-Za-z_]\w*)\s+implements\s+(?P<interfaces>.+)",
            line,
        )
        if inherits_implements:
            name = inherits_implements.group("name")
            self.class_parents[name] = inherits_implements.group("parent")
            self.class_members.setdefault(name, {})
            self.class_methods.setdefault(name, {})
            self.class_implements[name] = [
                part.strip()
                for part in inherits_implements.group("interfaces").split(",")
                if part.strip()
            ]
            return

        implements = re.match(
            r"class\s+(?P<name>[A-Za-z_]\w*)\s+implements\s+(?P<interfaces>.+)",
            line,
        )
        if implements:
            name = implements.group("name")
            self.class_parents.setdefault(name, None)
            self.class_members.setdefault(name, {})
            self.class_methods.setdefault(name, {})
            self.class_implements[name] = [
                part.strip() for part in implements.group("interfaces").split(",") if part.strip()
            ]
            return

        inherits = re.match(
            r"class\s+(?P<name>[A-Za-z_]\w*)\s+(?:inherits|super)\s+(?P<parent>[A-Za-z_]\w*)",
            line,
        )
        if inherits:
            name = inherits.group("name")
            self.class_parents[name] = inherits.group("parent")
            self.class_members.setdefault(name, {})
            self.class_methods.setdefault(name, {})
            return
        simple = re.match(r"class\s+(?P<name>[A-Za-z_]\w*)", line)
        if simple:
            name = simple.group("name")
            self.class_parents.setdefault(name, None)
            self.class_members.setdefault(name, {})
            self.class_methods.setdefault(name, {})

    def _record_class_member(self, line: str) -> None:
        if self._directly_inside_interface():
            iface_name = self._current_class_name()
            if not iface_name:
                return
            field = re.fullmatch(
                r"(?P<access>public|private|protected|module)\s+(?:int|float|char|string|bool)\s+(?P<name>[A-Za-z_]\w*)(?:\s*=\s*.+)?",
                line,
            )
            if field:
                raise TranspileError(
                    "Interfaces may only declare abstract methods, not fields.",
                    code_line=line,
                )
            method = re.fullmatch(
                r"(?P<access>public|private|protected|module)\s+(?:(?:int|float|char|string|bool)\s+)?(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*)\)",
                line,
            )
            if method:
                if method.group("access") != "public":
                    raise TranspileError(
                        "Interface methods must be public.",
                        code_line=line,
                    )
                arity = self._param_arity(method.group("args"))
                self.interface_methods.setdefault(iface_name, {})[method.group("name")] = arity
                self.class_members.setdefault(iface_name, {})[method.group("name")] = "public"
            return

        if not self._directly_inside_class():
            return
        cls_name = self._current_class_name()
        if not cls_name:
            return

        field = re.fullmatch(
            r"(?P<access>public|private|protected|module)\s+(?:[A-Za-z_]\w*(?:\[\])?)\s+(?P<name>[A-Za-z_]\w*)(?:\s*=\s*.+)?",
            line,
        )
        if field:
            self.class_members.setdefault(cls_name, {})[field.group("name")] = field.group("access")
            return

        method = re.fullmatch(
            r"(?P<access>public|private|protected|module)\s+(?:(?:[A-Za-z_]\w*(?:\[\])?)\s+)?(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*)\)",
            line,
        )
        if method and method.group("name") != cls_name:
            self.class_members.setdefault(cls_name, {})[method.group("name")] = method.group("access")
            self.class_methods.setdefault(cls_name, {})[method.group("name")] = self._param_arity(
                method.group("args")
            )

    def _enforce_class_member_access(self, line: str, line_number: int, raw_line: str) -> None:
        if not (self._directly_inside_class() or self._directly_inside_interface()):
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

    def _is_compile_time_const_expr(self, expr: str) -> bool:
        expr = expr.strip()
        if not expr:
            return False
        if (expr.startswith('"') and expr.endswith('"')) or (
            expr.startswith("'") and expr.endswith("'") and len(expr) >= 2
        ):
            return True
        if re.fullmatch(r"\d+(?:\.\d+)?", expr):
            return True
        if expr in {"true", "false", "True", "False", "null", "None"}:
            return True
        if re.fullmatch(r"[A-Za-z_]\w*", expr):
            return expr in self.constants
        if expr.startswith("(") and expr.endswith(")"):
            return self._is_compile_time_const_expr(expr[1:-1])
        cast = re.fullmatch(r"\(\s*(?:int|float|char|string|bool)\s*\)\s*(?P<inner>.+)", expr)
        if cast:
            return self._is_compile_time_const_expr(cast.group("inner"))
        if expr.startswith(("+", "-")):
            return self._is_compile_time_const_expr(expr[1:])
        binop = re.fullmatch(r"(?P<left>.+?)\s*(?:\+|\-|\*|/|%)\s*(?P<right>.+)", expr)
        if binop:
            return self._is_compile_time_const_expr(binop.group("left")) and self._is_compile_time_const_expr(
                binop.group("right")
            )
        return False

    def _match_const_decl(self, line: str) -> re.Match[str] | None:
        return re.fullmatch(
            r"(?:(?P<vis>global|package|module)\s+)?const\s+(?P<type>int|float|char|string|bool)\s+"
            r"(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)",
            line,
        )

    def _enforce_const_declaration(self, line: str, line_number: int, raw_line: str) -> None:
        const_match = self._match_const_decl(line)
        if not const_match:
            if re.match(r"^(?:(?:global|package|module)\s+)?const\b", line):
                self._error(
                    "Invalid const declaration; expected `const <type> name = compile-time value` "
                    "(optional visibility: global/package/module).",
                    line_number,
                    raw_line.rstrip(),
                )
            return

        name = const_match.group("name")
        type_name = const_match.group("type")
        expr = const_match.group("expr").strip()
        if not self._is_compile_time_const_expr(expr):
            column = raw_line.find(expr) + 1 if raw_line and expr in raw_line else 1
            self._error(
                f"Const '{name}' must be initialized with a compile-time constant expression.",
                line_number,
                raw_line.rstrip(),
                column,
            )

        inferred = self._infer_expr_type(expr)
        if inferred is not None and not self._is_assignable_to(inferred, type_name):
            column = raw_line.find(name) + 1 if raw_line else 1
            self._error(
                f"Type mismatch: cannot assign {inferred} to const '{name}' of type {type_name}.",
                line_number,
                raw_line.rstrip(),
                column,
            )

        self.declared_variables.add(name)
        self.variable_types[name] = type_name
        self.constants.add(name)

    def _enforce_const_assignment(self, line: str, line_number: int, raw_line: str) -> None:
        if self._match_const_decl(line):
            return
        assign = re.fullmatch(r"(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)", line)
        if not assign:
            return
        name = assign.group("name")
        if name not in self.constants:
            return
        column = raw_line.find(name) + 1 if raw_line else 1
        self._error(
            f"Cannot assign to const '{name}'. Constants are fixed at compile time.",
            line_number,
            raw_line.rstrip(),
            column,
        )

    def _record_declared_variables(self, line: str) -> None:
        primitives = {"int", "float", "char", "string", "bool"}

        const_match = self._match_const_decl(line)
        if const_match:
            name = const_match.group("name")
            self.declared_variables.add(name)
            self.variable_types[name] = const_match.group("type")
            self.constants.add(name)
            return

        var_match = re.fullmatch(r"var\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)", line)
        if var_match:
            name = var_match.group("name")
            expr = var_match.group("expr").strip()
            inferred = self._infer_expr_type(expr)
            self.declared_variables.add(name)
            if inferred:
                self.variable_types[name] = inferred
            return

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
                if type_name in {"const", "global", "package", "module", "var", "function", "func", "class", "interface"}:
                    return
                self.declared_variables.add(name)
                self.variable_types[name] = type_name
                break

    def _infer_expr_type(self, expr: str) -> str | None:
        expr = expr.strip()
        if not expr:
            return None

        if (expr.startswith('"') and expr.endswith('"')) or (
            expr.startswith("'") and expr.endswith("'") and len(expr) >= 2
        ):
            if expr.startswith("'") and len(expr) == 3:
                return "char"
            return "string"

        if re.fullmatch(r"\d+", expr):
            return "int"
        if re.fullmatch(r"\d+\.\d+", expr):
            return "float"
        if expr in {"true", "false", "True", "False"}:
            return "bool"
        if expr in {"null", "None"}:
            return None

        cast = re.fullmatch(r"\(\s*(?P<type>[A-Za-z_]\w*)\s*\)\s*(?P<inner>.+)", expr)
        if cast:
            return cast.group("type")

        ctor = re.fullmatch(r"(?P<type>[A-Za-z_]\w*)\s*\(.*\)", expr)
        if ctor and (
            ctor.group("type") in self.class_members or ctor.group("type") in self.interfaces
        ):
            return ctor.group("type")

        if re.fullmatch(r"[A-Za-z_]\w*", expr):
            return self.variable_types.get(expr)

        member = re.fullmatch(r"(?P<recv>this|super|[A-Za-z_]\w*)\.(?P<name>[A-Za-z_]\w*)", expr)
        if member:
            # Field value types are not tracked yet; only class identity for receivers.
            return None

        binop = re.fullmatch(r"(?P<left>.+?)\s*(?P<op>\+|\-|\*|/|%)\s*(?P<right>.+)", expr)
        if binop:
            left_t = self._infer_expr_type(binop.group("left"))
            right_t = self._infer_expr_type(binop.group("right"))
            if binop.group("op") == "+" and (left_t == "string" or right_t == "string"):
                return "string"
            if left_t == "float" or right_t == "float":
                return "float"
            if left_t == "int" and right_t == "int":
                return "int"
            return None

        return None

    def _enforce_assignment_type(self, line: str, line_number: int, raw_line: str) -> None:
        # Declarations establish type elsewhere; only check plain reassignments here.
        if re.match(
            r"^(?:var|const|global|package|module|public|private|protected|int|float|char|string|bool)\b",
            line,
        ):
            return
        if re.match(r"^[A-Za-z_]\w*\s+[A-Za-z_]\w*\s*=", line):
            return

        assign = re.fullmatch(r"(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)", line)
        if not assign:
            return

        name = assign.group("name")
        declared = self.variable_types.get(name)
        if not declared:
            return

        expr = assign.group("expr").strip()
        inferred = self._infer_expr_type(expr)
        if inferred is None:
            return
        if self._is_assignable_to(inferred, declared):
            return

        column = raw_line.find(name) + 1 if raw_line else 1
        self._error(
            f"Type mismatch: cannot assign {inferred} to '{name}' of type {declared}.",
            line_number,
            raw_line.rstrip(),
            column,
        )

    def _enforce_loop_counter_immutability(self, line: str, line_number: int, raw_line: str) -> None:
        if not self.loop_counters:
            return
        active = set()
        for counters in self.loop_counters:
            active |= counters
        if not active:
            return
        for var in active:
            if re.match(rf"^{re.escape(var)}\s*=\s*", line):
                column = raw_line.find(var) + 1 if raw_line else 1
                self._error(
                    f"Loop counter '{var}' is immutable and cannot be modified inside the loop.",
                    line_number, raw_line.rstrip(), column,
                )
            if re.match(rf"^{re.escape(var)}\s*(\+\+|--|(\+|-)\s*=)", line):
                column = raw_line.find(var) + 1 if raw_line else 1
                self._error(
                    f"Loop counter '{var}' is immutable and cannot be modified inside the loop.",
                    line_number, raw_line.rstrip(), column,
                )

    def _enforce_typed_interpolation(self, line: str, line_number: int, raw_line: str) -> None:
        spec_to_types: dict[str, set[str]] = {
            "s": {"string"},
            "i": {"int"},
            "f": {"float"},
            "c": {"char"},
            "b": {"bool"},
            "o": set(),  # any non-primitive (class/interface)
        }
        primitives = {"int", "float", "char", "string", "bool"}

        for m in re.finditer(r"#([sficbo])\{([^}]+)\}", line):
            spec = m.group(1)
            expr = m.group(2).strip()
            var_type = self._infer_expr_type(expr) or self.variable_types.get(expr)
            if var_type is None:
                continue
            allowed = spec_to_types[spec]
            if spec == "o":
                if var_type in primitives:
                    column = raw_line.find(m.group(0)) + 1 if raw_line else 1
                    self._error(
                        f"Typed interpolation #o{{}} requires an object type, but '{expr}' is {var_type}.",
                        line_number, raw_line.rstrip(), column,
                    )
            elif var_type not in allowed:
                spec_label = {"s": "string", "i": "int", "f": "float", "c": "char", "b": "bool"}[spec]
                column = raw_line.find(m.group(0)) + 1 if raw_line else 1
                self._error(
                    f"Typed interpolation #{spec}{{}} requires {spec_label}, but '{expr}' is {var_type}.",
                    line_number, raw_line.rstrip(), column,
                )

    def _enforce_var_initializer_type(self, line: str, line_number: int, raw_line: str) -> None:
        var_match = re.fullmatch(r"var\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)", line)
        if var_match:
            if self._infer_expr_type(var_match.group("expr").strip()) is not None:
                return
            column = raw_line.find("var") + 1 if raw_line else 1
            self._error(
                f"Cannot infer type for '{var_match.group('name')}'; initialize var with a typed expression.",
                line_number,
                raw_line.rstrip(),
                column,
            )
            return

        typed = re.fullmatch(
            r"(?P<type>[A-Za-z_]\w*)\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)",
            line,
        )
        if not typed:
            return
        type_name = typed.group("type")
        reserved = {
            "var",
            "let",
            "function",
            "func",
            "class",
            "interface",
            "if",
            "else",
            "loop",
            "unless",
            "return",
            "import",
            "from",
            "all",
            "public",
            "private",
            "protected",
            "module",
            "const",
            "global",
            "package",
        }
        if type_name in reserved:
            return
        inferred = self._infer_expr_type(typed.group("expr").strip())
        if inferred is None or self._is_assignable_to(inferred, type_name):
            return
        column = raw_line.find(typed.group("name")) + 1 if raw_line else 1
        self._error(
            f"Type mismatch: cannot assign {inferred} to '{typed.group('name')}' of type {type_name}.",
            line_number,
            raw_line.rstrip(),
            column,
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

        imported = self._translate_import_statement(line, line_number, raw_line)
        if imported is not None:
            return imported

        array_decl = self._translate_array_declaration(line, line_number, raw_line)
        if array_decl is not None:
            return array_decl

        line = self._strip_generic_params(line)
        line = self._rewrite_generic_type_args(line)
        self._record_top_level_export(line)
        self._set_pending_block_context(line)
        self._record_class_declaration(line)
        self._record_class_member(line)
        self._record_declared_variables(line)
        self._enforce_const_declaration(line, line_number, raw_line)
        self._enforce_const_assignment(line, line_number, raw_line)
        self._enforce_class_member_access(line, line_number, raw_line)
        self._enforce_expression_member_access(line, line_number, raw_line)
        self._enforce_seen_name_access(line, line_number, raw_line)
        self._enforce_loop_counter_immutability(line, line_number, raw_line)
        self._enforce_typed_interpolation(line, line_number, raw_line)
        self._enforce_var_initializer_type(line, line_number, raw_line)
        self._enforce_assignment_type(line, line_number, raw_line)

        if re.match(r"^let\b", line):
            column = raw_line.find("let") + 1 if raw_line else 1
            self._error(
                "Use `var` instead of `let` for type-inferred variables.",
                line_number,
                raw_line.rstrip(),
                column,
            )

        # Class members with parentheses are constructors/methods (access modifier required).
        if self._directly_inside_interface():
            member_fn_match = re.fullmatch(
                r"(?:public|private|protected|module)\s+(?:(?P<rtype>int|float|char|string|bool)\s+)?(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*)\)",
                line,
            )
            if member_fn_match:
                name = member_fn_match.group("name")
                args_raw = member_fn_match.group("args").strip()
                args = _strip_type_annotation(args_raw)
                args = f"self, {args}" if args else "self"
                self.needs_abc_import = True
                return (
                    f"@abstractmethod\n"
                    f"def {name}({args}):\n"
                    f"{' ' * INDENT_SIZE}pass"
                )
            self._error(
                "Interfaces may only declare abstract methods.",
                line_number,
                raw_line.rstrip(),
            )

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
                r"(?:public|private|protected|module)\s+(?:(?P<rtype>[A-Za-z_]\w*(?:\[\])?)\s+)?(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*)\)",
                line,
            )
            if member_fn_match:
                cls_name = self._current_class_name()
                name = member_fn_match.group("name")
                args_raw = member_fn_match.group("args").strip()
                if cls_name and name == cls_name:
                    type_params = self.generic_type_params.get(cls_name, [])
                    type_kwargs = [f"__{p}__=object" for p in type_params]
                    if not args_raw:
                        if type_kwargs:
                            return f"def __init__(self, {', '.join(type_kwargs)}):"
                        return "def __init__(self):"
                    params = []
                    for part in [p.strip() for p in args_raw.split(",") if p.strip()]:
                        m = re.fullmatch(
                            r"(?:(?P<type>[A-Za-z_]\w*(?:\[\])?)\s+)?(?P<name>[A-Za-z_]\w*)(?:\s*=\s*(?P<default>.+))?",
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
                    all_params = params + type_kwargs
                    args = "self, " + ", ".join(all_params)
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

        if transformed == line and line.startswith("var "):
            assignment = line[4:].strip()
            if "=" not in assignment:
                self._error(
                    "Invalid var statement; expected `var name = value`.",
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


def transpile(source_code: str, *, source_path: Path | None = None) -> str:
    """Convert teaching language source into valid Python source."""
    parser = Parser(source_code, source_path=source_path)
    return parser.parse()


def transpile_with_modules(source_path: Path) -> dict[str, str]:
    """Transpile a .pys entry file and all imported .pys modules.

    Returns a mapping of module stem -> Python source text.
    """
    source_path = source_path.resolve()
    module_cache: dict[Path, ModuleInfo] = {}
    parser = Parser(
        source_path.read_text(encoding="utf-8"),
        source_path=source_path,
        module_cache=module_cache,
    )
    modules = {source_path.stem: parser.parse()}
    for path, info in module_cache.items():
        modules[path.stem] = info.python
    return modules


def transpile_path(source_path: Path, target_path: Path) -> None:
    """Transpile a file to Python and write the output (plus imported modules)."""
    source_path = source_path.resolve()
    if source_path.suffix == ".pys":
        modules = transpile_with_modules(source_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(modules[source_path.stem], encoding="utf-8")
        for stem, python_text in modules.items():
            if stem == source_path.stem:
                continue
            (target_path.parent / f"{stem}.py").write_text(python_text, encoding="utf-8")
        return

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")


def run_source(source_path: Path) -> int:
    """Transpile a source file and execute it with the current Python interpreter."""
    source_path = source_path.resolve()
    if source_path.suffix == ".pys":
        modules = transpile_with_modules(source_path)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            for stem, python_text in modules.items():
                (temp_root / f"{stem}.py").write_text(python_text, encoding="utf-8")
            main_file = temp_root / f"{source_path.stem}.py"
            process = subprocess.run([sys.executable, str(main_file)], check=False, cwd=temp_root)
            return process.returncode

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
        temp_file.write(source_path.read_text(encoding="utf-8"))
        temp_filename = temp_file.name

    process = subprocess.run([sys.executable, temp_filename], check=False)
    return process.returncode
