"""Workspace path containment shared by IDE and import analysis."""
from __future__ import annotations

import os
from pathlib import Path

WORKSPACE_ROOT_ENV = "PYS_WORKSPACE_ROOT"


def workspace_root_from_env() -> Path | None:
    value = os.environ.get(WORKSPACE_ROOT_ENV)
    if not value:
        return None
    try:
        return Path(value).expanduser().resolve(strict=True)
    except OSError:
        return None


def resolve_workspace_path(candidate: Path, workspace_root: Path) -> Path | None:
    """Resolve an existing path only when lexical and real paths stay in root."""
    try:
        lexical_root = Path(os.path.abspath(workspace_root))
        lexical_candidate = Path(os.path.abspath(candidate))
        lexical_candidate.relative_to(lexical_root)

        real_root = workspace_root.resolve(strict=True)
        real_candidate = candidate.resolve(strict=True)
        real_candidate.relative_to(real_root)
        return real_candidate
    except (OSError, ValueError):
        return None
