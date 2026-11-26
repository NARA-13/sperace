#!/usr/bin/env python3
"""
Per-pixel character rasterizer for SPERACE (v3).
Cute sperm-cell sprites: banded 32-bit shading, crisp dark outline,
expressive eyes, serpentine tail, boost / turn / hurt / cheer / blink frames.
Sprite cell: 48 x 56.
"""
import math

W, H = 48, 56
HEAD_CX, HEAD_CY = 24.0, 17.5
HEAD_RX, HEAD_RY = 14.2, 12.2
TAIL_Y0, TAIL_Y1 = 28.0, 54.0


def clamp(v, a, b):
    return a if v < a else (b if v > b else v)


def hexc(s, a=255):
    s = s.lstrip("#")
    return [int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a]


def mul(c, f):
    return [clamp(int(c[0] * f), 0, 255), clamp(int(c[1] * f), 0, 255), clamp(int(c[2] * f), 0, 255), c[3]]


def mix(c1, c2, t):
    t = clamp(t, 0, 1)
    return [int(c1[i] + (c2[i] - c1[i]) * t) for i in range(4)]


def hash2(x, y, s=0):
    n = (int(x) * 374761393 + int(y) * 668265263 + s * 1442695040888963407) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 < 1e-6:
        return math.hypot(px - ax, py - ay), 0.0
    t = clamp(((px - ax) * dx + (py - ay) * dy) / l2, 0.0, 1.0)
    return math.hypot(px - (ax + dx * t), py - (ay + dy * t)), t


def ramp(base, n=8):
    """Dark -> mid -> highlight palette from one base colour."""
    out = []
    for i in range(n):
        t = i / (n - 1)
        if t < 0.66:
            f = 0.68 + (t / 0.66) * 0.32          # 0.56 .. 1.00
        else:
            f = 1.00 + ((t - 0.66) / 0.34) * 0.22  # 1.00 .. 1.22
        c = mul(base, f)
        if t > 0.93:
            c = mix(c, [255, 255, 255, 255], 0.16)
        out.append(c)
    return out


def tail_points(phase, lean=0.0, boost=False):
    pts = []
    n = 20
    for i in range(n):
        t = i / (n - 1)
        y = TAIL_Y0 + t * (TAIL_Y1 - TAIL_Y0)
        amp = (6.2 if not boost else 3.4) * (0.25 + t ** 0.8)
        x = HEAD_CX + lean * 0.9 * (1.0 - t * 0.7) + math.sin(phase + t * 4.2) * amp
        pts.append((x, y, t))
    return pts


