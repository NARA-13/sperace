#!/usr/bin/env python3
"""
SPERACE asset generator: procedural 32-bit-inspired pixel art.
Outputs crisp PNGs (nearest-neighbour friendly) into assets/sprites/.
Everything is generated from code -- no placeholders, no external art.
"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import char_render
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Godot_Project", "assets", "sprites")
OUT = os.path.abspath(OUT)
os.makedirs(OUT, exist_ok=True)
SS = 4  # supersample factor for anti-aliased then hardened shapes

def new(w, h, col=(0, 0, 0, 0)):
    return Image.new("RGBA", (w, h), col)

def save(img, name):
    p = os.path.join(OUT, name)
    img.save(p)
    print("wrote", name, img.size)

def hexc(s, a=255):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)

def lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(len(c1)))

def shade(c, f):
    """multiply brightness, keep alpha"""
    return (max(0, min(255, int(c[0] * f))), max(0, min(255, int(c[1] * f))), max(0, min(255, int(c[2] * f))), c[3] if len(c) > 3 else 255)

# ---------------------------------------------------------------- character
# Head is a 32x28 ellipse, tail 32px, sprite = 48x48 (head + tail + a bit)
SPR_W, SPR_H = 48, 48
HEAD_RX, HEAD_RY = 15.0, 13.0
HEAD_CX, HEAD_CY = 24.0, 20.0

TAIL_PHASES = 8
BOOST_PHASES = 4
TURN_SET = 5  # lean index

def head_mask():
    m = new(SPR_W, SPR_H, (255, 255, 255, 255))
    d = ImageDraw.Draw(m)
    d.ellipse([HEAD_CX - HEAD_RX, HEAD_CY - HEAD_RY, HEAD_CX + HEAD_RX, HEAD_CY + HEAD_RY], fill=(255, 255, 255, 255))
    return m

def draw_tail(d, phase, color, thick=3.2, speed=1.0, boost=False):
    """Tail extends downward from the head, serpentine. phase in radians."""
    n = 26
    pts = []
    for i in range(n):
        t = i / (n - 1)
        y = HEAD_CY + HEAD_RY * 0.55 + t * (SPR_H - HEAD_CY - HEAD_RY * 0.55 - 2)
        amp = 5.2 * (t ** 0.75) / max(0.75, speed)
        x = HEAD_CX + math.sin(phase + t * 4.3) * amp
        pts.append((x, y))
    for i in range(len(pts) - 1):
        t = i / (len(pts) - 1)
        w = max(1, int(round(thick * (1.0 - t * 0.82))))
        d.line([pts[i], pts[i + 1]], fill=color, width=w)
    return pts

def draw_character(head_col, tail_col, tail_col2, eye_style="cute", phase=0.0, lean=0.0,
                   expression="normal", boost=False, blink=False, cheer=False):
    """Returns RGBA 48x48 sprite."""
    img = new(SPR_W, SPR_H)
    d = ImageDraw.Draw(img)
    cx = HEAD_CX + lean
    cy = HEAD_CY
    # ---- tail
    draw_tail(d, phase, tail_col2, thick=4.6)
    draw_tail(d, phase, tail_col, thick=2.9)
    # ---- outer glow rim
    d.ellipse([cx - HEAD_RX - 1.2, cy - HEAD_RY - 1.2, cx + HEAD_RX + 1.2, cy + HEAD_RY + 1.2],
              fill=shade(head_col, 0.42))
    # ---- head body
    d.ellipse([cx - HEAD_RX, cy - HEAD_RY, cx + HEAD_RX, cy + HEAD_RY], fill=head_col)
    # top-light shading bands (pixel-art banding)
    body = new(SPR_W, SPR_H)
    bd = ImageDraw.Draw(body)
    for i in range(6):
        f = 1.0 + 0.13 * (1.0 - i / 6.0)
        bd.ellipse([cx - HEAD_RX + i * 0.6, cy - HEAD_RY + i * 1.15,
                    cx + HEAD_RX - i * 0.6, cy + HEAD_RY - i * 0.35], fill=shade(head_col, f))
    mask = head_mask()
    img.paste(body, (0, 0), mask)
    # dark outline
    d = ImageDraw.Draw(img)
    d.arc([cx - HEAD_RX, cy - HEAD_RY, cx + HEAD_RX, cy + HEAD_RY], 200, 340, fill=shade(head_col, 1.45), width=2)
    d.arc([cx - HEAD_RX, cy - HEAD_RY, cx + HEAD_RX, cy + HEAD_RY], 20, 160, fill=shade(head_col, 0.6), width=2)
    # bottom shadow crescent
    sh = new(SPR_W, SPR_H)
    ImageDraw.Draw(sh).ellipse([cx - HEAD_RX + 2, cy - HEAD_RY + 9, cx + HEAD_RX - 2, cy + HEAD_RY + 2],
                               fill=shade(head_col, 0.74))
    crop = Image.new("L", (SPR_W, SPR_H), 0)
    cd = ImageDraw.Draw(crop)
    cd.ellipse([cx - HEAD_RX + 1, cy + 1, cx + HEAD_RX - 1, cy + HEAD_RY + 2], fill=110)
    img.paste(sh, (0, 0), crop)
    # gloss highlight
    d.ellipse([cx - 9, cy - 9.5, cx - 1.5, cy - 4.5], fill=shade(head_col, 1.9) + (255,) if len(shade(head_col,1.9))==3 else shade(head_col,1.9))
    # ---- eyes
    ex1, ex2 = cx - 6.0, cx + 6.0
    ey = cy - 1.5
    if expression == "hurt":
        for ex in (ex1, ex2):
            d.line([ex - 2.5, ey - 2.5, ex + 2.5, ey + 2.5], fill=(30, 20, 40, 255), width=2)
            d.line([ex + 2.5, ey - 2.5, ex - 2.5, ey + 2.5], fill=(30, 20, 40, 255), width=2)
    elif blink:
        for ex in (ex1, ex2):
            d.line([ex - 2.5, ey, ex + 2.5, ey], fill=(28, 18, 36, 255), width=2)
    else:
        for ex in (ex1, ex2):
            d.ellipse([ex - 3.2, ey - 3.8, ex + 3.2, ey + 3.8], fill=(255, 255, 255, 255))
            d.ellipse([ex - 2.4, ey - 2.6, ex + 2.4, ey + 3.2], fill=(38, 24, 58, 255))
            d.ellipse([ex - 1.3, ey - 1.8, ex + 1.1, ey + 1.0], fill=(20, 12, 32, 255))
            # sparkle
            d.point((int(ex - 1.0), int(ey - 2.0)), fill=(255, 255, 255, 255))
            d.ellipse([ex - 2.0, ey + 0.4, ex - 0.2, ey + 2.0], fill=(120, 200, 255, 160))
    # ---- mouth
    if expression == "hurt":
        d.ellipse([cx - 2.0, cy + 5.0, cx + 2.0, cy + 8.0], fill=(120, 40, 60, 255))
    elif cheer:
        d.arc([cx - 4.5, cy + 2.5, cx + 4.5, cy + 9.5], 0, 180, fill=(60, 25, 45, 255), width=2)
        d.ellipse([cx - 2.6, cy + 5.4, cx + 2.6, cy + 8.2], fill=(150, 50, 70, 255))
    elif boost:
        d.ellipse([cx - 3.0, cy + 4.0, cx + 3.0, cy + 8.0], fill=(70, 25, 45, 255))
        d.ellipse([cx - 1.6, cy + 5.6, cx + 1.6, cy + 7.8], fill=(180, 70, 90, 255))
    else:
        d.arc([cx - 4.0, cy + 2.5, cx + 4.0, cy + 8.0], 10, 170, fill=(70, 30, 50, 255), width=1)
    # ---- cheeks
    d.ellipse([cx - 11.5, cy + 2.5, cx - 8.0, cy + 5.2], fill=(255, 130, 150, 90))
    d.ellipse([cx + 8.0, cy + 2.5, cx + 11.5, cy + 5.2], fill=(255, 130, 150, 90))
    return img

# --------------------------------------------------------------- skins data
SKINS = [
    # id, head, tail, tail2
    ("classic",  "#f6e2c4", "#f9d7bb", "#e8a882"),
    ("ocean",    "#7fe3ff", "#4fb8f0", "#2b74c8"),
    ("toxic",    "#a8f06a", "#63c23a", "#2f7b22"),
    ("sunset",   "#ffb066", "#ff7a4d", "#c23b2e"),
    ("midnight", "#b79bff", "#6f52c8", "#3b2a7a"),
    ("golden",   "#ffe066", "#f0b429", "#a86c12"),
    ("diamond",  "#e9fbff", "#a9e2f5", "#6fb3d4"),
    ("neon",     "#c6ff4a", "#38f0c8", "#1b8f9c"),
    ("galaxy",   "#8f7dff", "#5b3fbf", "#20123f"),
    ("fire",     "#ff9a3c", "#f0482c", "#8f1b12"),
    ("ice",      "#d8f6ff", "#8fd4f2", "#4a91c4"),
    ("rainbow",  "#ff8ad4", "#8fd4f2", "#6ce07a"),
    ("bubblegum","#ffa8d8", "#ff6fae", "#a32d68"),
    ("emerald",  "#7df7b0", "#2fcb7c", "#137a4a"),
    ("obsidian", "#6b7280", "#3f4451", "#1c1f26"),
    ("lava",     "#ff6b3d", "#c42020", "#5c0d0d"),
    ("aurora",   "#a8f0ff", "#7c7cff", "#3b2fa0"),
    ("coral",    "#ffb3a7", "#ff7a6b", "#b83f3a"),
    ("royal",    "#c9a6ff", "#8a5cf0", "#45217a"),
    ("sand",     "#f2dca8", "#d9b678", "#9c7f45"),
    ("mint",     "#bff5d8", "#7fdcae", "#3f9c78"),
    ("vapor",    "#ffb3f0", "#b98cff", "#5c3fa0"),
    ("steel",    "#cfd8e3", "#8b98ab", "#4b5563"),
    ("cherry",   "#ff9aa8", "#e8455f", "#8a1b2c"),
]

def gen_characters():
    for sid, head, tail, tail2 in SKINS:
        sheet = char_render.build_sheet(head, tail, tail2)
        save(sheet, f"char_{sid}.png")

# ---------------------------------------------------------------- powerups
POWERUPS = [
    ("turbo",   "#ff9f1c", "#fff3b0"),
    ("shield",  "#4ff0ff", "#ffffff"),
    ("energy",  "#a8ff4a", "#e6ffd0"),
    ("magnet",  "#ff4fa3", "#ffd0e8"),
    ("ghost",   "#c9b6ff", "#ffffff"),
    ("dash",    "#ffd23f", "#ffffff"),
    ("stabilizer", "#7df7b0", "#e0fff0"),
    ("recovery", "#5ad1ff", "#e0f7ff"),
    ("teleport", "#b98cff", "#f0e6ff"),
    ("lucky",   "#ffe066", "#fffbe0"),
]

def star_poly(cx, cy, r1, r2, n=5, rot=-math.pi/2):
    pts = []
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r2
        a = rot + i * math.pi / n
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts

def gen_powerups():
    for pid, c, cl in POWERUPS:
        img = new(24, 24)
        d = ImageDraw.Draw(img)
        col = hexc(c)
        light = hexc(cl)
        # capsule shell
        d.ellipse([1, 1, 22, 22], fill=shade(col, 0.35))
        d.ellipse([2, 2, 21, 21], fill=col)
        # glass highlight
        d.arc([3, 3, 20, 20], 190, 330, fill=light, width=2)
        d.ellipse([6, 5, 10, 8], fill=(255, 255, 255, 220))
        if pid == "turbo":
            d.polygon([(8, 8), (17, 12), (8, 16)], fill=light)
            d.line([5, 12, 8, 12], fill=light, width=2)
        elif pid == "shield":
            d.polygon([(12, 5), (18, 8), (18, 13), (12, 19), (6, 13), (6, 8)], fill=light)
            d.polygon([(12, 8), (15, 10), (15, 12.5), (12, 16), (9, 12.5), (9, 10)], fill=col)
        elif pid == "energy":
            d.polygon([(13, 5), (7, 13), (11, 13), (10, 19), (17, 10), (13, 10)], fill=light)
        elif pid == "magnet":
            d.arc([6, 6, 18, 18], 180, 360, fill=light, width=4)
            d.rectangle([6, 12, 9, 18], fill=light)
            d.rectangle([15, 12, 18, 18], fill=light)
            d.rectangle([6, 16, 9, 18], fill=hexc("#ff4f4f"))
            d.rectangle([15, 16, 18, 18], fill=hexc("#4f7dff"))
        elif pid == "ghost":
            d.ellipse([7, 6, 17, 15], fill=light)
            d.rectangle([7, 12, 17, 16], fill=light)
            for i in range(3):
                d.polygon([(7 + i * 3.5, 16), (8.7 + i * 3.5, 19), (10.4 + i * 3.5, 16)], fill=col)
            d.ellipse([9, 9, 11, 11], fill=col)
            d.ellipse([13, 9, 15, 11], fill=col)
        elif pid == "dash":
            for i in range(3):
                x = 7 + i * 4
                d.polygon([(x, 7), (x + 4, 12), (x, 17), (x + 2, 12)], fill=light)
        elif pid == "stabilizer":
            d.line([12, 5, 12, 19], fill=light, width=2)
            d.line([5, 12, 19, 12], fill=light, width=2)
            d.ellipse([9, 9, 15, 15], fill=light)
            d.ellipse([10.5, 10.5, 13.5, 13.5], fill=col)
        elif pid == "recovery":
            d.arc([6, 6, 18, 18], 30, 300, fill=light, width=3)
            d.polygon([(16, 5), (20, 9), (15, 10)], fill=light)
        elif pid == "teleport":
            d.ellipse([7, 7, 17, 17], outline=light, width=2)
            d.ellipse([10, 10, 14, 14], fill=light)
            d.arc([3, 3, 21, 21], 40, 140, fill=light, width=1)
        elif pid == "lucky":
            d.polygon(star_poly(12, 12, 8, 3.4), fill=light)
            d.polygon(star_poly(12, 12, 4, 1.8), fill=col)
        save(img, f"pu_{pid}.png")

# ---------------------------------------------------------------- obstacles
def gen_obstacles():
    # cell cluster
    img = new(48, 48)
    d = ImageDraw.Draw(img)
    random.seed(7)
    d.ellipse([4, 6, 40, 42], fill=(90, 60, 110, 255))
    d.ellipse([6, 8, 38, 40], fill=(140, 96, 168, 255))
    for i in range(6):
        a = i * math.tau / 6
        x = 22 + math.cos(a) * 9
        y = 24 + math.sin(a) * 9
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(176, 130, 205, 255))
        d.ellipse([x - 3, y - 3, x + 2, y + 2], fill=(214, 178, 236, 255))
    d.ellipse([14, 16, 26, 26], fill=(120, 80, 150, 255))
    d.ellipse([18, 19, 22, 23], fill=(90, 40, 130, 255))
    save(img, "obs_cell.png")

    # rock / particle
    img = new(24, 24)
    d = ImageDraw.Draw(img)
    d.polygon([(4, 14), (7, 5), (15, 3), (21, 9), (19, 18), (11, 21)], fill=(70, 60, 90, 255))
    d.polygon([(6, 13), (9, 7), (14, 5), (18, 10), (17, 16), (11, 19)], fill=(110, 100, 135, 255))
    d.polygon([(9, 9), (13, 7), (16, 11), (12, 13)], fill=(160, 150, 185, 255))
    save(img, "obs_rock.png")

    # spiky virus
    img = new(32, 32)
    d = ImageDraw.Draw(img)
    for i in range(10):
        a = i * math.tau / 10
        x1, y1 = 16 + math.cos(a) * 8, 16 + math.sin(a) * 8
        x2, y2 = 16 + math.cos(a) * 15, 16 + math.sin(a) * 15
        d.line([x1, y1, x2, y2], fill=(200, 60, 90, 255), width=3)
        d.ellipse([x2 - 2, y2 - 2, x2 + 2, y2 + 2], fill=(255, 130, 150, 255))
    d.ellipse([4, 4, 28, 28], fill=(120, 30, 60, 255))
    d.ellipse([6, 6, 26, 26], fill=(196, 52, 88, 255))
    d.ellipse([10, 10, 22, 22], fill=(235, 96, 130, 255))
    d.ellipse([13, 12, 17, 16], fill=(255, 200, 215, 255))
    save(img, "obs_virus.png")

    # blob barrier segment (used in strips, tileable)
    img = new(32, 32)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([1, 1, 30, 30], radius=7, fill=(48, 84, 76, 255))
    d.rounded_rectangle([2, 2, 29, 29], radius=6, fill=(76, 128, 112, 255))
    d.rounded_rectangle([4, 4, 27, 27], radius=5, fill=(104, 168, 144, 255))
    d.ellipse([6, 6, 14, 12], fill=(150, 210, 180, 255))
    d.ellipse([16, 17, 25, 25], fill=(84, 140, 120, 255))
    save(img, "obs_barrier.png")

    # sticky zone
    img = new(48, 48)
    d = ImageDraw.Draw(img)
    for i in range(5):
        r = 22 - i * 3.5
        d.ellipse([24 - r, 24 - r, 24 + r, 24 + r], outline=(120, 160, 60, 200 - i * 25), width=2)
    for i in range(7):
        a = i * math.tau / 7
        x, y = 24 + math.cos(a) * 16, 24 + math.sin(a) * 16
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(180, 220, 90, 180))
    d.ellipse([18, 18, 30, 30], fill=(150, 200, 70, 210))
    save(img, "obs_sticky.png")

    # immune patrol cell
    img = new(40, 40)
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, 37, 37], fill=(30, 60, 110, 255))
    d.ellipse([4, 4, 35, 35], fill=(58, 108, 180, 255))
    d.ellipse([8, 8, 31, 31], fill=(92, 152, 224, 255))
    d.ellipse([13, 13, 26, 26], fill=(40, 74, 130, 255))
    for i in range(4):
        a = i * math.tau / 4 + 0.4
        x, y = 20 + math.cos(a) * 13, 20 + math.sin(a) * 13
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(220, 240, 255, 255))
    d.ellipse([16, 16, 24, 24], fill=(255, 220, 90, 255))
    d.ellipse([18, 18, 22, 22], fill=(255, 255, 200, 255))
    save(img, "obs_patrol.png")

    # rotating bar (long)
    img = new(96, 16)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 2, 95, 13], radius=5, fill=(52, 40, 80, 255))
    d.rounded_rectangle([1, 3, 94, 12], radius=4, fill=(96, 72, 140, 255))
    d.rounded_rectangle([3, 4, 92, 7], radius=2, fill=(150, 120, 200, 255))
    for x in range(6, 92, 12):
        d.ellipse([x, 5, x + 6, 11], fill=(255, 200, 80, 200))
    save(img, "obs_bar.png")

# ---------------------------------------------------------------- crown
def gen_crown():
    img = new(20, 16)
    d = ImageDraw.Draw(img)
    gold = (255, 210, 64, 255)
    gold_d = (200, 144, 20, 255)
    gold_l = (255, 246, 170, 255)
    d.polygon([(2, 13), (3, 4), (7, 8), (10, 2), (13, 8), (17, 4), (18, 13)], fill=gold_d)
    d.polygon([(3, 12), (4, 6), (7, 9), (10, 4), (13, 9), (16, 6), (17, 12)], fill=gold)
    d.rectangle([3, 11, 17, 13], fill=gold_d)
    d.rectangle([3, 10, 17, 11], fill=gold_l)
    d.ellipse([8, 7, 12, 12], fill=(255, 90, 120, 255))
    d.ellipse([4, 3, 6, 5], fill=gold_l)
    d.ellipse([14, 3, 16, 5], fill=gold_l)
    d.ellipse([9, 1, 11, 3], fill=gold_l)
    save(img, "crown.png")
    # sparkle
    img = new(9, 9)
    d = ImageDraw.Draw(img)
    d.polygon(star_poly(4.5, 4.5, 4.4, 1.2, 4), fill=(255, 250, 200, 255))
    d.polygon(star_poly(4.5, 4.5, 2.2, 0.6, 4), fill=(255, 255, 255, 255))
    save(img, "sparkle.png")

# ---------------------------------------------------------------- egg / finish
def gen_egg():
    S = 4
    W, H = 220, 280
    big = new(W * S, H * S)
    d = ImageDraw.Draw(big)
    cx, cy = W * S / 2, H * S / 2
    # egg silhouette: bottom-heavy ellipse
    bw, bh = 96 * S, 124 * S
    d.ellipse([cx - bw, cy - bh * 1.02, cx + bw, cy + bh * 0.92], fill=(255, 236, 214, 255))
    # rim
    d.ellipse([cx - bw - 5 * S, cy - bh * 1.02 - 5 * S, cx + bw + 5 * S, cy + bh * 0.92 + 5 * S],
              fill=(255, 200, 150, 255))
    d.ellipse([cx - bw, cy - bh * 1.02, cx + bw, cy + bh * 0.92], fill=(255, 240, 220, 255))
    # shading
    for i in range(16):
        f = 0.88 + 0.12 * (1 - i / 16)
        d.ellipse([cx - bw + i * 4 * S, cy - bh * 1.02 + i * 3 * S,
                   cx + bw - i * 4 * S, cy + bh * 0.92 - i * 1 * S],
                  fill=tuple(int(v * f) for v in (255, 240, 220, 255)))
    # bottom shadow
    d.chord([cx - bw + 8 * S, cy - bh * 0.1, cx + bw - 8 * S, cy + bh * 0.95], 0, 180, fill=(236, 196, 168, 255))
    # highlight
    d.ellipse([cx - bw * 0.55, cy - bh * 0.72, cx - bw * 0.05, cy - bh * 0.34], fill=(255, 255, 250, 235))
    d.ellipse([cx - bw * 0.42, cy - bh * 0.63, cx - bw * 0.22, cy - bh * 0.45], fill=(255, 255, 255, 255))
    # speckles
    random.seed(3)
    for i in range(60):
        a = random.random() * math.tau
        r = random.random() ** 0.6
        x = cx + math.cos(a) * bw * r * 0.85
        y = cy + math.sin(a) * bh * r * 0.85
        s = random.randint(1, 3) * S
        d.ellipse([x - s, y - s, x + s, y + s], fill=(240, 206, 180, 200))
    # heart-shaped zygote glow inside
    hx, hy = cx, cy + bh * 0.1
    hr = 22 * S
    d.ellipse([hx - hr - 12 * S, hy - hr - 12 * S, hx + hr + 12 * S, hy + hr + 12 * S], fill=(255, 190, 210, 90))
    d.ellipse([hx - hr, hy - hr, hx, hy], fill=(255, 150, 180, 170))
    d.ellipse([hx, hy - hr, hx + hr, hy], fill=(255, 150, 180, 170))
    d.polygon([(hx - hr, hy), (hx + hr, hy), (hx, hy + hr * 1.35)], fill=(255, 150, 180, 170))
    # outer glow ring
    small = big.resize((W, H), Image.LANCZOS)
    save(small, "egg.png")
    # crown halo for egg finish
    return

# ---------------------------------------------------------------- backgrounds
def gen_backgrounds():
    W, H = 512, 512
    random.seed(11)
    # base membrane tissue
    base = new(W, H, (26, 14, 42, 255))
    d = ImageDraw.Draw(base)
    for i in range(240):
        x = random.randint(0, W)
        y = random.randint(0, H)
        r = random.randint(6, 40)
        c = random.choice([(38, 22, 62, 255), (46, 28, 74, 255), (32, 18, 54, 255)])
        d.ellipse([x - r, y - r * 0.75, x + r, y + r * 0.75], fill=c)
    base = base.filter(ImageFilter.GaussianBlur(1.2))
    # veins
    d = ImageDraw.Draw(base)
    for v in range(40):
        x, y = random.randint(0, W), random.randint(0, H)
        ang = random.random() * math.tau
        pts = [(x, y)]
        for i in range(24):
            ang += random.uniform(-0.5, 0.5)
            x += math.cos(ang) * 9
            y += math.sin(ang) * 9
            pts.append((x, y))
        for i in range(len(pts) - 1):
            d.line([pts[i], pts[i + 1]], fill=(58 + random.randint(0, 18), 26, 62, 190), width=1)
    save(base, "bg_tissue.png")

    # tileable floaters (transparent)
    fl = new(W, H)
    d = ImageDraw.Draw(fl)
    for i in range(90):
        x, y = random.randint(0, W), random.randint(0, H)
        r = random.randint(2, 9)
        c = random.choice([(150, 120, 220, 60), (110, 220, 220, 55), (230, 160, 220, 45), (200, 240, 255, 40)])
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)
        d.ellipse([x - r * 0.4, y - r * 0.4, x + r * 0.2, y + r * 0.2], fill=(255, 255, 255, 70))
    # a few strands
    for i in range(14):
        x, y = random.randint(0, W), random.randint(0, H)
        ang = random.random() * math.tau
        for k in range(20):
            ang += random.uniform(-0.3, 0.3)
            nx, ny = x + math.cos(ang) * 6, y + math.sin(ang) * 6
            d.line([x, y, nx, ny], fill=(180, 200, 255, 40), width=1)
            x, y = nx, ny
    save(fl, "bg_floaters.png")

    # current arrows / streaks
    ar = new(64, 64)
    d = ImageDraw.Draw(ar)
    for i in range(3):
        y = 14 + i * 18
        d.polygon([(10, y), (34, y), (34, y - 5), (50, y + 3), (34, y + 11), (34, y + 6), (10, y + 6)],
                  fill=(120, 230, 255, 90))
    save(ar, "current_arrow.png")

    # splitter glow
    sg = new(64, 64)
    d = ImageDraw.Draw(sg)
    for i in range(20):
        a = int(120 * (1 - i / 20))
        d.ellipse([i, i, 63 - i, 63 - i], outline=(255, 220, 120, 60), width=1)
    save(sg, "splitter.png")

    # waves (tileable, cosmetic parallax)
    wv = new(512, 128)
    d = ImageDraw.Draw(wv)
    for row in range(4):
        pts = []
        for x in range(0, 520, 4):
            y = 24 + row * 26 + math.sin(x * 0.03 + row) * 8
            pts.append((x, y))
        for i in range(len(pts) - 1):
            d.line([pts[i], pts[i + 1]], fill=(80, 40, 120, 70), width=2)
    save(wv, "waves.png")

# ---------------------------------------------------------------- UI art
def gen_ui():
    # logo: SPERACE with gradient fill, chunky italic arcade lettering drawn as vector-ish blocks
    W, H = 900, 240
    from PIL import ImageFont
    fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Godot_Project", "assets", "fonts", "PressStart2P-Regular.ttf")
    fpath = os.path.abspath(fpath)
    img = new(W, H)
    try:
        font = ImageFont.truetype(fpath, 96)
    except Exception:
        font = ImageFont.load_default()
    tmp = new(W, H)
    td = ImageDraw.Draw(tmp)
    text = "SPERACE"
    bbox = td.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x0 = (W - tw) // 2 - bbox[0]
    y0 = (H - th) // 2 - bbox[1]
    # thick dark outline pass first
    for ox in range(-6, 7):
        for oy in range(-6, 7):
            if ox * ox + oy * oy <= 26:
                continue
            td.text((x0 + ox, y0 + oy), text, font=font, fill=(30, 8, 48, 255))
    for ox in range(-3, 4):
        for oy in range(-3, 4):
            if ox * ox + oy * oy > 9:
                continue
            td.text((x0 + ox, y0 + oy), text, font=font, fill=(46, 14, 66, 255))
    img.alpha_composite(tmp)
    # gradient fill clipped to the glyph mask
    mask = new(W, H, (0, 0, 0, 0))
    md = ImageDraw.Draw(mask)
    md.text((x0, y0), text, font=font, fill=(255, 255, 255, 255))
    grad = new(W, H)
    gd = ImageDraw.Draw(grad)
    c1 = (255, 246, 200)
    c2 = (255, 168, 72)
    c3 = (255, 92, 148)
    for y in range(H):
        t = y / H
        c = lerp(c1, c2, t * 2) if t < 0.5 else lerp(c2, c3, (t - 0.5) * 2)
        gd.line([(0, y), (W, y)], fill=c + (255,))
    img.paste(grad, (0, 0), mask)
    # top highlight sweep
    hl = new(W, H, (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.text((x0, y0), text, font=font, fill=(255, 255, 255, 255))
    band = new(W, H, (0, 0, 0, 0))
    ImageDraw.Draw(band).rectangle([0, 0, W, int(H * 0.42)], fill=(255, 255, 255, 255))
    hl = Image.composite(hl, new(W, H, (0, 0, 0, 0)), band.split()[3].point(lambda v: min(255, int(v * 0.35))))
    img.alpha_composite(hl)
    save(img, "logo.png")

    # sprite-ish logo lettering small (for HUD) -> just reuse scaled text in engine

    # panel 9-patch source (48x48, border 14)
    p = new(64, 64)
    d = ImageDraw.Draw(p)
    d.rounded_rectangle([0, 0, 63, 63], radius=10, fill=(18, 10, 32, 235))
    d.rounded_rectangle([1, 1, 62, 62], radius=9, outline=(120, 80, 190, 255), width=2)
    d.rounded_rectangle([3, 3, 60, 60], radius=8, outline=(56, 32, 96, 200), width=1)
    d.line([10, 4, 54, 4], fill=(200, 160, 255, 120), width=1)
    save(p, "ui_panel.png")

    # button states
    def button(fill_top, fill_bot, border, name):
        b = new(180, 52)
        d = ImageDraw.Draw(b)
        for y in range(52):
            c = lerp(fill_top, fill_bot, y / 51)
            d.line([(0, y), (179, y)], fill=c + (255,))
        m = Image.new("L", (180, 52), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, 179, 51], radius=8, fill=255)
        out = new(180, 52)
        out.paste(b, (0, 0), m)
        d = ImageDraw.Draw(out)
        d.rounded_rectangle([0, 0, 179, 51], radius=8, outline=border, width=2)
        d.line([8, 3, 172, 3], fill=(255, 255, 255, 90), width=1)
        d.line([8, 48, 172, 48], fill=(0, 0, 0, 90), width=1)
        save(out, name)

    button((120, 70, 210), (72, 36, 140), (190, 150, 255), "btn_normal.png")
    button((160, 110, 250), (104, 60, 190), (255, 220, 150), "btn_hover.png")
    button((70, 40, 120), (44, 24, 80), (90, 60, 140), "btn_disabled.png")

    # bar fill textures handled in engine via StyleBox

    # rank medal
    def medal(c1, c2, name):
        m = new(24, 24)
        d = ImageDraw.Draw(m)
        d.polygon([(12, 2), (22, 8), (22, 17), (12, 23), (2, 17), (2, 8)], fill=hexc(c2))
        d.polygon([(12, 4), (20, 9), (20, 16), (12, 21), (4, 16), (4, 9)], fill=hexc(c1))
        save(m, name)
    medal("#ffe066", "#c08a12", "medal_gold.png")
    medal("#dfe6ef", "#8a94a6", "medal_silver.png")
    medal("#f0b088", "#9c5a30", "medal_bronze.png")

    # crown small indicator for leaderboard
    ci = new(14, 12)
    d = ImageDraw.Draw(ci)
    d.polygon([(1, 10), (2, 3), (5, 6), (7, 1), (9, 6), (12, 3), (13, 10)], fill=(200, 144, 20, 255))
    d.polygon([(2, 9), (3, 4), (5, 7), (7, 3), (9, 7), (11, 4), (12, 9)], fill=(255, 214, 70, 255))
    d.rectangle([2, 8, 12, 10], fill=(255, 246, 170, 255))
    save(ci, "crown_small.png")

    # arrow marker for player on minimap
    am = new(10, 10)
    d = ImageDraw.Draw(am)
    d.polygon([(5, 0), (10, 9), (5, 6), (0, 9)], fill=(255, 255, 255, 255))
    save(am, "marker.png")

    # lock icon
    lk = new(14, 14)
    d = ImageDraw.Draw(lk)
    d.rectangle([2, 6, 11, 13], fill=(160, 150, 190, 255))
    d.arc([4, 1, 9, 8], 180, 360, fill=(160, 150, 190, 255), width=2)
    d.ellipse([5, 8, 8, 11], fill=(60, 50, 80, 255))
    save(lk, "lock.png")

    # trophy icon
    tr = new(20, 20)
    d = ImageDraw.Draw(tr)
    d.polygon([(3, 2), (17, 2), (15, 10), (10, 14), (5, 10)], fill=(255, 210, 64, 255))
    d.rectangle([9, 13, 11, 17], fill=(200, 150, 30, 255))
    d.rectangle([5, 16, 15, 19], fill=(230, 180, 50, 255))
    d.arc([0, 3, 6, 10], 90, 270, fill=(255, 210, 64, 255), width=1)
    d.arc([14, 3, 20, 10], 270, 90, fill=(255, 210, 64, 255), width=1)
    save(tr, "trophy.png")

    # coin
    co = new(16, 16)
    d = ImageDraw.Draw(co)
    d.ellipse([1, 1, 14, 14], fill=(190, 130, 20, 255))
    d.ellipse([2, 2, 13, 13], fill=(255, 208, 70, 255))
    d.ellipse([4, 4, 11, 11], fill=(255, 240, 160, 255))
    d.text((6, 3), "S", fill=(190, 130, 20, 255))
    save(co, "coin.png")

    # warning triangle
    wt = new(24, 22)
    d = ImageDraw.Draw(wt)
    d.polygon([(12, 1), (23, 21), (1, 21)], fill=(255, 200, 40, 255))
    d.polygon([(12, 5), (20, 19), (4, 19)], fill=(40, 24, 10, 255))
    d.rectangle([11, 9, 13, 15], fill=(255, 200, 40, 255))
    d.rectangle([11, 16, 13, 18], fill=(255, 200, 40, 255))
    save(wt, "warning.png")

def gen_icon():
    # app icon 128x128: character face + crown on a badge
    img = new(128, 128)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, 127, 127], radius=24, fill=(30, 16, 50, 255))
    for i in range(24):
        f = 1.0 + 0.02 * i
        d.ellipse([10 + i * 0.6, 12 + i * 0.6, 118 - i * 0.6, 116 - i * 0.6], outline=(60 + i * 3, 30, 90, 255), width=1)
    px = char_render.render("#f6e2c4", "#f9d7bb", "#e8a882", phase=1.0, t_param=1.0)
    ch = char_render.to_image(px)
    ch = ch.resize((96, 112), Image.LANCZOS)
    img.alpha_composite(ch, (14, 20))
    cr = Image.open(os.path.join(OUT, "crown.png")).resize((44, 36), Image.LANCZOS)
    img.alpha_composite(cr, (42, 8))
    save(img, "icon.png")

if __name__ == "__main__":
    gen_characters()
    gen_powerups()
    gen_obstacles()
    gen_crown()
    gen_egg()
    gen_backgrounds()
    gen_ui()
    gen_icon()
    print("ALL ASSETS DONE ->", OUT)
