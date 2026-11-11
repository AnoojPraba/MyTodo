# Copyright (c) 2026 Anooj Prabaharan. All rights reserved.
"""Generate MyTodo's logo files from one geometry.

    static/icon.svg   header logo + browser tab icon (vector)
    static/icon.png   256 px PNG (apple-touch / fallbacks)
    icon.ico          Windows icon embedded in MyTodo.exe (16..256 px)
    icon.icns         Mac icon embedded in MyTodo.app (16..1024 px)

Concept: a check mark whose tail rises into an arrow -> "done, and moving up"
(tasks completed + performance). Needs Pillow:  pip install pillow
Run:  .venv\\Scripts\\python tools\\make_icon.py
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parent.parent

# design grid is 256 x 256
C1, C2 = "#4263eb", "#7048e8"          # indigo -> violet gradient
RADIUS = 58
CHECK = [(66, 136), (110, 178)]        # short stroke of the check
RISE_FROM, RISE_TO = (110, 178), (184, 96)   # long stroke, ends in arrow
STROKE = 30
HEAD_LEN, HEAD_HALF = 50, 40           # arrowhead size


def arrow_geometry():
    (x0, y0), (x1, y1) = RISE_FROM, RISE_TO
    dx, dy = x1 - x0, y1 - y0
    n = math.hypot(dx, dy)
    ux, uy = dx / n, dy / n            # direction of travel
    px, py = -uy, ux                   # perpendicular
    tip = (x1 + ux * HEAD_LEN * 0.55, y1 + uy * HEAD_LEN * 0.55)
    base = (tip[0] - ux * HEAD_LEN, tip[1] - uy * HEAD_LEN)
    left = (base[0] + px * HEAD_HALF, base[1] + py * HEAD_HALF)
    right = (base[0] - px * HEAD_HALF, base[1] - py * HEAD_HALF)
    shaft_end = (base[0] + ux * 6, base[1] + uy * 6)  # tuck shaft under the head
    return tip, left, right, shaft_end


def svg():
    tip, left, right, shaft_end = arrow_geometry()
    f = lambda p: f"{p[0]:.1f} {p[1]:.1f}"  # noqa: E731
    return f"""<!-- Copyright (c) 2026 Anooj Prabaharan. All rights reserved. -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-label="MyTodo">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{C1}"/>
      <stop offset="1" stop-color="{C2}"/>
    </linearGradient>
  </defs>
  <rect width="256" height="256" rx="{RADIUS}" fill="url(#g)"/>
  <path d="M{f(CHECK[0])} L{f(CHECK[1])} L{f(shaft_end)}" fill="none" stroke="#fff"
        stroke-width="{STROKE}" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M{f(left)} L{f(tip)} L{f(right)} Z" fill="#fff" stroke="#fff"
        stroke-width="8" stroke-linejoin="round"/>
</svg>
"""


def raster(size=1024):
    s = size / 256
    S = lambda p: (p[0] * s, p[1] * s)  # noqa: E731

    # diagonal gradient: vertical ramp, rotated 45 degrees, centre-cropped
    ramp = Image.linear_gradient("L").resize((size * 2, size * 2))
    ramp = ramp.rotate(45, resample=Image.BICUBIC)
    off = size // 2
    ramp = ramp.crop((off, off, off + size, off + size))
    bg = ImageOps.colorize(ramp, C1, C2).convert("RGBA")

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), RADIUS * s, fill=255)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.paste(bg, (0, 0), mask)

    d = ImageDraw.Draw(img)
    tip, left, right, shaft_end = arrow_geometry()
    pts = [S(CHECK[0]), S(CHECK[1]), S(shaft_end)]
    w = int(STROKE * s)
    d.line(pts, fill="white", width=w, joint="curve")
    for x, y in pts:  # round caps
        d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill="white")
    head = [S(left), S(tip), S(right)]
    d.polygon(head, fill="white")
    # soften the arrowhead corners like the SVG's 8-unit round-joined stroke
    d.line(head + [head[0], head[1]], fill="white", width=int(8 * s), joint="curve")
    return img


def main():
    (ROOT / "static").mkdir(exist_ok=True)
    (ROOT / "static" / "icon.svg").write_text(svg(), encoding="utf-8")
    big = raster(1024)
    big.resize((256, 256), Image.LANCZOS).save(ROOT / "static" / "icon.png")
    sizes = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64),
             (128, 128), (256, 256)]
    big.save(ROOT / "icon.ico", sizes=sizes)
    big.resize((32, 32), Image.LANCZOS).save(ROOT / "static" / "favicon.ico")
    big.save(ROOT / "icon.icns")  # Pillow writes all Mac sizes from the 1024 px image
    print("wrote static/icon.svg, static/icon.png, static/favicon.ico, icon.ico, icon.icns")


if __name__ == "__main__":
    main()
