"""Render marketplace extension icon: braces + eye (U+1F441)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "icons" / "pys-icon.png"
SIZE = 128
BG = (252, 148, 44, 255)  # brand orange #fc942c
FG = (255, 255, 255, 255)
EYE_WHITE = (255, 252, 245, 255)
PUPIL = (45, 30, 20, 255)
HIGHLIGHT = (255, 255, 255, 255)


def main() -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded square background
    margin = 6
    draw.rounded_rectangle(
        [margin, margin, SIZE - margin, SIZE - margin],
        radius=28,
        fill=BG,
    )

    # Try a bold mono font for braces; fall back to default.
    brace_font = None
    for name in (
        "C:/Windows/Fonts/consolab.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "DejaVuSansMono-Bold.ttf",
    ):
        try:
            brace_font = ImageFont.truetype(name, 72)
            break
        except OSError:
            continue
    if brace_font is None:
        brace_font = ImageFont.load_default()

    # Braces
    left = "{"
    right = "}"
    ly = 18
    draw.text((14, ly), left, font=brace_font, fill=FG)
    # Measure right brace to right-align
    rb = draw.textbbox((0, 0), right, font=brace_font)
    rw = rb[2] - rb[0]
    draw.text((SIZE - 14 - rw, ly), right, font=brace_font, fill=FG)

    # Eye (geometric stand-in for U+1F441 — crisp at 128px)
    cx, cy = SIZE // 2, SIZE // 2 + 4
    rx, ry = 28, 18
    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=EYE_WHITE, outline=FG, width=3)
    pr = 11
    draw.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=PUPIL)
    draw.ellipse([cx + 2, cy - 6, cx + 8, cy], fill=HIGHLIGHT)

    # Optional tiny Unicode label in metadata comment via sidecar not needed
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG")
    print(f"wrote {OUT} ({SIZE}x{SIZE}) braces+eye U+1F441")


if __name__ == "__main__":
    main()