def render(head_hex, tail_hex, tail2_hex, phase=0.0, lean=0.0, boost=False,
           expression="normal", blink=False, cheer=False, t_param=0.0):
    head = hexc(head_hex)
    tail = hexc(tail_hex)
    tail2 = hexc(tail2_hex)
    hr = ramp(head, 8)
    tr = ramp(tail, 7)
    tr = [mix(c, mul(head, 0.9), 0.25) for c in tr]
    t2r = ramp(tail2, 5)
    outline = mix(mul(head, 0.30), [12, 4, 22, 255], 0.35)

    cy = HEAD_CY + math.sin(t_param * 1.6) * 0.5
    cx = HEAD_CX + lean * 0.6
    rx = HEAD_RX
    ry = HEAD_RY
    tpts = tail_points(phase, lean=lean, boost=boost)

    L = (-0.45, -0.72, 0.53)
    ll = math.sqrt(sum(v * v for v in L))
    L = tuple(v / ll for v in L)

    col = [[0, 0, 0, 0] for _ in range(W * H)]
    cov = [0] * (W * H)  # 0 empty, 1 head, 2 tail

    for y in range(H):
        for x in range(W):
            fx, fy = x + 0.5, y + 0.5
            # ---------- tail ----------
            best = None
            for i in range(len(tpts) - 1):
                d, tt = seg_dist(fx, fy, tpts[i][0], tpts[i][1], tpts[i + 1][0], tpts[i + 1][1])
                rt = 3.6 * (1.0 - tpts[i][2] * 0.82) + 0.7
                if d <= rt and (best is None or tpts[i][2] < best[0]):
                    best = (tpts[i][2], d, rt, tpts[i][0])
            if best is not None:
                t, d, rt, bx = best
                k = 1.0 - d / rt
                side = 1.0 if fx < bx else 0.45
                lam = 0.42 + 0.58 * k * (0.55 + 0.45 * side)
                idx = int(clamp(lam + (hash2(x, y, 5) - 0.5) * 0.05, 0, 1) * (len(tr) - 1) + 0.5)
                idx = int(clamp(idx, 0, len(tr) - 1))
                c = tr[idx]
                # tip fades to the second tail colour
                c = mix(c, t2r[int(clamp(idx * 0.8, 0, len(t2r) - 1))], t * 0.45)
                if d > rt - 0.9:
                    c = mix(c, outline, 0.55)
                col[y * W + x] = c
                cov[y * W + x] = 2
            # ---------- head ----------
            nx = (fx - cx) / rx
            ny = (fy - cy) / ry
            dd = nx * nx + ny * ny
            if dd <= 1.0:
                nz = math.sqrt(max(0.0, 1.0 - dd))
                lam = nx * L[0] + ny * L[1] + nz * L[2]
                lam = (lam + 0.60) / 1.46
                lam *= 0.93 + 0.07 * clamp(0.6 - ny, 0, 1)
                dth = (hash2(x, y, 1) - 0.5) * 0.055
                idx = int(clamp(lam + dth, 0, 1) * (len(hr) - 1) + 0.5)
                idx = int(clamp(idx, 0, len(hr) - 1))
                c = hr[idx]
                # specular
                sp = math.hypot(nx + 0.42, ny + 0.48)
                if sp < 0.22 and nz > 0.6:
                    c = mix(c, [255, 255, 255, 255], 0.30 * (1 - sp / 0.22))
                # top rim light
                if dd > 0.90 and ny < -0.15:
                    c = mix(c, hr[-1], 0.32)
                # bottom inner shadow
                if dd > 0.82 and ny > 0.55:
                    c = mix(c, hr[2], 0.22)
                if dd > 0.985:
                    c = mix(c, outline, 0.8)
                col[y * W + x] = c
                cov[y * W + x] = 1

    # ---------- outline pass (4-neighbour) ----------
    for y in range(H):
        for x in range(W):
            i = y * W + x
            if cov[i] != 0:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx2, ny2 = x + dx, y + dy
                if 0 <= nx2 < W and 0 <= ny2 < H:
                    j = ny2 * W + nx2
                    if cov[j] == 1:
                        col[i] = mix(outline, hr[0], 0.35)
                        break
                    if cov[j] == 2:
                        col[i] = mix(outline, t2r[0], 0.45)
                        break

    # ---------- face ----------
    def put(x, y, c, force=False):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < W and 0 <= y < H:
            i = y * W + x
            if force or cov[i] == 1:
                col[i] = c
                cov[i] = 1

    EYE = [
        ".wwwww.",
        "wwwwwww",
        "wiiiihw",
        "wippiww",
        "wippiiw",
        "wiiiiww",
        ".wwwww.",
    ]
    EYE_COL = {
        "w": [252, 250, 255, 255],
        "i": ([46, 34, 88, 255] if not boost else [104, 32, 62, 255]),
        "p": [14, 9, 24, 255],
        "h": [255, 255, 255, 255],
    }

    def put_eye(ex, ey):
        for ry_, row in enumerate(EYE):
            for cx_, ch in enumerate(row):
                if ch == ".":
                    continue
                xx = ex + cx_ - 3
                yy = ey + ry_ - 3
                c = EYE_COL[ch]
                if ch == "w":
                    c = [228, 236, 250, 255]
                put(xx, yy, c, True)
        # re-draw interior so the outer white ring stays as a subtle grey rim
        for ry_, row in enumerate(EYE):
            for cx_, ch in enumerate(row):
                if ch == "." or ch == "w":
                    continue
                put(ex + cx_ - 3, ey + ry_ - 3, EYE_COL[ch], True)

    ey = cy - 0.6
    for sx in (-1, 1):
        ex = round(cx + sx * 6.2)
        eyi = round(ey)
        if expression == "hurt":
            for k in range(4):
                put(ex - 2 + k, eyi - 2 + k, [30, 18, 40, 255], True)
                put(ex + 2 - k, eyi - 2 + k, [30, 18, 40, 255], True)
            continue
        if blink or expression == "blink":
            for k in (-2, -1, 0, 1, 2):
                put(ex + k, eyi + 1, [30, 18, 40, 255], True)
            for k in (-1, 0, 1):
                put(ex + k, eyi, [30, 18, 40, 255], True)
            put(ex - 3, eyi + 2, [30, 18, 40, 255], True)
            put(ex + 3, eyi + 2, [30, 18, 40, 255], True)
            continue
        if cheer:
            for oy_, row in enumerate([".#.. #.", ".#.#..", "..#..."]):
                pass
            for ox, oy in ((-2, 1), (-1, 0), (0, -1), (1, 0), (2, 1)):
                put(ex + ox, eyi + oy, [30, 18, 40, 255], True)
            continue
        put_eye(ex, eyi)

    ey = cy - 0.6
    for sx in (-1, 1):
        ex = round(cx + sx * 5.6)
        eyi = round(ey)
        if expression == "hurt":
            for k in range(4):
                put(ex - 2 + k, eyi - 2 + k, [30, 18, 40, 255], True)
                put(ex + 2 - k, eyi - 2 + k, [30, 18, 40, 255], True)
            continue
        if blink or expression == "blink":
            for k in (-2, -1, 0, 1, 2):
                put(ex + k, eyi + 1, [30, 18, 40, 255], True)
            put(ex - 1, eyi, [30, 18, 40, 255], True)
            put(ex, eyi, [30, 18, 40, 255], True)
            put(ex + 1, eyi, [30, 18, 40, 255], True)
            continue
        if cheer:
            for ox, oy in ((-2, 1), (-1, 0), (0, -1), (1, 0), (2, 1)):
                put(ex + ox, eyi + oy, [30, 18, 40, 255], True)
            continue
        put_eye(ex, eyi)

    # blush
    for sx in (-1, 1):
        bx = round(cx + sx * 10.4)
        for dx in (-2, -1, 0, 1, 2):
            for dy in (0, 1):
                if abs(dx) + dy < 3:
                    i = int(cy + 3.6 + dy) * W + (bx + dx)
                    if 0 <= i < W * H and cov[i] == 1:
                        col[i] = mix(col[i], [255, 128, 150, 255], 0.42)

    # mouth
    my = round(cy + 7.0)
    mx = round(cx)
    if expression == "hurt":
        for dx in (-1, 0, 1):
            put(mx + dx, my, [96, 30, 48, 255], True)
            put(mx + dx, my + 1, [140, 54, 70, 255], True)
        put(mx, my + 2, [96, 30, 48, 255], True)
    elif cheer:
        for dx in (-3, -2, -1, 0, 1, 2, 3):
            dy = int(abs(dx) * 0.55)
            put(mx + dx, my - 1 + dy, [70, 24, 40, 255], True)
        for dx in (-2, -1, 0, 1, 2):
            dy = int(abs(dx) * 0.55)
            put(mx + dx, my + dy, [176, 58, 78, 255], True)
    elif boost:
        for dx in (-2, -1, 0, 1, 2):
            put(mx + dx, my, [78, 24, 40, 255], True)
        for dx in (-1, 0, 1):
            put(mx + dx, my + 1, [78, 24, 40, 255], True)
    else:
        for dx in (-3, -2, -1, 0, 1, 2, 3):
            dy = int((abs(dx) ** 1.6) / 7.0)
            put(mx + dx, my + dy, [74, 26, 42, 255], True)
        for dx in (-2, -1, 0, 1, 2):
            dy = int((abs(dx) ** 1.6) / 7.0)
            put(mx + dx, my + dy + 1, [198, 108, 120, 255], True)

    return col


