from __future__ import annotations

import re
from pathlib import Path


WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def test_workflow_actions_use_immutable_commit_shas() -> None:
    action_ref = re.compile(r"^\s*uses:\s+([^@\s]+)@([^\s#]+)", re.MULTILINE)
    for workflow in WORKFLOWS.glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        for action, ref in action_ref.findall(text):
            assert re.fullmatch(r"[0-9a-f]{40}", ref), (
                f"{workflow.name}: {action}@{ref} is not pinned to a commit SHA"
            )


def test_publish_workflow_never_downloads_npx_tools() -> None:
    text = (WORKFLOWS / "publish-extension.yml").read_text(encoding="utf-8")
    assert "npx --yes" not in text
