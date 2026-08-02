"""Post-pass: rewrite overloaded Python methods into arity dispatchers."""
from __future__ import annotations

import re
from typing import List


def rewrite_overloaded_methods(python_text: str) -> str:
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

            rewritten.extend(_transform_class_body(class_lines))
            continue

        rewritten.append(line)
        index += 1
    return "\n".join(rewritten) + "\n"


_METHOD_DEF_RE = re.compile(r"^    def\s+([A-Za-z_]\w*)\s*\((.*?)\)\s*:\s*$")
_DECORATOR_RE = re.compile(r"^    @[A-Za-z_][\w.]*\s*$")


def _method_def_line(line: str) -> re.Match[str] | None:
    if not line.strip():
        return None
    return _METHOD_DEF_RE.match(line)


def _def_line_of(method_lines: List[str]) -> str | None:
    for ln in method_lines:
        if _method_def_line(ln):
            return ln
    return None


def _split_trailing_decorators(segment: List[str]) -> tuple[List[str], List[str]]:
    """Pull trailing blank/`@decorator` lines off a text segment for the next method."""
    i = len(segment)
    while i > 0 and not segment[i - 1].strip():
        i -= 1
    deco_start = i
    while deco_start > 0 and _DECORATOR_RE.match(segment[deco_start - 1]):
        deco_start -= 1
    if deco_start == i:
        return segment, []
    # Include blanks between decorators and the following def.
    return segment[:deco_start], segment[deco_start:]


def _collect_method_body(class_lines: List[str], index: int) -> tuple[List[str], int]:
    method_lines = [class_lines[index]]
    index += 1
    while index < len(class_lines):
        next_line = class_lines[index]
        if next_line.strip() and len(next_line) - len(next_line.lstrip(" ")) <= 4:
            break
        method_lines.append(next_line)
        index += 1
    return method_lines, index


def _transform_class_body(class_lines: List[str]) -> List[str]:
    segments: List[tuple[str, List[str]]] = []
    index = 0
    while index < len(class_lines):
        line = class_lines[index]
        if _method_def_line(line):
            method_lines, index = _collect_method_body(class_lines, index)
            segments.append(("method", method_lines))
            continue
        segment: List[str] = []
        while index < len(class_lines):
            current = class_lines[index]
            if _method_def_line(current):
                break
            segment.append(current)
            index += 1
        if index < len(class_lines) and _method_def_line(class_lines[index]):
            segment, decorators = _split_trailing_decorators(segment)
            if segment:
                segments.append(("text", segment))
            method_lines, index = _collect_method_body(class_lines, index)
            segments.append(("method", list(decorators) + method_lines))
            continue
        if segment:
            segments.append(("text", segment))

    method_groups: dict[str, List[List[str]]] = {}
    transformed: List[str] = []
    for kind, payload in segments:
        if kind == "text":
            transformed.extend(payload)
            continue
        def_line = _def_line_of(payload)
        if def_line is None:
            transformed.extend(payload)
            continue
        method_name_match = _METHOD_DEF_RE.match(def_line)
        assert method_name_match is not None
        method_groups.setdefault(method_name_match.group(1), []).append(payload)

    for kind, payload in segments:
        if kind == "text":
            continue
        def_line = _def_line_of(payload)
        if def_line is None:
            transformed.extend(payload)
            continue
        method_name_match = _METHOD_DEF_RE.match(def_line)
        assert method_name_match is not None
        method_name = method_name_match.group(1)
        overloads = method_groups[method_name]
        if len(overloads) == 1:
            transformed.extend(payload)
            continue
        overload_index = overloads.index(payload)
        prefix: List[str] = []
        body_start = 0
        for i, ln in enumerate(payload):
            if _method_def_line(ln):
                body_start = i
                break
            prefix.append(ln)
        def_header = payload[body_start]
        if overload_index == 0:
            has_type_kwargs = any(
                re.search(r"__\w+__=object", dl)
                for ol in overloads
                for dl in [_def_line_of(ol)]
                if dl is not None
            )
            if has_type_kwargs:
                dispatcher = f"    def {method_name}(self, *args, **kwargs):\n"
            else:
                dispatcher = f"    def {method_name}(self, *args):\n"
            for idx, overload in enumerate(overloads):
                ol_def = _def_line_of(overload)
                assert ol_def is not None
                header_match = re.match(
                    r"^    def\s+[A-Za-z_]\w*\s*\(self(?:,\s*(?P<params>.*))?\)\s*:",
                    ol_def,
                )
                param_count = 0
                if header_match and header_match.group("params"):
                    positional = [
                        p for p in header_match.group("params").split(",")
                        if p.strip() and "__" not in p
                    ]
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
            dispatcher += (
                f'        raise TypeError(f"{{method_name}}() got an unexpected number of arguments")\n'
            )
            transformed.append(dispatcher.rstrip("\n"))
        helper_def = def_header.replace(
            f"def {method_name}", f"def _{method_name}_{overload_index}", 1
        )
        helper_lines = prefix + [helper_def] + payload[body_start + 1 :]
        transformed.extend(helper_lines)

    return transformed
