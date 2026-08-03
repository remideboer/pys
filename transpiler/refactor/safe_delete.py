"""Safe Delete and Introduce Parameter."""
from __future__ import annotations

import re
from pathlib import Path

from ..lex import KEYWORDS
from .catalog import catalog_entry
from .plan import RefactorConflict, RefactorEdit, RefactorPlan
from .refs import build_index, resolve_at


_IDENT = re.compile(r"^[A-Za-z_]\w*$")


def plan_safe_delete(
    source_path: Path,
    *,
    line: int,
    column: int,
) -> RefactorPlan:
    meta = catalog_entry("safe-delete")
    plan = RefactorPlan(
        ok=False,
        catalog_id="safe-delete",
        title=str(meta["title"]),
        summary=str(meta["summary"]),
        why=str(meta["why"]),
    )
    path = source_path.resolve()
    index = build_index(path)
    decl = resolve_at(index, path, line, column)
    if decl is None:
        plan.conflicts.append(RefactorConflict(message="No declaration under the cursor."))
        return plan
    sites = index.sites_for(decl)
    others = [s for s in sites if s.kind != "decl"]
    if others:
        for s in others:
            plan.conflicts.append(
                RefactorConflict(
                    message=f"Still referenced ({s.kind}).",
                    file=s.file,
                    line=s.line,
                    column=s.column,
                )
            )
        plan.message = "Safe Delete blocked: remaining references listed as conflicts."
        return plan
    decl_sites = [s for s in sites if s.kind == "decl"]
    if not decl_sites:
        plan.conflicts.append(RefactorConflict(message="Declaration site not found."))
        return plan
    source = index.sources.get(decl.file, "")
    lines = source.splitlines()
    ds = decl_sites[0]
    # Delete whole line of declaration (simple)
    end_col = len(lines[ds.line - 1]) + 1 if lines else ds.end_column
    plan.edits.append(
        RefactorEdit(
            file=ds.file,
            line=ds.line,
            column=1,
            end_line=ds.line,
            end_column=end_col,
            new_text="",
            kind="replace",
            label=f"delete {decl.kind} {decl.name}",
        )
    )
    plan.ok = True
    return plan


def plan_introduce_parameter(
    source_path: Path,
    *,
    line: int,
    column: int,
    param_name: str,
    param_type: str = "int",
) -> RefactorPlan:
    """Introduce a parameter for a local variable inside a function (lite)."""
    meta = catalog_entry("introduce-parameter")
    plan = RefactorPlan(
        ok=False,
        catalog_id="introduce-parameter",
        title=str(meta["title"]),
        summary=str(meta["summary"]),
        why=str(meta["why"]),
    )
    param_name = (param_name or "").strip()
    if not _IDENT.match(param_name) or param_name in KEYWORDS:
        plan.conflicts.append(RefactorConflict(message=f"Invalid parameter name {param_name!r}."))
        return plan
    path = source_path.resolve()
    index = build_index(path)
    decl = resolve_at(index, path, line, column)
    if decl is None or decl.kind != "var":
        plan.conflicts.append(
            RefactorConflict(message="Select a local variable to promote to a parameter.")
        )
        return plan
    source = index.sources.get(decl.file, "")
    lines = source.splitlines()
    # Find enclosing function by scanning upward for `function`
    fn_line = None
    for i in range(decl.line - 1, -1, -1):
        if re.search(r"\bfunction\b", lines[i]):
            fn_line = i + 1
            break
    if fn_line is None:
        plan.conflicts.append(RefactorConflict(message="No enclosing function found."))
        return plan
    # Insert parameter into function signature: before closing )
    sig = lines[fn_line - 1]
    rparen = sig.rfind(")")
    if rparen < 0:
        plan.conflicts.append(RefactorConflict(message="Could not find function parameter list."))
        return plan
    inside = sig[sig.find("(") + 1 : rparen].strip()
    addition = f"{param_type} {param_name}"
    if inside:
        addition = ", " + addition
    new_sig = sig[:rparen] + addition + sig[rparen:]
    plan.edits.append(
        RefactorEdit(
            file=decl.file,
            line=fn_line,
            column=1,
            end_line=fn_line,
            end_column=len(sig) + 1,
            new_text=new_sig + ("\n" if False else ""),
            kind="replace",
            label="add parameter",
        )
    )
    # Fix: preserve newline — replace line content only via apply helper using columns
    plan.edits[-1] = RefactorEdit(
        file=decl.file,
        line=fn_line,
        column=1,
        end_line=fn_line,
        end_column=len(sig) + 1,
        new_text=new_sig,
        kind="replace",
        label="add parameter",
    )
    # Remove local declaration line; rename uses of local to param if names differ
    sites = index.sites_for(decl)
    for s in sites:
        if s.kind == "decl":
            plan.edits.append(
                RefactorEdit(
                    file=s.file,
                    line=s.line,
                    column=1,
                    end_line=s.line,
                    end_column=len(lines[s.line - 1]) + 1,
                    new_text="",
                    kind="replace",
                    label="remove local",
                )
            )
        elif s.kind == "use" and decl.name != param_name:
            plan.edits.append(
                RefactorEdit(
                    file=s.file,
                    line=s.line,
                    column=s.column,
                    end_line=s.line,
                    end_column=s.end_column,
                    new_text=param_name,
                    kind="replace",
                    label="use parameter",
                )
            )
    # Update call sites of the function — find function decl name from signature
    m = re.search(r"function\s+(?:\w+\s+)?(\w+)\s*\(", sig)
    if m:
        fname = m.group(1)
        # Resolve function decl by scanning index
        for dkey, sites_f in index.sites_by_decl.items():
            if dkey.name == fname and dkey.kind == "function" and dkey.file == decl.file:
                for cs in sites_f:
                    if cs.kind != "use":
                        continue
                    fl = Path(cs.file).read_text(encoding="utf-8").splitlines()
                    line_txt = fl[cs.line - 1]
                    # Insert arg before closing paren of call — naive: name()
                    idx = cs.end_column - 1
                    if idx < len(line_txt) and line_txt[idx : idx + 2] == "()":
                        plan.edits.append(
                            RefactorEdit(
                                file=cs.file,
                                line=cs.line,
                                column=cs.end_column + 1,
                                end_line=cs.line,
                                end_column=cs.end_column + 1,
                                new_text=param_name if decl.name == param_name else "/* TODO arg */",
                                kind="insert",
                                label="pass argument",
                                optional=True,
                            )
                        )
                break
    plan.ok = True
    return plan
