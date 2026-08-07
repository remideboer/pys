from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
PKG = ROOT / "pys-language" / "package.json"
NOTES = ROOT / "pys-language" / "RELEASE_NOTES.md"


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


def test_publish_workflow_requires_release_notes_gate() -> None:
    text = (WORKFLOWS / "publish-extension.yml").read_text(encoding="utf-8")
    assert "Require RELEASE_NOTES.md for this version" in text
    assert "RELEASE_NOTES.md" in text
    assert "body_path: release-artifacts/RELEASE_BODY.md" in text
    assert "generate_release_notes: true" in text
    # Zip channel must stay releasable without Marketplace PAT
    assert "Missing GitHub Actions secret VSCE_PAT." not in text
    assert "skipping Marketplace" in text


def test_release_notes_mention_package_version() -> None:
    version = json.loads(PKG.read_text(encoding="utf-8"))["version"]
    notes = NOTES.read_text(encoding="utf-8")
    assert version in notes, (
        f"pys-language/RELEASE_NOTES.md must mention package.json version {version}"
    )
