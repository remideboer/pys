"""Convert book/*.md to book/html/*.html with shared styling and rewritten links."""

from __future__ import annotations

import html as html_lib
import re
import shutil
from pathlib import Path
from typing import Any

from pys_highlight import highlight_html_document

ROOT = Path(__file__).resolve().parent
SRC = ROOT
OUT = ROOT / "html"
REPOSITORY_URL = "https://github.com/remideboer/pys"

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
main blockquote strong:first-child {
  color: var(--fg);
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
  line-height: 1.45;
}
main pre code { background: transparent; padding: 0; color: inherit; }

/* PYS syntax highlighting (token spans from pys_highlight.py) */
.tok-kw { color: #c792ea; font-weight: 600; }
.tok-mod { color: #82aaff; font-weight: 600; }
.tok-type { color: #ffcb6b; }
.tok-typename { color: #ffcb6b; }
.tok-builtin { color: #82aaff; }
.tok-const { color: #f78c6c; }
.tok-number { color: #f78c6c; }
.tok-string { color: #c3e88d; }
.tok-interp { color: #89ddff; }
.tok-comment { color: #697098; font-style: italic; }
.tok-op { color: #89ddff; }
.tok-ident { color: #eeffff; }

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
.concept-diagram {
  margin: 1.25rem 0;
  padding: 1rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #f1eee7;
  overflow-x: auto;
}
.concept-diagram figcaption {
  margin-top: 0.75rem;
  color: var(--muted);
  font-size: 0.9rem;
  text-align: center;
}
.diagram-flow {
  display: flex;
  align-items: stretch;
  justify-content: center;
  gap: 0.55rem;
  min-width: 36rem;
}
.diagram-box {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  justify-content: center;
  min-width: 8rem;
  padding: 0.7rem;
  border: 1px solid #aaa397;
  border-radius: 6px;
  background: var(--bg);
  text-align: center;
}
.diagram-box span { color: var(--muted); font-size: 0.88rem; }
.diagram-arrow {
  align-self: center;
  color: var(--accent);
  font-size: 1.4rem;
  font-weight: 700;
}
.diagram-stack {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  max-width: 32rem;
  margin: 0 auto;
}
.diagram-stack .diagram-box { flex: none; }
.diagram-threads {
  display: grid;
  grid-template-columns: 1fr minmax(10rem, 1.3fr) 1fr;
  gap: 0.65rem;
  align-items: center;
  min-width: 34rem;
}
.diagram-shared {
  border: 2px solid var(--accent);
  background: #e5edff;
}
/* Session 10 pattern diagrams — layered architecture / boundaries / states */
.diagram-layers {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  max-width: 34rem;
  margin: 0 auto;
}
.diagram-layer {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding: 0.7rem 0.85rem;
  border: 1px solid #aaa397;
  border-radius: 6px;
  background: var(--bg);
  text-align: center;
}
.diagram-layer strong { display: block; }
.diagram-layer span { color: var(--muted); font-size: 0.88rem; }
.diagram-layer-core {
  border: 2px solid var(--accent);
  background: #e5edff;
}
.diagram-layer-edge {
  border-style: dashed;
  border-color: #8a6d3b;
  background: #f5ecd8;
}
.diagram-outside {
  border-style: solid;
  border-color: #aaa397;
  background: #efebe3;
  color: var(--muted);
}
.diagram-boundary {
  margin: 0.35rem auto;
  padding: 0.55rem 0.75rem;
  border: 2px dashed #8a6d3b;
  border-radius: 6px;
  background: #f5ecd8;
  text-align: center;
  max-width: 28rem;
}
.diagram-boundary strong { display: block; }
.diagram-boundary span { color: var(--muted); font-size: 0.88rem; }
.diagram-states {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
}
.diagram-state {
  min-width: 5.5rem;
  padding: 0.45rem 0.65rem;
  border: 1px solid #aaa397;
  border-radius: 999px;
  background: var(--bg);
  text-align: center;
  font-size: 0.9rem;
  font-weight: 650;
}
.diagram-state.is-active {
  border: 2px solid var(--accent);
  background: #e5edff;
  color: var(--accent);
}
.diagram-state span {
  display: block;
  margin-top: 0.15rem;
  font-weight: 400;
  color: var(--muted);
  font-size: 0.78rem;
}
.diagram-grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(10rem, 1fr));
  gap: 0.65rem;
  max-width: 36rem;
  margin: 0 auto;
}
.diagram-grid-5 {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(7.5rem, 1fr));
  gap: 0.45rem;
  max-width: 40rem;
  margin: 0 auto;
}
.diagram-slot-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.4rem;
}
.diagram-slot {
  min-width: 3.2rem;
  min-height: 2.4rem;
  padding: 0.35rem 0.5rem;
  border: 1px solid #aaa397;
  border-radius: 4px;
  background: var(--bg);
  text-align: center;
  font-size: 0.85rem;
}
.diagram-slot.is-full {
  border: 2px solid var(--accent);
  background: #e5edff;
}
.diagram-slot.is-blocked {
  border-style: dashed;
  color: var(--muted);
  background: #efebe3;
}
.diagram-prompt-pair {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 0.75rem;
  max-width: 40rem;
  margin: 0 auto;
}
.diagram-prompt {
  padding: 0.75rem 0.85rem;
  border: 1px solid #aaa397;
  border-radius: 6px;
  background: var(--bg);
}
.diagram-prompt.is-weak {
  border-color: #8a6d3b;
  background: #f5ecd8;
}
.diagram-prompt.is-strong {
  border: 2px solid var(--accent);
  background: #e5edff;
}
.diagram-prompt .diagram-prompt-label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--muted);
}
.diagram-box.diagram-layer-core,
.diagram-box.is-core {
  border: 2px solid var(--accent);
  background: #e5edff;
}
.diagram-box.diagram-layer-edge,
.diagram-box.is-edge {
  border-style: dashed;
  border-width: 2px;
  border-color: #8a6d3b;
  background: #f5ecd8;
}
.diagram-box.is-warn {
  border: 2px solid #8a6d3b;
  background: #f5ecd8;
}
.memory-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 0.35rem 0.5rem;
  margin: 0 auto 0.85rem;
  font-size: 0.95rem;
}
.memory-name-tag {
  font-family: Consolas, "Cascadia Mono", monospace;
  font-weight: 650;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  background: #e5edff;
  border: 1px solid var(--accent);
  color: var(--accent);
}
.memory-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(4.5rem, 1fr));
  gap: 0.4rem;
  max-width: 28rem;
  margin: 0 auto;
}
.memory-cell {
  position: relative;
  min-height: 4.25rem;
  padding: 0.35rem 0.4rem;
  border: 1px solid #aaa397;
  border-radius: 6px;
  background: var(--bg);
  font-family: Consolas, "Cascadia Mono", monospace;
  font-size: 0.85rem;
}
.memory-cell .memory-meta {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.25rem;
  min-height: 1em;
}
.memory-cell.locked .memory-meta {
  padding-right: 1.15rem;
}
.memory-cell .addr {
  color: var(--muted);
  font-size: 0.78rem;
  text-align: left;
}
.memory-cell .type {
  color: var(--muted);
  font-size: 0.72rem;
  text-align: right;
}
.memory-cell.named {
  border: 2px solid var(--accent);
  background: #e5edff;
}
.memory-cell .varname {
  display: block;
  margin-top: 0.2rem;
  font-weight: 650;
  color: var(--accent);
  font-size: 0.72rem;
  word-break: break-word;
}
.memory-cell .val {
  display: block;
  margin-top: 0.15rem;
  color: var(--fg);
}
.memory-cell.locked {
  border-color: #8a6d3b;
  background: #f5ecd8;
}
.memory-cell .lock {
  position: absolute;
  top: 0.25rem;
  right: 0.3rem;
  font-size: 1rem;
  line-height: 1;
}
.memory-cell.changed {
  box-shadow: inset 0 0 0 2px #c47b00;
}
.memory-compare {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  justify-content: center;
  gap: 0.75rem 1rem;
}
.memory-compare > .concept-diagram {
  flex: 1 1 16rem;
  margin: 0;
  max-width: 20rem;
}
.memory-compare-arrow {
  align-self: center;
  color: var(--accent);
  font-size: 1.6rem;
  font-weight: 700;
}
.fn-flow {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  justify-content: center;
  gap: 0.55rem 0.65rem;
}
.fn-port {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.2rem;
  min-width: 6.5rem;
  max-width: 9rem;
  padding: 0.65rem 0.7rem;
  border: 1px dashed #aaa397;
  border-radius: 6px;
  background: var(--bg);
  text-align: center;
  font-size: 0.9rem;
}
.fn-port-label {
  color: var(--muted);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.fn-port .fn-type {
  font-family: Consolas, "Cascadia Mono", monospace;
  font-size: 0.78rem;
  color: var(--muted);
}
.fn-arrow {
  align-self: center;
  color: var(--accent);
  font-size: 1.45rem;
  font-weight: 700;
}
.fn-box {
  flex: 1 1 14rem;
  max-width: 22rem;
  border: 2px solid var(--accent);
  border-radius: 8px;
  background: #e5edff;
  padding: 0.65rem 0.75rem 0.75rem;
}
.fn-box-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
  margin-bottom: 0.45rem;
}
.fn-gear {
  font-size: 1.35rem;
  line-height: 1;
}
.fn-box-head code {
  font-weight: 650;
  background: transparent;
  padding: 0;
}
.fn-repeat {
  margin-left: auto;
  font-size: 0.75rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.fn-body {
  margin: 0;
  padding: 0.55rem 0.65rem;
  border-radius: 4px;
  background: var(--code-bg);
  color: var(--fg);
  font-family: Consolas, "Cascadia Mono", monospace;
  font-size: 0.82rem;
  white-space: pre-wrap;
  overflow-x: auto;
}
.fn-box-foot {
  display: block;
  margin-top: 0.45rem;
  font-size: 0.85rem;
  color: var(--muted);
}
.fn-port.fn-out {
  border-style: solid;
  border-color: var(--accent);
  background: #e5edff;
}
.fn-port.fn-side {
  border-color: #8a6d3b;
  background: #f5ecd8;
}
.cls-machine {
  border: 3px solid #2a3f6e;
  border-radius: 10px;
  background: linear-gradient(180deg, #e8eefc 0%, #d9e4f8 100%);
  padding: 0.75rem 0.85rem 0.85rem;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.55);
}
.cls-machine.is-abstract {
  border-style: dashed;
  border-color: #5a6f9e;
  background:
    linear-gradient(180deg, rgba(232, 238, 252, 0.92) 0%, rgba(217, 228, 248, 0.92) 100%),
    repeating-linear-gradient(
      -45deg,
      transparent,
      transparent 6px,
      rgba(90, 111, 158, 0.07) 6px,
      rgba(90, 111, 158, 0.07) 12px
    );
}
.cls-machine-sm {
  flex: 1 1 14rem;
  max-width: 20rem;
}
.cls-slot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.3rem 0.4rem;
  margin: 0.28rem 0;
  padding: 0.4rem 0.45rem;
  border: 1.5px dashed #6a6a6a;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.65);
  font-size: 0.88rem;
}
.cls-slot code {
  background: transparent;
  padding: 0;
}
.cls-member.cls-slot-filled {
  box-shadow: inset 3px 0 0 #2a7a3a;
}
.cls-machine.cls-specialized {
  border-color: #2a7a3a;
  background: linear-gradient(180deg, #e8f6ec 0%, #d7eedd 100%);
}
.trait-module {
  border: 2px solid #6b4f2a;
  border-radius: 10px;
  border-style: solid;
  background:
    linear-gradient(180deg, #f7f0e4 0%, #efe4d2 100%),
    repeating-linear-gradient(
      90deg,
      transparent,
      transparent 10px,
      rgba(107, 79, 42, 0.06) 10px,
      rgba(107, 79, 42, 0.06) 20px
    );
  padding: 0.75rem 0.85rem 0.85rem;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.45);
}
.trait-icon {
  font-size: 1.35rem;
  line-height: 1;
}
.trait-wire {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.3rem 0.4rem;
  margin: 0.28rem 0;
  padding: 0.4rem 0.45rem;
  border: 1.5px dashed #8a6d3b;
  border-radius: 6px;
  background: #fff8ee;
  font-size: 0.88rem;
}
.trait-wire code {
  background: transparent;
  padding: 0;
}
.trait-wire-jack {
  width: 0.9rem;
  height: 0.9rem;
  border: 2px solid #6b4f2a;
  border-radius: 3px;
  background:
    linear-gradient(#6b4f2a, #6b4f2a) center / 2px 60% no-repeat,
    #f7f0e4;
  flex: 0 0 auto;
  box-shadow: inset 0 0 0 2px #fff;
}
.trait-remap {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 0.55rem 0.75rem;
}
.trait-remap .cls-member {
  margin: 0;
}
.trait-collide-wires {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
  gap: 0.75rem 0.85rem;
}
.trait-collide-wire {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
  color: var(--accent);
  font-size: 0.85rem;
}
.trait-collide-wire .cls-line-arrow {
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1;
}
.trait-collide-wire .iface-plug-label {
  color: #6b4f2a;
  text-align: center;
}
.cls-head,
.iface-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
  margin-bottom: 0.65rem;
}
.cls-icon {
  font-size: 1.45rem;
  letter-spacing: -0.15em;
  line-height: 1;
}
.cls-head code,
.iface-head code {
  font-weight: 650;
  background: transparent;
  padding: 0;
  font-size: 1.05em;
}
.cls-tag {
  margin-left: auto;
  font-size: 0.72rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.cls-columns {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: 0.65rem;
}
.cls-section {
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid #b7c4e0;
  border-radius: 6px;
  padding: 0.5rem 0.55rem 0.55rem;
}
.cls-section-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--muted);
  margin-bottom: 0.4rem;
}
.cls-member {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.25rem 0.4rem;
  margin: 0.28rem 0;
  padding: 0.35rem 0.4rem;
  border-radius: 4px;
  font-size: 0.88rem;
  background: var(--bg);
  border: 1px solid transparent;
}
.cls-member code {
  background: transparent;
  padding: 0;
}
.cls-member.is-public {
  border-color: var(--accent);
  background: #e5edff;
}
.cls-member.is-private {
  border-color: #8a6d3b;
  background: #f5ecd8;
  opacity: 0.95;
}
.cls-channel,
.cls-lock {
  font-size: 0.95rem;
  line-height: 1;
}
.cls-note {
  font-size: 0.75rem;
  color: var(--muted);
}
.cls-channels {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.45rem;
  margin-top: 0.7rem;
  padding-top: 0.55rem;
  border-top: 1px dashed #8fa0c4;
}
.cls-channels-label {
  width: 100%;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--muted);
}
.cls-channels code {
  font-size: 0.82rem;
  border: 1px solid var(--accent);
  background: #fff;
}
.iface-pair {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  justify-content: center;
  gap: 0.75rem 0.85rem;
}
.iface-socket {
  flex: 1 1 12rem;
  max-width: 18rem;
  border: 2px dashed #6a6a6a;
  border-radius: 10px;
  background:
    repeating-linear-gradient(
      -45deg,
      #f3f1eb,
      #f3f1eb 8px,
      #ebe7de 8px,
      #ebe7de 16px
    );
  padding: 0.75rem 0.85rem 0.85rem;
}
.iface-icon {
  font-size: 1.25rem;
  line-height: 1;
  color: #444;
}
.iface-slot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.45rem;
  margin: 0.35rem 0;
  padding: 0.45rem 0.5rem;
  border: 1px solid #8a8a8a;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.75);
  font-size: 0.9rem;
}
.iface-slot code {
  background: transparent;
  padding: 0;
}
.iface-hole {
  width: 0.85rem;
  height: 0.85rem;
  border: 2px solid #555;
  border-radius: 50%;
  background: var(--bg);
  box-shadow: inset 0 0 0 2px #fff;
  flex: 0 0 auto;
}
.iface-empty {
  margin: 0.55rem 0 0;
  font-size: 0.85rem;
  color: var(--muted);
  font-style: italic;
}
.iface-plug {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.15rem;
  min-width: 4.5rem;
  color: var(--accent);
}
.iface-plug-arrow {
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1;
}
.iface-plug-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.iface-choice {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.65rem;
}
.iface-caller {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 0.35rem 0.55rem;
  padding: 0.55rem 0.7rem;
  border: 1px solid #8a6d3b;
  border-radius: 8px;
  background: #f5ecd8;
  text-align: center;
}
.iface-caller-label {
  width: 100%;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--muted);
}
.iface-caller code {
  font-weight: 650;
  background: #fff;
  border: 1px solid #8a6d3b;
}
.iface-cable {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  margin-top: 0.15rem;
}
.iface-cable-line {
  width: 3px;
  height: 1.1rem;
  background: linear-gradient(#8a6d3b, var(--accent));
  border-radius: 2px;
}
.iface-cable-tip {
  font-family: Consolas, "Cascadia Mono", monospace;
  font-size: 0.82rem;
  color: var(--accent);
  font-weight: 650;
}
.iface-socket-wide {
  max-width: none;
  width: 100%;
}
.iface-impls {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
  gap: 0.75rem 0.85rem;
  align-items: stretch;
}
.iface-plug-down {
  min-width: 0;
}
.iface-impls .cls-machine-sm {
  max-width: none;
  width: 100%;
}
.cls-factory {
  border: 2px solid #4a5568;
  border-radius: 12px;
  background:
    repeating-linear-gradient(
      90deg,
      #ece8e0,
      #ece8e0 12px,
      #e4dfd5 12px,
      #e4dfd5 24px
    );
  padding: 0.75rem 0.85rem 0.9rem;
}
.cls-factory-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
  margin-bottom: 0.65rem;
  font-size: 0.9rem;
  color: #333;
  font-weight: 650;
}
.cls-factory-icon {
  font-size: 1.35rem;
  line-height: 1;
}
.cls-factory > .cls-machine {
  background: linear-gradient(180deg, #e8eefc 0%, #d9e4f8 100%);
}
.cls-station {
  background: rgba(255, 255, 255, 0.35);
}
.cls-machine-nested {
  border-width: 2px;
  border-style: solid;
  border-color: #3d5a9a;
  background: linear-gradient(180deg, #f4f7ff 0%, #e5edff 100%);
  padding: 0.55rem 0.6rem 0.65rem;
  box-shadow: none;
}
.cls-machine-nested .cls-head {
  margin-bottom: 0.35rem;
}
.cls-station-note {
  margin: 0.2rem 0 0.45rem;
  font-size: 0.82rem;
  color: var(--muted);
  line-height: 1.4;
}
.cls-line {
  margin-top: 0.7rem;
  padding: 0.55rem 0.6rem;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px dashed #8fa0c4;
}
.cls-line-label {
  display: block;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--muted);
  margin-bottom: 0.35rem;
}
.cls-line-steps {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.45rem;
  font-size: 0.9rem;
}
.cls-line-arrow {
  color: var(--accent);
  font-weight: 700;
  font-size: 1.15rem;
}
.cls-line-steps code {
  background: #fff;
  border: 1px solid var(--accent);
}
main hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }
.nav-footer { margin-top: 2.5rem; color: var(--muted); font-size: 0.95rem; }
.mermaid {
  margin: 1.25rem 0;
  padding: 0.85rem 1rem;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow-x: auto;
}
@media (max-width: 800px) {
  .layout { grid-template-columns: 1fr; }
  nav.toc { position: static; height: auto; border-right: none; border-bottom: 1px solid var(--border); }
}
"""


_MD: Any | None = None


def _markdown_converter() -> Any:
    """Lazy: link-rewrite helpers must load without the ``markdown`` package (CI)."""
    global _MD
    if _MD is None:
        import markdown

        _MD = markdown.Markdown(
            extensions=[
                "fenced_code",
                "tables",
                "sane_lists",
                "smarty",
                "attr_list",
            ]
        )
    return _MD


def md_href_to_html(match: re.Match[str]) -> str:
    href = match.group(1)
    if href.startswith(("http://", "https://", "mailto:", "#")):
        return match.group(0)
    if href.startswith("../"):
        path, frag = (href[3:].split("#", 1) + [""])[:2]
        is_directory = path.endswith("/")
        kind = "tree" if is_directory else "blob"
        path = path.rstrip("/")
        out = f"{REPOSITORY_URL}/{kind}/main/{path}"
        if frag:
            out += "#" + frag
        return f'href="{out}"'
    path, frag = (href.split("#", 1) + [""])[:2]
    if path == "SUMMARY.md":
        path = "index.html"
    elif path.endswith(".md"):
        path = path[:-3] + ".html"
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


def promote_mermaid_blocks(body: str) -> tuple[str, bool]:
    """Turn fenced mermaid code blocks into ``div.mermaid`` for the CDN renderer."""
    found = False

    def repl(match: re.Match[str]) -> str:
        nonlocal found
        found = True
        source = html_lib.unescape(match.group(1)).strip("\n")
        return f'<div class="mermaid">\n{source}\n</div>'

    out = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        repl,
        body,
        flags=re.DOTALL,
    )
    return out, found


def page(title: str, nav: str, content: str, *, mermaid: bool = False) -> str:
    mermaid_boot = ""
    if mermaid:
        mermaid_boot = """
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "strict" });
    await mermaid.run({ querySelector: ".mermaid" });
  </script>
"""
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
{mermaid_boot}</body>
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
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    summary_text = (SRC / "SUMMARY.md").read_text(encoding="utf-8")
    nav = parse_summary_nav(summary_text)

    md_files = sorted(
        p for p in SRC.glob("*.md") if not p.name.startswith("_")
    )
    for md_path in md_files:
        text = md_path.read_text(encoding="utf-8")
        MD = _markdown_converter()
        MD.reset()
        body = rewrite_links(MD.convert(text))
        body, has_mermaid = promote_mermaid_blocks(body)
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

        html = page(title, nav, body, mermaid=has_mermaid)
        html = highlight_html_document(html)
        (OUT / out_name).write_text(html, encoding="utf-8", newline="\n")
        print(f"wrote {out_name}")

    print(f"done -> {OUT}")


if __name__ == "__main__":
    convert()
