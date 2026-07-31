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


def _transform_class_body(class_lines: List[str]) -> List[str]:
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
                header_match = re.match(
                    r"^    def\s+[A-Za-z_]\w*\s*\(self(?:,\s*(?P<params>.*))?\)\s*:",
                    overload[0],
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
        helper_def = method_lines[0].replace(
            f"def {method_name}", f"def _{method_name}_{overload_index}", 1
        )
        helper_lines = [helper_def] + method_lines[1:]
        transformed.extend(helper_lines)

    return transformed
