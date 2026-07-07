# -*- coding: utf-8 -*-
"""Generate the LiveCSV application icon (static icon set).

Produces, under ``static/``:

* ``favicon.ico``  – multi-size Windows icon (16/32/48/64/128/256), used as the
  browser tab favicon **and** the Windows tray icon.
* ``icon.png``     – 256×256 PNG, used in the README.

The motif is a blue table/grid on a transparent background — a rounded outline
rectangle (the table border) filling most of the canvas, with one horizontal
header line at 50% and one vertical column line at 50% (2×2 equal-size cells),
no filled background. The green "Live" accent dot sits at the top-left inner
corner, flush with the table edges and ringed by a faint green glow. Strokes are bold so the icon stays legible
at small sizes (taskbar / favicon). Re-run any time: ``python backend/make_icon.py``.
"""

import os
from PIL import Image, ImageDraw, ImageChops, ImageOps, ImageFilter

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
BLUE = (37, 99, 235, 255)        # table strokes — matches the page accent (#2563eb)
GREEN = (22, 163, 74, 255)       # corner "Live" dot — the page --green (#16a34a)

# Geometry as fractions of the canvas size.
_RECT = (0.075, 0.075, 0.925, 0.925)   # outer table border — fills ~85% of the canvas
_CORNER = 0.106                         # corner radius — matches dot radius for consistent curvature
_HEADER_Y = 0.500                       # header divider line at 50% (equal-height rows)
_VDIV = (0.500,)                     # single vertical divider at center (2 columns)
_LINE_W = 0.100                         # stroke width — bold for small-size legibility
_DOT_R = 0.106                          # dot radius = table_size / 8, so diameter = table_size / 4


def draw(size):
    """Render the icon at *size*: blue 2×2 equal-size table grid with a green
    "Live" accent dot at the top-left inner corner, flush with the table edges and ringed by a faint green glow."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(1, round(size * _LINE_W))
    rad = max(lw + 1, round(size * _CORNER))   # keep radius > stroke so corners read as rounded
    x0, y0, x1, y1 = [round(size * f) for f in _RECT]
    hy = round(size * _HEADER_Y)
    vx1 = round(size * _VDIV[0])
    # full blue table: rounded border + header line + one column divider
    d.rounded_rectangle([x0, y0, x1, y1], radius=rad, outline=BLUE, width=lw)
    d.line([x0, hy, x1, hy], fill=BLUE, width=lw)
    for fx in _VDIV:
        vx = round(size * fx)
        d.line([vx, y0, vx, y1], fill=BLUE, width=lw)
    # open the top-left corner: erase cell-1's top + left border segments
    erase = Image.new("L", (size, size), 0)
    ed = ImageDraw.Draw(erase)
    ed.rectangle([0, 0, max(0, vx1 - lw // 2), y0 + rad], fill=255)   # top border of cell 1 + corner
    ed.rectangle([0, 0, x0 + rad, max(0, hy - lw // 2)], fill=255)    # left border of cell 1 + corner
    img.putalpha(ImageChops.multiply(img.split()[3], ImageOps.invert(erase)))
    # green "Live" accent dot at top-left corner of the table (edges flush with inner borders)
    dr = max(2, round(size * _DOT_R))
    cx, cy = x0 + dr, y0 + dr
    # faint soft halo behind the dot — sized to stay fully within the canvas
    # (reach ≤ distance from the dot to the nearest canvas edge), bright alpha kept
    gr = round(dr * 1.1)
    glow = Image.new("RGBA", (size, size), 0)
    ImageDraw.Draw(glow).ellipse([cx - gr, cy - gr, cx + gr, cy + gr], fill=GREEN)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(1, round(dr * 0.15))))
    glow.putalpha(glow.split()[3].point(lambda a: int(a * 0.95)))
    img = Image.alpha_composite(img, glow)
    # crisp dot on top of the glow
    d = ImageDraw.Draw(img)
    d.ellipse([cx - dr, cy - dr, cx + dr, cy + dr], fill=GREEN)
    return img


def main():
    os.makedirs(STATIC_DIR, exist_ok=True)
    sizes = [16, 32, 48, 64, 128, 256]
    # Supersample: draw at 4× the largest size, then downscale with LANCZOS
    # for crisp anti-aliased edges at small sizes (browser tab / taskbar).
    master = draw(1024)
    frames = [master.resize((s, s), Image.LANCZOS) for s in sizes]
    ico_path = os.path.join(STATIC_DIR, "favicon.ico")
    png_path = os.path.join(STATIC_DIR, "icon.png")
    frames[-1].save(ico_path, format="ICO", sizes=[(s, s) for s in sizes],
                    append_images=frames[:-1])
    frames[-1].save(png_path, format="PNG")
    print("wrote %s (sizes %s)" % (ico_path, sizes))
    print("wrote %s (256x256)" % png_path)


if __name__ == "__main__":
    main()
