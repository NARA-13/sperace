#!/usr/bin/env python3
"""
SPERACE audio generator -- original soundtrack + SFX synthesized from scratch.
Outputs .wav into assets/audio, then converts to .ogg with ffmpeg.
"""
import math, os, subprocess, wave
import numpy as np

SR = 44100
OUT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                   "Godot_Project", "assets", "audio"))
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(1234)

# ------------------------------------------------------------------ helpers
def env(n, a, d, s, r, sus=0.7):
    total = n
    ai, di, ri = int(a * SR), int(d * SR), int(r * SR)
    si = max(0, total - ai - di - ri)
    e = np.concatenate([
        np.linspace(0, 1, max(1, ai), endpoint=False),
        np.linspace(1, sus, max(1, di), endpoint=False),
        np.full(si, sus),
        np.linspace(sus, 0, max(1, ri)),
    ])
    if len(e) < total:
        e = np.pad(e, (0, total - len(e)))
    return e[:total]


def osc(freq, dur, kind="saw", detune=0.0, vib=0.0, vib_rate=5.0, phase=0.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = freq * (1.0 + detune) * (1.0 + vib * np.sin(2 * math.pi * vib_rate * t))
    ph = 2 * np.pi * np.cumsum(f) / SR + phase
    if kind == "sine":
        return np.sin(ph)
    if kind == "tri":
        return 2 / np.pi * np.arcsin(np.sin(ph))
    if kind == "square":
        return np.sign(np.sin(ph))
    if kind == "pulse":
        return np.where((ph % (2 * np.pi)) < math.pi * 0.65, 1.0, -1.0)
    # saw
    return 2 * ((ph / (2 * np.pi)) % 1.0) - 1.0


def lowpass(x, cutoff):
    if cutoff >= SR / 2:
        return x
    a = math.exp(-2 * math.pi * cutoff / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def lowpass_fast(x, cutoff):
    """one-pole IIR via scipy-free vectorised approximation using lfilter-like recursion in blocks"""
    a = math.exp(-2 * math.pi * cutoff / SR)
    # use recursive filter via numpy frompyfunc fallback: simple loop in C through np.vectorize is slow,
    # so we approximate with an FFT-domain filter (zero-phase, good enough for music buses)
    n = len(x)
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    H = 1.0 / np.sqrt(1 + (freqs / max(1.0, cutoff)) ** 4)
    return np.fft.irfft(X * H, n)


def highpass_fast(x, cutoff):
    n = len(x)
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    H = 1.0 - 1.0 / np.sqrt(1 + (freqs / max(1.0, cutoff)) ** 4)
    return np.fft.irfft(X * H, n)


def note(name):
    """'A4' -> 440.0"""
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6,
             "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    n = name[:-1]
    octv = int(name[-1])
    return 440.0 * (2 ** ((names[n] + (octv - 4) * 12 - 9) / 12))


def kick(dur=0.28, punch=110, f0=150, f1=45):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 26)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 9)
    click = rng.normal(0, 1, n) * np.exp(-t * 220) * 0.5
    return np.tanh((body + click) * 1.6) * punch / 110


def snare(dur=0.22):
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    noise = highpass_fast(noise, 1200)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 26)
    return (noise * np.exp(-t * 18) * 0.7 + tone * 0.5)


def hat(dur=0.06, open_=False):
    d = 0.16 if open_ else dur
    n = int(d * SR)
    t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    noise = highpass_fast(noise, 7000)
    return noise * np.exp(-t * (14 if open_ else 70)) * 0.5


def write_wav(name, data, stereo=True):
    data = np.nan_to_num(data)
    peak = np.max(np.abs(data)) or 1.0
    data = data / peak * 0.92
    if data.ndim == 1 and stereo:
        data = np.stack([data, data], axis=1)
    pcm = (np.clip(data, -1, 1) * 32767).astype(np.int16)
    p = os.path.join(OUT, name + ".wav")
    with wave.open(p, "wb") as w:
        w.setnchannels(2 if stereo else 1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return p


def oggify(name, quality=4):
    wav = os.path.join(OUT, name + ".wav")
    ogg = os.path.join(OUT, name + ".ogg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
                    "-c:a", "libvorbis", "-q:a", str(quality), ogg], check=True)
    os.remove(wav)
    print("   ->", os.path.basename(ogg), f"{os.path.getsize(ogg)/1024:.0f} KB")


