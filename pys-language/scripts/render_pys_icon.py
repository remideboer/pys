"""Render marketplace extension icon: braces + two eyes (“P eyes”).

Uses the light file-icon palette (teal #0F766E / mint #ECFDF5) and the same
brace path as ``icons/pys-light.svg``, scaled into a 128×128 squircle.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "icons" / "pys-icon.png"
SIZE = 128

# Light scheme (pys-light.svg)
BG = (15, 118, 110, 255)  # #0F766E
FG = (236, 253, 245, 255)  # #ECFDF5 braces + eye ring / highlight
SCLERA = (255, 255, 255, 255)  # white sclera (reads on teal)
PUPIL = (6, 78, 72, 255)  # #064E48 — darker than bg so pupils aren’t cutouts
HIGHLIGHT = (236, 253, 245, 255)

# Left brace only (viewBox 0 0 16 16); right brace is a horizontal mirror.
_BRACE_LEFT = (
    "M4.75 2.25c-1.2 0-2.1.75-2.1 1.9v1.85c0 .55-.2.9-.75 1.05v.4c.55.15.75.5"
    ".75 1.05v1.85c0 1.15.9 1.9 2.1 1.9h.55V11.1h-.4c-.5 0-.85-.3-.85-.8V8.55c0"
    "-.95-.4-1.45-1.1-1.65.7-.2 1.1-.7 1.1-1.65V4.15c0-.5.35-.8.85-.8h.4V2.25h-"
    ".55z"
)

_TOKEN = re.compile(
    r"([MmZzLlHhVvCc])|([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
)


def _parse_path(d: str) -> list[list[tuple[float, float]]]:
    """Flatten SVG path (M/L/H/V/C/Z, relative+absolute) to polygon rings."""
    tokens: list[str] = [m.group(0) for m in _TOKEN.finditer(d) if m.group(0)]
    i = 0
    cx = cy = 0.0
    start = (0.0, 0.0)
    rings: list[list[tuple[float, float]]] = []
    ring: list[tuple[float, float]] = []

    def take(n: int) -> list[float]:
        nonlocal i
        out: list[float] = []
        for _ in range(n):
            out.append(float(tokens[i]))
            i += 1
        return out

    def add(x: float, y: float) -> None:
        nonlocal cx, cy
        cx, cy = x, y
        ring.append((x, y))

    def cubic(
        x1: float, y1: float, x2: float, y2: float, x: float, y: float, steps: int = 14
    ) -> None:
        x0, y0 = cx, cy
        for s in range(1, steps + 1):
            t = s / steps
            u = 1.0 - t
            px = (
                u * u * u * x0
                + 3 * u * u * t * x1
                + 3 * u * t * t * x2
                + t * t * t * x
            )
            py = (
                u * u * u * y0
                + 3 * u * u * t * y1
                + 3 * u * t * t * y2
                + t * t * t * y
            )
            add(px, py)

    while i < len(tokens):
        cmd = tokens[i]
        if cmd.isalpha():
            i += 1
        else:
            raise ValueError(f"expected command at {tokens[i]!r}")

        if cmd == "M":
            if ring:
                rings.append(ring)
                ring = []
            x, y = take(2)
            add(x, y)
            start = (cx, cy)
            while i < len(tokens) and not tokens[i].isalpha():
                x, y = take(2)
                add(x, y)
        elif cmd == "m":
            if ring:
                rings.append(ring)
                ring = []
            dx, dy = take(2)
            add(cx + dx, cy + dy)
            start = (cx, cy)
            while i < len(tokens) and not tokens[i].isalpha():
                dx, dy = take(2)
                add(cx + dx, cy + dy)
        elif cmd in "Ll":
            rel = cmd == "l"
            while i < len(tokens) and not tokens[i].isalpha():
                a, b = take(2)
                add(cx + a if rel else a, cy + b if rel else b)
        elif cmd in "Hh":
            rel = cmd == "h"
            while i < len(tokens) and not tokens[i].isalpha():
                a = take(1)[0]
                add(cx + a if rel else a, cy)
        elif cmd in "Vv":
            rel = cmd == "v"
            while i < len(tokens) and not tokens[i].isalpha():
                a = take(1)[0]
                add(cx, cy + a if rel else a)
        elif cmd in "Cc":
            rel = cmd == "c"
            while i < len(tokens) and not tokens[i].isalpha():
                vals = take(6)
                if rel:
                    x1, y1, x2, y2, x, y = (
                        cx + vals[0],
                        cy + vals[1],
                        cx + vals[2],
                        cy + vals[3],
                        cx + vals[4],
                        cy + vals[5],
                    )
                else:
                    x1, y1, x2, y2, x, y = vals
                cubic(x1, y1, x2, y2, x, y)
        elif cmd in "Zz":
            if ring and ring[0] != ring[-1]:
                ring.append(ring[0])
            rings.append(ring)
            ring = []
            cx, cy = start
        else:
            raise ValueError(f"unsupported SVG command {cmd!r}")

    if ring:
        rings.append(ring)
    return rings


def _transform(
    rings: list[list[tuple[float, float]]], scale: float, ox: float, oy: float
) -> list[list[tuple[float, float]]]:
    return [[(ox + x * scale, oy + y * scale) for x, y in ring] for ring in rings]


def _ink_bounds(
    rings: list[list[tuple[float, float]]],
) -> tuple[float, float, float, float]:
    xs = [p[0] for ring in rings for p in ring]
    ys = [p[1] for ring in rings for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


def _mirror_x(
    rings: list[list[tuple[float, float]]], width: float
) -> list[list[tuple[float, float]]]:
    return [[(width - x, y) for x, y in ring] for ring in rings]


def _brace_arm_faces(
    rings: list[list[tuple[float, float]]],
) -> tuple[float, float]:
    """Inner faces = rightmost of left ring, leftmost of right ring."""
    assert len(rings) == 2
    a, b = rings
    ax = sum(p[0] for p in a) / len(a)
    bx = sum(p[0] for p in b) / len(b)
    left_ring, right_ring = (a, b) if ax < bx else (b, a)
    return max(p[0] for p in left_ring), min(p[0] for p in right_ring)


def _draw_eye(
    draw: ImageDraw.ImageDraw,
    ex: float,
    ey: float,
    scale: float,
) -> None:
    """One eye at (ex, ey); sizes match pys-light.svg viewBox units × scale."""
    rx_o, ry_o = 1.1 * scale, 0.8 * scale
    rx_i, ry_i = 0.95 * scale, 0.68 * scale
    pr = 0.42 * scale
    hr = 0.14 * scale
    draw.ellipse([ex - rx_o, ey - ry_o, ex + rx_o, ey + ry_o], fill=FG)
    draw.ellipse([ex - rx_i, ey - ry_i, ex + rx_i, ey + ry_i], fill=SCLERA)
    draw.ellipse([ex - pr, ey - pr, ex + pr, ey + pr], fill=PUPIL)
    hx, hy = ex + 0.17 * scale, ey - 0.15 * scale
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=HIGHLIGHT)


def main() -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = 6
    draw.rounded_rectangle(
        [margin, margin, SIZE - margin, SIZE - margin],
        radius=28,
        fill=BG,
    )

    pad = 16
    usable = SIZE - 2 * pad
    scale = usable / 16.0
    ox = oy = float(pad)

    left_rings = _transform(_parse_path(_BRACE_LEFT), scale, ox, oy)
    right_rings = _transform(
        _mirror_x(_parse_path(_BRACE_LEFT), 16.0), scale, ox, oy
    )
    rings = left_rings + right_rings
    for ring in rings:
        draw.polygon(ring, fill=FG)

    _left, top, _right, bot = _ink_bounds(rings)
    cy = (top + bot) / 2.0

    lb_right, rb_left = _brace_arm_faces(rings)
    rx_o = 1.1 * scale
    between = 0.5 * scale
    pair = 4 * rx_o + between
    gap = rb_left - lb_right
    side = (gap - pair) / 2.0
    left_ex = lb_right + side + rx_o
    right_ex = left_ex + 2 * rx_o + between
    _draw_eye(draw, left_ex, cy, scale)
    _draw_eye(draw, right_ex, cy, scale)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG")
    ry = 0.8 * scale
    gap_l = (left_ex - rx_o) - lb_right
    gap_r = rb_left - (right_ex + rx_o)
    print(
        f"wrote {OUT}; eye_cy={cy:.1f} "
        f"vpad={cy - ry - top:.1f}/{bot - (cy + ry):.1f} "
        f"hpad={gap_l:.1f}/{gap_r:.1f} "
        f"viewBox cx={(left_ex - ox) / scale:.2f}/{(right_ex - ox) / scale:.2f}"
    )


if __name__ == "__main__":
    main()