def to_image(px):
    from PIL import Image
    img = Image.new("RGBA", (W, H))
    img.putdata([tuple(p) for p in px])
    return img


def build_sheet(head_hex, tail_hex, tail2_hex):
    from PIL import Image
    frames = []
    for i in range(8):
        frames.append(render(head_hex, tail_hex, tail2_hex, phase=i / 8 * math.tau, t_param=i * 0.2))
    for i in range(4):
        frames.append(render(head_hex, tail_hex, tail2_hex, phase=i / 4 * math.tau, boost=True,
                             t_param=i * 0.3))
    for i in range(5):
        lean = (-2.6, -1.3, 0.0, 1.3, 2.6)[i]
        frames.append(render(head_hex, tail_hex, tail2_hex, phase=1.1 + i * 0.55, lean=lean,
                             t_param=i * 0.25))
    frames.append(render(head_hex, tail_hex, tail2_hex, phase=2.1, expression="hurt", t_param=0.4))
    frames.append(render(head_hex, tail_hex, tail2_hex, phase=0.5, cheer=True, t_param=0.1))
    frames.append(render(head_hex, tail_hex, tail2_hex, phase=1.0, blink=True, t_param=0.6))
    sheet = Image.new("RGBA", (W * len(frames), H))
    for i, f in enumerate(frames):
        sheet.paste(to_image(f), (i * W, 0))
    return sheet
