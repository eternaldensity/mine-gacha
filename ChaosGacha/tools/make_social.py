#!/usr/bin/env python3
"""Generate social preview images (1200x630 PNG) for link unfurls.

Pure stdlib (no Pillow on this machine): shapes only, no text — the
embed title/description carry the words. Rerun after visual changes:

    python3 tools/make_social.py
"""
import math
import os
import random
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "web", "social")
ICON_DIR = os.path.join(ROOT, "web", "icons")
W, H = 1200, 630


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


GOLD = hexrgb("#f6c54c")
INK_TOP = hexrgb("#1b2130")
INK_BOT = hexrgb("#0c0f16")
LINK = hexrgb("#3d4457")


class Canvas:
    def __init__(self, w=W, h=H):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def background(self):
        w, h = self.w, self.h
        for y in range(h):
            t = y / (h - 1)
            c = tuple(round(a + (b - a) * t) for a, b in zip(INK_TOP, INK_BOT))
            row = bytes(c) * w
            self.px[y * w * 3:(y + 1) * w * 3] = row
        # vignette: darken toward the corners
        cx, cy = w / 2, h / 2
        maxd = math.hypot(cx, cy)
        for y in range(0, h, 2):
            for x in range(0, w, 2):
                f = 1.0 - 0.35 * (math.hypot(x - cx, y - cy) / maxd) ** 2
                i = (y * w + x) * 3
                self.px[i] = int(self.px[i] * f)
                self.px[i + 1] = int(self.px[i + 1] * f)
                self.px[i + 2] = int(self.px[i + 2] * f)

    def disc(self, cx, cy, r, c):
        r = int(round(r))
        for y in range(cy - r, cy + r + 1):
            dx = int(math.sqrt(max(0, r * r - (y - cy) ** 2)))
            for x in range(cx - dx, cx + dx + 1):
                self.set(x, y, c)

    def glow(self, cx, cy, r, c, layers=5):
        for i in range(layers, 0, -1):
            f = 0.25 + 0.75 * (1 - i / (layers + 1))
            dim = tuple(int(v * f * 0.45) for v in c)
            self.disc(cx, cy, r * (1 + i * 0.35), dim)

    def link(self, x0, y0, x1, y1, c, w=3):
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(steps + 1):
            t = i / steps
            self.disc(round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), w, c)

    def save(self, path):
        w, h = self.w, self.h
        raw = bytearray()
        for y in range(h):
            raw.append(0)
            raw += self.px[y * w * 3:(y + 1) * w * 3]
        def chunk(typ, data):
            out = struct.pack(">I", len(data)) + typ + data
            out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
            return out
        ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
        png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
               chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
        with open(path, "wb") as fh:
            fh.write(png)
        print(f"wrote {path} ({os.path.getsize(path)} bytes)")


def field(cv, rng, palette, n=90):
    pts = []
    for _ in range(n):
        x = rng.randrange(0, W)
        y = rng.randrange(0, H)
        c = palette[rng.randrange(len(palette))]
        dim = tuple(int(v * rng.uniform(0.25, 0.7)) for v in c)
        pts.append((x, y, dim))
    for i, (x, y, _) in enumerate(pts):
        best, bd = None, 1e9
        for j, (u, v, _) in enumerate(pts):
            if i == j:
                continue
            d = math.hypot(x - u, y - v)
            if d < bd:
                bd, best = d, j
        if best is not None and bd < 130:
            u, v, _ = pts[best]
            cv.link(x, y, u, v, LINK, 2)
    for x, y, dim in pts:
        cv.disc(x, y, rng.choice([2, 2, 3, 4]), dim)


def motif(cv, cx, cy, scale, sats):
    for (dx, dy, _c) in sats:
        cv.link(cx, cy, cx + int(dx * scale), cy + int(dy * scale), LINK, 4)
    cv.glow(cx, cy, int(26 * scale), GOLD)
    for dx, dy, c in sats:
        x, y = cx + int(dx * scale), cy + int(dy * scale)
        cv.glow(x, y, int(15 * scale), c, layers=3)
        cv.disc(x, y, int(15 * scale), c)
    cv.disc(cx, cy, int(26 * scale), GOLD)
    cv.disc(cx - int(7 * scale), cy - int(8 * scale), int(8 * scale), (255, 242, 207))


TREE_SATS = [(-150, -110, hexrgb("#7cc4ff")), (140, -120, hexrgb("#ff6bae")),
             (-170, 100, hexrgb("#11d939")), (160, 105, hexrgb("#b388ff")),
             (0, -170, hexrgb("#9bf3eb")), (-60, 150, hexrgb("#aed1d1"))]
GACHA_SATS = [(-150, -110, hexrgb("#74573e")), (140, -120, hexrgb("#acb9b8")),
              (-170, 100, hexrgb("#f5993d")), (160, 105, hexrgb("#ff6bae")),
              (0, -170, hexrgb("#9bf3eb")), (60, 150, hexrgb("#f61e1e"))]
INDEX_SATS = [(-150, -110, hexrgb("#7cc4ff")), (140, -120, hexrgb("#f5993d")),
              (-170, 100, hexrgb("#11d939")), (160, 105, hexrgb("#b388ff")),
              (0, -170, hexrgb("#acb9b8")), (-60, 150, hexrgb("#ff6bae"))]


def make(name, sats, palette, seed):
    rng = random.Random(seed)
    cv = Canvas()
    cv.background()
    field(cv, rng, palette)
    motif(cv, W // 2, H // 2, 1.0, sats)
    cv.save(os.path.join(OUT_DIR, name))


def make_icons():
    """App icons for the PWA manifest (opaque squares, OS masks them)."""
    sats = [(-1, -0.72, hexrgb("#7cc4ff")), (0.95, -0.78, hexrgb("#ff6bae")),
            (-1.1, 0.66, hexrgb("#11d939")), (1.05, 0.7, hexrgb("#b388ff")),
            (0, -1.05, hexrgb("#9bf3eb")), (-0.4, 1.0, hexrgb("#f5993d"))]
    for size, name in ((512, "icon-512.png"), (192, "icon-192.png"),
                       (180, "apple-touch-icon.png")):
        cv = Canvas(size, size)
        cv.background()
        cx = cy = size // 2
        for dx, dy, _c in sats:
            cv.link(cx, cy, cx + int(dx * size * 0.32), cy + int(dy * size * 0.32),
                    LINK, max(2, size // 160))
        cv.glow(cx, cy, int(size * 0.085), GOLD)
        for dx, dy, c in sats:
            x, y = cx + int(dx * size * 0.32), cy + int(dy * size * 0.32)
            cv.glow(x, y, int(size * 0.05), c, layers=3)
            cv.disc(x, y, int(size * 0.05), c)
        cv.disc(cx, cy, int(size * 0.085), GOLD)
        cv.disc(cx - int(size * 0.023), cy - int(size * 0.026),
                int(size * 0.026), (255, 242, 207))
        cv.save(os.path.join(ICON_DIR, name))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(ICON_DIR, exist_ok=True)
    tree_pal = [hexrgb(c) for c in
                ["#7cc4ff", "#b388ff", "#69f0ae", "#11d939", "#ffd54f"]]
    gacha_pal = [hexrgb(c) for c in
                 ["#74573e", "#acb9b8", "#f6c54c", "#f5993d", "#ff6bae", "#f61e1e"]]
    make("social-tree.png", TREE_SATS, tree_pal, 7)
    make("social-gacha.png", GACHA_SATS, gacha_pal, 21)
    make("social.png", INDEX_SATS, tree_pal + gacha_pal, 42)
    make_icons()


if __name__ == "__main__":
    main()