# ------------------------------------------------------------------ mixer
class Track:
    def __init__(self, seconds):
        self.n = int(seconds * SR)
        self.buf = np.zeros((self.n, 2), dtype=np.float64)

    def add(self, sig, at, gain=1.0, pan=0.0):
        i = int(at * SR)
        if i >= self.n:
            return
        sig = sig[: self.n - i]
        l = gain * math.sqrt(0.5 * (1 - pan))
        r = gain * math.sqrt(0.5 * (1 + pan))
        self.buf[i:i + len(sig), 0] += sig * l
        self.buf[i:i + len(sig), 1] += sig * r

    def finish(self, name, fade=None, loop_cross=True):
        b = self.buf
        if loop_cross:
            # crossfade the tail into the head so the loop is seamless
            xf = int(0.06 * SR)
            head = b[:xf].copy()
            tail = b[-xf:].copy()
            f = np.linspace(0, 1, xf)[:, None]
            b[:xf] = head * f + tail * (1 - f)
            b = b[:-xf]
        b = lowpass_fast(b.T[0], 15000), lowpass_fast(b.T[1], 15000)
        out = np.stack(b, axis=1)
        write_wav(name, out)
        oggify(name)
        return out


# ------------------------------------------------------------------ music
def music_race(name="music_race", bpm=128, bars=16, intense=False, seed=0):
    r = np.random.default_rng(seed)
    spb = 60.0 / bpm
    beat = 4
    total = bars * beat * spb
    tr = Track(total + 0.5)
    # chord progression (Am - F - C - G) in A minor
    prog = [("A2", ["A3", "C4", "E4"]), ("F2", ["F3", "A3", "C4"]),
            ("C3", ["C4", "E4", "G4"]), ("G2", ["G3", "B3", "D4"])]
    scale = ["A3", "B3", "C4", "D4", "E4", "G4", "A4", "C5", "D5", "E5"]

    for bar in range(bars):
        t0 = bar * beat * spb
        root, chord = prog[bar % 4]
        # bass: driving 8ths
        for k in range(8):
            t = t0 + k * spb / 2
            f = note(root) * (2 if k % 4 == 3 else 1)
            s = osc(f, spb * 0.46, "saw", detune=0, vib=0.0)
            s *= env(len(s), 0.004, 0.06, 0.0, 0.10, 0.55)
            s = lowpass_fast(s, 700 if not intense else 1100)
            tr.add(s, t, 0.34)
        # chord stabs on off-beats
        for k in range(4):
            t = t0 + (k + 0.5) * spb
            for ni, nn in enumerate(chord):
                s = osc(note(nn), spb * 0.35, "pulse", detune=0.002 * (ni - 1))
                s *= env(len(s), 0.006, 0.10, 0.0, 0.16, 0.35)
                s = lowpass_fast(s, 3200)
                tr.add(s, t, 0.085, pan=(ni - 1) * 0.35)
        # arp lead
        arp = [0, 4, 2, 5, 4, 1, 3, 6]
        for k in range(8):
            if r.random() < (0.35 if not intense else 0.15):
                continue
            t = t0 + k * spb / 2
            nn = scale[(arp[k] + bar) % len(scale)]
            s = osc(note(nn) * (2 if k % 2 else 1), spb * 0.42, "square",
                    vib=0.004, vib_rate=6.5)
            s *= env(len(s), 0.004, 0.09, 0.0, 0.20, 0.30)
            s = lowpass_fast(s, 5200)
            tr.add(s, t, 0.10, pan=0.25 if k % 2 else -0.25)
        # drums
        for b in range(4):
            t = t0 + b * spb
            tr.add(kick(), t, 0.95)
            if b in (1, 3):
                tr.add(snare(), t, 0.45, pan=0.05)
            for h in range(2):
                tr.add(hat(open_=(b == 3 and h == 1)), t + h * spb / 2, 0.24,
                       pan=-0.3 + 0.6 * h)
        if intense:
            for k in range(16):
                tr.add(hat(open_=False), t0 + k * spb / 4, 0.12, pan=0.4 if k % 2 else -0.4)
    tr.finish(name)


def music_menu(name="music_menu"):
    bpm = 96
    spb = 60.0 / bpm
    bars = 12
    total = bars * 4 * spb
    tr = Track(total + 0.5)
    prog = [("D3", ["D4", "F4", "A4"]), ("A2", ["A3", "C4", "E4"]),
            ("B2", ["B3", "D4", "F4"]), ("G2", ["G3", "B3", "D4"])]
    scale = ["D4", "E4", "F4", "G4", "A4", "C5", "D5"]
    for bar in range(bars):
        t0 = bar * 4 * spb
        root, chord = prog[bar % 4]
        # warm pad
        for ni, nn in enumerate(chord):
            s = osc(note(nn), 4 * spb, "saw", detune=0.003 * (ni - 1), vib=0.002, vib_rate=0.6)
            s *= env(len(s), 0.5, 0.4, 0.0, 0.7, 0.6)
            s = lowpass_fast(s, 1800)
            tr.add(s, t0, 0.10, pan=(ni - 1) * 0.4)
        # soft bass
        s = osc(note(root), 4 * spb, "sine")
        s *= env(len(s), 0.02, 0.5, 0.0, 0.6, 0.6)
        tr.add(s, t0, 0.28)
        # bell melody
        for k in range(3):
            if (bar + k) % 3 == 1:
                continue
            nn = scale[(bar * 3 + k * 2) % len(scale)]
            s = osc(note(nn) * 2, 1.1, "sine")
            s = s * env(len(s), 0.005, 0.5, 0.0, 0.5, 0.2) + 0.3 * osc(note(nn) * 4, 1.1, "sine") * env(int(1.1 * SR), 0.005, 0.3, 0.0, 0.6, 0.1)
            tr.add(s, t0 + k * 4 * spb / 3, 0.14, pan=0.2)
        # soft hats + occasional kick
        for h in range(4):
            tr.add(hat(open_=(h == 2)), t0 + h * spb, 0.09, pan=-0.2 + 0.13 * h)
        if bar % 2 == 0:
            tr.add(kick(dur=0.3, punch=70, f0=110, f1=42), t0, 0.45)
    tr.finish(name)


