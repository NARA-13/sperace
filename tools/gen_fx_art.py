#!/usr/bin/env python3
"""Particle / effect textures for SPERACE."""
import math, os
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

OUT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                   "Godot_Project", "assets", "sprites"))
os.makedirs(OUT, exist_ok=True)


def radial(size, power=2.2, color=(255, 255, 255), hard=0.0):
    a = np.zeros((size, size), dtype=np.float32)
    c = (size - 1) / 2.0
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c, y - c) / c
            v = max(0.0, 1.0 - d)
            a[y, x] = (v ** power) if d > hard else 1.0
    a = (a * 255).astype(np.uint8)
    img = Image.new("RGBA", (size, size), color + (0,))
    px = a
    img.putalpha(Image.fromarray(px))
    return img


def save(img, name):
    img.save(os.path.join(OUT, name))
    print("wrote", name, img.size)


# soft spark
save(radial(12, 2.0), "fx_spark.png")
# hard dot
save(radial(8, 1.0, hard=0.55), "fx_dot.png")
# ring
S = 32
ring = Image.new("RGBA", (S, S), (255, 255, 255, 0))
d = ImageDraw.Draw(ring)
for r in range(3):
    d.ellipse([2 + r, 2 + r, S - 3 - r, S - 3 - r], outline=(255, 255, 255, 255 - r * 60), width=2)
ring = ring.filter(ImageFilter.GaussianBlur(0.6))
save(ring, "fx_ring.png")
# bubble
b = Image.new("RGBA", (16, 16), (255, 255, 255, 0))
d = ImageDraw.Draw(b)
d.ellipse([3, 3, 12, 12], fill=(200, 240, 255, 140))
d.ellipse([4, 4, 11, 11], outline=(255, 255, 255, 220), width=1)
d.ellipse([6, 6, 8, 8], fill=(255, 255, 255, 240))
save(b, "fx_bubble.png")
# four point star
st = Image.new("RGBA", (24, 24), (255, 255, 255, 0))
d = ImageDraw.Draw(st)
d.polygon([(12, 0), (14, 10), (24, 12), (14, 14), (12, 24), (10, 14), (0, 12), (10, 10)],
          fill=(255, 255, 255, 255))
st = st.filter(ImageFilter.GaussianBlur(0.5))
save(st, "fx_star.png")
# soft smoke puff
sm = radial(32, 1.4, hard=0.0)
save(sm, "fx_smoke.png")
# light streak (for speed lines)
ls = Image.new("RGBA", (48, 6), (255, 255, 255, 0))
d = ImageDraw.Draw(ls)
for i in range(48):
    a = int(255 * math.sin(i / 47 * math.pi) ** 1.5)
    d.line([(i, 0), (i, 5)], fill=(255, 255, 255, a))
save(ls, "fx_streak.png")
# crown glow
cg = radial(64, 1.8)
save(cg, "fx_glow.png")
print("FX ART DONE")
