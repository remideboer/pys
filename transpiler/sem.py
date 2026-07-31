"""Semantic checks on AST (types, scopes, await DAG).

During migration, deep checks remain in the legacy Python emitter path.
This module is the seam for moving them off string rewriting.
"""
from __future__ import annotations

from .ast_nodes import Module


def analyze(module: Module) -> Module:
    """Validate / annotate module. Currently a pass-through seam."""
    return module
