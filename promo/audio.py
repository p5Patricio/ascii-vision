"""Synthesise an original soundtrack for the promo (no samples, no third-party music)."""
import numpy as np
from scipy.signal import butter, sosfilt
import wave

SR = 44100
DUR = 40.0
N = int(SR * DUR)
rng = np.random.default_rng(11)
BOUNDS = [0, 3.4, 7.4, 11.4, 15.0, 18.6, 22.4, 26.4, 29.0, 32.8, 35.8]
BPM = 112
BEAT = 60 / BPM

L = np.zeros(N); R = np.zeros(N)


def add(sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N or i + len(sig) <= 0:
        return
    j = min(N, i + len(sig))
    seg = sig[: j - i] * gain
    L[i:j] += seg * (1 - max(0, pan)); R[i:j] += seg * (1 + min(0, pan))


def env(n, a=0.005, d=0.1, s=0.0, r=0.05):
    e = np.ones(n)
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, max(na, 1))
    if nd > 0 and na + nd < n:
        e[na:na + nd] = np.linspace(1, s, nd); e[na + nd:] = s
    if nr > 0 and nr < n:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype="low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype="high", fs=SR, output="sos"), x)


def tone(freq, dur, kind="sine", detune=0.0):
    t = np.arange(int(dur * SR)) / SR
    if kind == "saw":
        out = sum(2 * ((t * f) % 1) - 1 for f in (freq, freq * (1 + detune), freq * (1 - detune))) / 3
    elif kind == "tri":
        out = 2 * np.abs(2 * ((t * freq) % 1) - 1) - 1
    elif kind == "sq":
        out = np.sign(np.sin(2 * np.pi * freq * t))
    else:
        out = np.sin(2 * np.pi * freq * t)
    return out


def kick(vol=1.0):
    n = int(0.28 * SR); t = np.arange(n) / SR
    f = 48 + 120 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 11) * vol


def hat(vol=1.0, open_=False):
    n = int((0.16 if open_ else 0.05) * SR)
    x = hp(rng.standard_normal(n), 7000) * np.exp(-np.arange(n) / SR * (22 if open_ else 70))
    return x * vol


def snap(vol=1.0):
    n = int(0.18 * SR); t = np.arange(n) / SR
    x = hp(rng.standard_normal(n), 1800) * np.exp(-t * 26) + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * .5
    return x * vol


def whoosh(dur=0.55, rise=True):
    n = int(dur * SR); x = rng.standard_normal(n)
    out = np.zeros(n); blocks = 24
    for b in range(blocks):
        a, c = b * n // blocks, (b + 1) * n // blocks
        frac = b / blocks if rise else 1 - b / blocks
        fc = 300 + 7500 * frac ** 2
        out[a:c] = lp(x[a:c], min(fc, 16000), 1)
    e = np.sin(np.linspace(0, np.pi, n)) ** 1.6
    return out * e


def note(m):
    return 440 * 2 ** ((m - 69) / 12)