def music_final(name="music_final"):
    music_race(name=name, bpm=152, bars=12, intense=True, seed=9)


def sting_victory():
    tr = Track(6.5)
    seq = [("C5", 0.0), ("E5", 0.14), ("G5", 0.28), ("C6", 0.42), ("G5", 0.62), ("C6", 0.76)]
    for nn, t in seq:
        for kind, g in (("square", 0.16), ("saw", 0.10), ("sine", 0.12)):
            s = osc(note(nn), 1.4, kind, detune=0.002)
            s *= env(len(s), 0.005, 0.25, 0.0, 0.9, 0.35)
            s = lowpass_fast(s, 6000)
            tr.add(s, t, g)
    for nn, t in (("C4", 0.0), ("E4", 0.0), ("G4", 0.0)):
        s = osc(note(nn), 4.0, "saw", detune=0.004)
        s *= env(len(s), 0.05, 0.6, 0.0, 2.6, 0.5)
        s = lowpass_fast(s, 2400)
        tr.add(s, t, 0.10)
    for i in range(6):
        tr.add(kick(punch=80), 0.0 + i * 0.14 if i < 2 else 1.0 + i * 0.0, 0.5)
    tr.add(hat(open_=True), 0.0, 0.2)
    tr.add(hat(open_=True), 0.76, 0.25)
    tr.finish("sfx_victory", loop_cross=False)


def sting_defeat():
    tr = Track(5.0)
    for i, nn in enumerate(["A4", "G4", "F4", "E4", "D4"]):
        s = osc(note(nn), 1.2, "square", vib=0.01, vib_rate=4)
        s *= env(len(s), 0.01, 0.3, 0.0, 0.8, 0.4)
        s = lowpass_fast(s, 2200)
        tr.add(s, i * 0.42, 0.16)
    s = osc(note("A2"), 3.6, "saw")
    s *= env(len(s), 0.3, 1.0, 0.0, 2.0, 0.5)
    tr.add(lowpass_fast(s, 700), 0.4, 0.16)
    tr.finish("sfx_defeat", loop_cross=False)


