"""Convert book/*.md to book/html/*.html with shared styling and rewritten links."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent
SRC = ROOT
OUT = ROOT / "html"

CSS = """\
:root {
  --bg: #f7f5f0;
  --fg: #1a1a1a;
  --muted: #555;
  --accent: #0b5fff;
  --code-bg: #ece8e1;
  --border: #d4cfc4;
  --pre-bg: #1e1e1e;
  --pre-fg: #e8e8e8;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Segoe UI", "Iowan Old Style", Georgia, serif;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.55;
}
.layout {
  display: grid;
  grid-template-columns: minmax(12rem, 16rem) 1fr;
  min-height: 100vh;
}
nav.toc {
  background: #efebe3;
  border-right: 1px solid var(--border);
  padding: 1.25rem 1rem 2rem;
  font-size: 0.9rem;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: auto;
}
nav.toc h1 {
  font-size: 1rem;
  margin: 0 0 0.75rem;
}
nav.toc ul { list-style: none; padding-left: 0.75rem; margin: 0.25rem 0; }
nav.toc > ul { padding-left: 0; }
nav.toc a { color: var(--fg); text-decoration: none; }
nav.toc a:hover { color: var(--accent); text-decoration: underline; }
nav.toc .section {
  display: block;
  font-weight: 650;
  margin: 0.85rem 0 0.25rem;
  color: var(--muted);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
main {
  max-width: 46rem;
  padding: 2rem 2.5rem 4rem;
}
main h1 { font-size: 1.85rem; line-height: 1.25; }
main h2 { margin-top: 1.75rem; font-size: 1.35rem; }
main h3 { margin-top: 1.35rem; font-size: 1.15rem; }
main a { color: var(--accent); }
main blockquote {
  margin: 1rem 0;
  padding: 0.15rem 0 0.15rem 1rem;
  border-left: 3px solid var(--border);
  color: var(--muted);
}
main code {
  font-family: Consolas, "Cascadia Mono", monospace;
  font-size: 0.9em;
  background: var(--code-bg);
  padding: 0.1em 0.35em;
  border-radius: 3px;
}
main pre {
  background: var(--pre-bg);
  color: var(--pre-fg);
  padding: 0.9rem 1rem;
  overflow-x: auto;
  border-radius: 6px;
  font-size: 0.88rem;
}
main pre code { background: transparent; padding: 0; color: inherit; }
main table {
  border-collapse: collapse;
  width: 100%;
  margin: 1rem 0;
  font-size: 0.95rem;
}
main th, main td {
  border: 1px solid var(--border);
  padding: 0.4rem 0.55rem;
  text-align: left;
  vertical-align: top;
}
main th { background: #efebe3; }
main hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }
.nav-footer { margin-top: 2.5rem; color: var(--muted); font-size: 0.95rem; }
@media (max-width: 800px) {
  .layout { grid-template-columns: 1fr; }
  nav.toc { position: static; height: auto; border-right: none; border-bottom: 1px solid var(--border); }
}
"""

MD = markdown.Markdown(
    extensions=[
        "fenced_code",
        "tables",
        "sane_lists",
        "smarty",
        "attr_list",
    ]
)


def md_href_to_html(match: re.Match[str]) -> str:
    href = match.group(1)
    if href.startswith(("http://", "https://", "mailto:", "#")):
        return match.group(0)
    if href.startswith("../"):
        # Keep repo-relative links as-is (may 404 when browsing file://)
        return match.group(0)
    path, frag = (href.split("#", 1) + [""])[:2]
    if path.endswith(".md"):
        path = path[:-3] + ".html"
    elif path == "SUMMARY.md":
        path = "index.html"
    out = path
    if frag:
        out += "#" + frag
    return f'href="{out}"'


def rewrite_links(html: str) -> str:
    return re.sub(r'href="([^"]+)"', md_href_to_html, html)


def parse_summary_nav(summary_md: str) -> str:
    """Turn SUMMARY.md into a compact HTML nav (links already .html)."""
    lines: list[str] = []
    for raw in summary_md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.strip() == "# Summary":
            continue
        # Bare link (Preface)
        m_bare = re.match(r"^\[([^\]]+)\]\(([^)]+)\)\s*$", line)
        if m_bare:
            label, href = m_bare.groups()
            if href.endswith(".md"):
                href = href[:-3] + ".html"
            lines.append(f'<li><a href="{href}">{_esc(label)}</a></li>')
            continue
        if re.match(r"^#+\s+", line):
            title = re.sub(r"^#+\s+", "", line).strip()
            lines.append(f'<span class="section">{_esc(title)}</span>')
            continue
        m = re.match(r"^(\s*)-\s+\[([^\]]+)\]\(([^)]+)\)\s*$", line)
        if not m:
            continue
        indent, label, href = m.groups()
        depth = len(indent.replace("\t", "    ")) // 2
        if href.endswith(".md"):
            href = href[:-3] + ".html"
        pad = "  " * depth
        lines.append(f'{pad}<li><a href="{href}">{_esc(label)}</a></li>')

    body: list[str] = ["<ul>"]
    for item in lines:
        if item.startswith("<span"):
            body.append("</ul>")
            body.append(item)
            body.append("<ul>")
        else:
            body.append(item.lstrip())
    body.append("</ul>")
    return "\n".join(body)


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def page(title: str, nav: str, content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_esc(title)} — PYS Development Classes</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="layout">
    <nav class="toc">
      <h1><a href="index.html">PYS Development Classes</a></h1>
      {nav}
    </nav>
    <main>
{content}
    </main>
  </div>
</body>
</html>
"""


def title_from_md(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def convert() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    (OUT / "style.css").write_text(CSS, encoding="utf-8")

    summary_text = (SRC / "SUMMARY.md").read_text(encoding="utf-8")
    nav = parse_summary_nav(summary_text)

    md_files = sorted(SRC.glob("*.md"))
    for md_path in md_files:
        text = md_path.read_text(encoding="utf-8")
        MD.reset()
        body = rewrite_links(MD.convert(text))
        title = title_from_md(text, md_path.stem)

        if md_path.name == "SUMMARY.md":
            out_name = "index.html"
            # Prefer a landing that shows the TOC as content too
            body = (
                "<h1>PYS Development Classes</h1>"
                "<p>Beginner book for the PYS teaching language. "
                "Use the sidebar or the outline below.</p>"
                + body
            )
            title = "Contents"
        else:
            out_name = md_path.stem + ".html"

        html = page(title, nav, body)
        (OUT / out_name).write_text(html, encoding="utf-8", newline="\n")
        print(f"wrote {out_name}")

    print(f"done -> {OUT}")


if __name__ == "__main__":
    convert()