# ---------------------------------------------------------------- harmony: Am F C G (one chord per 2 bars of 4/4)
CHORDS = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
BASS = [33, 29, 36, 31]
bar = BEAT * 4
nbars = int(DUR / bar) + 1
for b in range(nbars):
    t0 = b * bar
    ch = CHORDS[(b // 2) % 4]
    # pad
    dur = bar * 1.02
    pad = sum(tone(note(m), dur, "saw", 0.004) for m in ch) / 3
    pad = lp(pad, 1500 + 700 * np.sin(b * .5)) * env(len(pad), 0.35, 0.2, 0.8, 0.6)
    add(pad, t0, 0.17, 0.1)
    pad2 = sum(tone(note(m + 12), dur, "tri") for m in ch) / 3
    add(lp(pad2, 2500) * env(len(pad2), 0.5, 0.2, 0.7, 0.6), t0, 0.07, -0.2)

# ---------------------------------------------------------------- drums & bass (start at 3.4, thin out for the end card)
for bi in range(int(DUR / BEAT)):
    t = bi * BEAT
    if t < 3.2 or t >= 35.7:
        continue
    energy = 0.55 if t < 7.4 else 1.0
    if t > 29.0 and t < 32.8:
        energy = 0.85
    add(kick(0.9 * energy), t, 1.0)
    add(hat(0.35 * energy), t + BEAT / 2, 1.0, 0.3)
    if bi % 4 == 2 or bi % 4 == 0 and t > 7.4:
        add(hat(0.18 * energy, True), t + BEAT * 0.75, 1.0, -0.3) if bi % 2 else None
    if bi % 2 == 1:
        add(snap(0.5 * energy), t, 0.8)
    # bass on 8ths
    cb = BASS[int(t / bar / 2) % 4]
    for k in range(2):
        tt = t + k * BEAT / 2
        f = note(cb + (12 if (bi + k) % 4 == 3 else 0))
        b = lp(tone(f, BEAT * .48, "saw", .003), 420) * env(int(BEAT * .48 * SR), 0.004, 0.12, .55, 0.03)
        add(b, tt, 0.36 * energy)

# ---------------------------------------------------------------- arpeggio plucks (16ths) from the first scene on, delayed
sixteenth = BEAT / 4
for si in range(int(DUR / sixteenth)):
    t = si * sixteenth
    if t < 0.6 or t >= 35.7:
        continue
    bar_i = int(t / bar); ch = CHORDS[(bar_i // 2) % 4]
    pat = [0, 1, 2, 1, 2, 1, 0, 2]
    m = ch[pat[si % 8]] + 24
    n = int(0.22 * SR)
    x = lp(tone(note(m), 0.22, "sq"), 3400) * np.exp(-np.arange(n) / SR * 16)
    g = 0.045 * (0.5 if t < 3.4 else 1.0) * (1.0 + 0.3 * np.sin(t * 0.8))
    add(x, t, g, 0.4 * np.sin(si * .7))
    add(x, t + sixteenth * 3, g * .35, -0.5)   # delay tap

# ---------------------------------------------------------------- transitions: whoosh into each boundary + hit
for bnd in BOUNDS[1:]:
    add(whoosh(0.5, True), bnd - 0.5, 0.2, 0.0)
    n = int(0.5 * SR); t = np.arange(n) / SR
    hit = np.sin(2 * np.pi * (52 + 90 * np.exp(-t * 20)) * t) * np.exp(-t * 6)
    add(hit, bnd, 0.75)
    add(hat(0.9, True), bnd, 0.25)

# ---------------------------------------------------------------- UI foley
add(snap(0.7), 3.4 + 1.4, 0.6)                              # drop the file
for bnd_t in np.arange(29.0 + 0.55, 29.0 + 2.6, 0.025):     # typing ticks
    n = int(0.012 * SR)
    tick = hp(rng.standard_normal(n), 2500) * np.exp(-np.arange(n) / SR * 400)
    add(tick, bnd_t, 0.12 * (0.7 + 0.6 * rng.random()), rng.uniform(-.3, .3))
for k, f in enumerate([880, 1318.5, 1760]):                  # install finished
    x = tone(f, 0.5, "sine") * np.exp(-np.arange(int(.5 * SR)) / SR * 6)
    add(x, 32.8 + 1.9 + k * 0.09, 0.16)

# ---------------------------------------------------------------- end card: riser, hit, bell arpeggio, tail
n = int(1.1 * SR); t = np.arange(n) / SR
riser = lp(tone(note(57) * (1 + 1.2 * t / 1.1), 1.1, "saw", .006), 6000) * (t / 1.1) ** 2
add(riser, 35.8 - 1.0, 0.12)
t = np.arange(int(2.4 * SR)) / SR
boom = np.sin(2 * np.pi * (46 + 130 * np.exp(-t * 14)) * t) * np.exp(-t * 2.4)
add(boom, 35.8 + 0.12, 0.8)
for k, m in enumerate([69, 72, 76, 81, 88]):
    d = 2.8; tt = np.arange(int(d * SR)) / SR
    bell = (np.sin(2 * np.pi * note(m) * tt) + .35 * np.sin(2 * np.pi * note(m) * 2.76 * tt) + .2 * np.sin(2 * np.pi * note(m) * 5.4 * tt)) * np.exp(-tt * 2.0)
    add(bell, 35.95 + k * 0.11, 0.11, (-0.4 + 0.2 * k))
for m in [57, 64, 69, 72, 76]:
    d = 4.2; tt = np.arange(int(d * SR)) / SR
    p = lp(tone(note(m), d, "saw", .005), 1800) * env(len(tt), 0.3, 0.3, 0.7, 1.6)
    add(p, 35.9, 0.07)

# ---------------------------------------------------------------- master
fade = np.ones(N); fi = int(0.3 * SR); fo = int(2.2 * SR)
fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo) ** 1.5
L *= fade; R *= fade
# gentle glue: highpass, soft clip, normalise
L, R = hp(L, 28), hp(R, 28)
peak = max(np.abs(L).max(), np.abs(R).max())
L, R = np.tanh(L / peak * 1.5) , np.tanh(R / peak * 1.5)
peak = max(np.abs(L).max(), np.abs(R).max())
L, R = L / peak * 0.84, R / peak * 0.84
pcm = np.stack([L, R], 1)
pcm = (np.clip(pcm, -1, 1) * 32767).astype("<i2")
with wave.open("promo_audio.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("audio ok", DUR, "s", "peak", float(np.abs(pcm).max()) / 32767)