# ------------------------------------------------------------------ sfx
def sfx_all():
    made = []

    def finish(name):
        w = write_wav(name, tr.buf if hasattr(tr, 'buf') else tr)
        oggify(name)
        made.append(name)

    # boost: rising whoosh
    tr = Track(0.9)
    n = int(0.55 * SR)
    t = np.arange(n) / SR
    f = 180 + 1100 * (t / 0.55) ** 1.6
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    s += rng.normal(0, 1, n) * np.exp(-t * 4.0) * 0.35
    s = highpass_fast(s, 200)
    tr.add(s, 0, 0.9)
    tr.add(lowpass_fast(rng.normal(0, 1, len(t)) * np.exp(-t * 8), 3000), 0.0, 0.25)
    tr.finish("sfx_boost", loop_cross=False)

    # powerup pickup: bright arpeggio
    tr = Track(0.7)
    for i, nn in enumerate(["C6", "E6", "G6", "C7"]):
        s = osc(note(nn), 0.28, "sine")
        s *= env(len(s), 0.002, 0.06, 0.0, 0.16, 0.15)
        tr.add(s, i * 0.045, 0.5)
        s2 = osc(note(nn) * 1.5, 0.2, "square")
        s2 *= env(len(s2), 0.002, 0.04, 0.0, 0.12, 0.1)
        tr.add(s2, i * 0.045, 0.08)
    tr.finish("sfx_pickup", loop_cross=False)

    # collision: thud + squish
    tr = Track(0.55)
    n = int(0.4 * SR)
    t = np.arange(n) / SR
    thud = np.sin(2 * np.pi * (90 * np.exp(-t * 8) + 40) * t) * np.exp(-t * 10)
    sq = lowpass_fast(rng.normal(0, 1, n), 1400) * np.exp(-t * 12) * 0.6
    tr.add(np.tanh((thud + sq) * 1.5), 0, 0.9)
    tr.finish("sfx_hit", loop_cross=False)

    # swim loop: soft water swish
    tr = Track(0.6)
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    s = lowpass_fast(rng.normal(0, 1, n), 2200) * (np.sin(np.pi * t / 0.5) ** 3) * 0.5
    tr.add(s, 0, 0.55)
    tr.finish("sfx_swim", loop_cross=True)

    # countdown beep
    tr = Track(0.45)
    s = osc(660, 0.16, "square") * env(int(0.16 * SR), 0.003, 0.05, 0.0, 0.1, 0.4)
    tr.add(lowpass_fast(s, 3000), 0, 0.45)
    tr.finish("sfx_beep", loop_cross=False)

    # GO
    tr = Track(0.9)
    for f0 in (880, 1320):
        s = osc(f0, 0.42, "square") * env(int(0.42 * SR), 0.003, 0.08, 0.0, 0.3, 0.4)
        tr.add(lowpass_fast(s, 5000), 0, 0.35)
    tr.add(kick(punch=90), 0, 0.7)
    tr.finish("sfx_go", loop_cross=False)

    # elimination: descending zap
    tr = Track(0.8)
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = 900 * np.exp(-t * 5) + 70
    s = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t * 3.5)
    s = lowpass_fast(s, 4000)
    tr.add(s, 0, 0.5)
    tr.add(lowpass_fast(rng.normal(0, 1, n), 900) * np.exp(-t * 6), 0, 0.3)
    tr.finish("sfx_eliminate", loop_cross=False)

    # crown transfer: shimmer
    tr = Track(1.1)
    for i, nn in enumerate(["E6", "G6", "B6", "E7", "B6"]):
        s = osc(note(nn), 0.5, "sine")
        s *= env(len(s), 0.004, 0.12, 0.0, 0.3, 0.2)
        tr.add(s, i * 0.07, 0.4, pan=-0.5 + i * 0.25)
    tr.add(hat(open_=True), 0, 0.16)
    tr.finish("sfx_crown", loop_cross=False)

    # ui click
    tr = Track(0.18)
    s = osc(1200, 0.06, "square") * env(int(0.06 * SR), 0.001, 0.02, 0.0, 0.03, 0.2)
    tr.add(s, 0, 0.3)
    tr.finish("sfx_click", loop_cross=False)

    # ui hover
    tr = Track(0.14)
    s = osc(1800, 0.045, "sine") * env(int(0.045 * SR), 0.001, 0.02, 0.0, 0.02, 0.1)
    tr.add(s, 0, 0.16)
    tr.finish("sfx_hover", loop_cross=False)

    # shield activate
    tr = Track(0.7)
    for f0 in (420, 630, 840):
        s = osc(f0, 0.45, "sine", vib=0.02, vib_rate=14)
        s *= env(len(s), 0.01, 0.15, 0.0, 0.28, 0.4)
        tr.add(s, 0, 0.22)
    tr.finish("sfx_shield", loop_cross=False)

    # teleport
    tr = Track(0.6)
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 2200 * np.exp(-t * 6) + 300
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4)
    tr.add(s, 0, 0.4)
    tr.add(highpass_fast(rng.normal(0, 1, n), 4000) * np.exp(-t * 9), 0, 0.2)
    tr.finish("sfx_teleport", loop_cross=False)

    # finish line fanfare
    tr = Track(1.6)
    for i, nn in enumerate(["C5", "E5", "G5", "C6", "G5", "C6"]):
        s = osc(note(nn), 0.6, "square")
        s *= env(len(s), 0.004, 0.12, 0.0, 0.3, 0.3)
        tr.add(lowpass_fast(s, 6000), i * 0.10, 0.22)
    tr.finish("sfx_finish", loop_cross=False)

    # ambient bubbles (race ambience loop)
    tr = Track(4.0)
    for i in range(9):
        t0 = rng.uniform(0, 3.6)
        f0 = rng.uniform(300, 900)
        d = rng.uniform(0.08, 0.2)
        s = osc(f0, d, "sine") * env(int(d * SR), 0.005, 0.03, 0.0, d * 0.8, 0.2)
        tr.add(s, t0, 0.10, pan=rng.uniform(-0.7, 0.7))
    hum = lowpass_fast(rng.normal(0, 1, int(3.9 * SR)), 180) * 0.16
    tr.add(hum, 0, 0.6)
    tr.finish("amb_race", loop_cross=True)


if __name__ == "__main__":
    print("music...")
    music_menu()
    music_race()
    music_final()
    print("stingers...")
    sting_victory()
    sting_defeat()
    print("sfx...")
    sfx_all()
    print("AUDIO DONE ->", OUT)
