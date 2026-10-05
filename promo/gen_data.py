"""Generate procedural source images and run the REAL ASCII Vision engine over them.

Outputs assets/data.js (window.DATA) + assets/sunset.jpg used by the promo page.
"""
import base64, json, math, os, warnings
warnings.simplefilter("ignore")
import numpy as np
from PIL import Image, ImageFilter

from ascii_vision.engine import ConversionEngine
from ascii_vision.glyph_cache import GlyphCache
from ascii_vision.resources import default_font_path

OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f"{OUT}/assets", exist_ok=True)
rng = np.random.default_rng(7)


# ----------------------------------------------------------------- sunset image
def sunset(w=960, h=720):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    horizon = h * 0.62
    t = np.clip(y / horizon, 0, 1)
    top = np.array([18, 10, 70], np.float32)
    mid = np.array([190, 40, 120], np.float32)
    low = np.array([255, 170, 60], np.float32)
    sky = np.where(t[..., None] < 0.55,
                   top + (mid - top) * (t[..., None] / 0.55),
                   mid + (low - mid) * ((t[..., None] - 0.55) / 0.45))
    img = sky.copy()
    # sun
    cx, cy, r = w * 0.5, horizon - 70, 118
    d = np.hypot(x - cx, y - cy)
    glow = np.exp(-(d / 260) ** 2)[..., None] * np.array([255, 210, 120], np.float32) * 0.65
    img += glow
    disc = (d < r)[..., None]
    sun = np.array([255, 245, 190], np.float32) + (np.array([255, 120, 70], np.float32) - np.array([255, 245, 190], np.float32)) * np.clip((y - (cy - r)) / (2 * r), 0, 1)[..., None]
    img = np.where(disc, sun, img)
    # stars
    for _ in range(90):
        sx, sy = rng.integers(0, w), rng.integers(0, int(horizon * 0.5))
        img[sy:sy + 2, sx:sx + 2] = 255
    # mountains
    def ridge(base, amp, freq, phase, color, seed):
        xs = np.arange(w)
        line = base + sum(a * np.sin(xs * f * 0.01 + p) for a, f, p in zip(amp, freq, phase))
        mask = y >= line[None, :]
        return mask, np.array(color, np.float32)
    layers = [
        (horizon - 40, [40, 22, 10], [1.1, 2.7, 6.0], [0.3, 1.2, 2.0], (92, 28, 100), 1),
        (horizon - 5, [36, 18, 9], [1.7, 3.3, 7.1], [2.1, 0.4, 1.1], (52, 16, 78), 2),
        (horizon + 15, [26, 14, 6], [2.3, 4.1, 8.3], [1.1, 2.4, 0.2], (24, 8, 50), 3),
    ]
    for base, amp, freq, ph, col, seed in layers:
        mask, c = ridge(base, amp, freq, ph, col, seed)
        mask &= (y < horizon + 4) | (seed == 3)
        img = np.where(mask[..., None], c, img)
    # water
    water = y >= horizon + 40
    wy = np.clip((2 * (horizon + 40) - y).astype(int), 0, h - 1)
    ripple = (np.sin(y * 0.55 + x * 0.02) * 6).astype(int)
    wx = np.clip(np.arange(w)[None, :] + ripple, 0, w - 1)
    reflection = img[wy, wx] * 0.8 + np.array([10, 20, 60], np.float32) * 0.4
    img = np.where(water[..., None], reflection, img)
    # sun glitter
    streak = np.exp(-((x - cx) / 70) ** 2) * (np.sin(y * 0.9 + x * 0.05) > 0.4) * water
    img += streak[..., None] * np.array([255, 190, 110], np.float32) * 0.6
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))


# ----------------------------------------------------------------- donut frames
def donut_frames(n=90, size=360):
    frames = []
    theta = np.linspace(0, 2 * math.pi, 420)
    phi = np.linspace(0, 2 * math.pi, 1100)
    th, ph = np.meshgrid(theta, phi)
    th, ph = th.ravel(), ph.ravel()
    R1, R2, K2 = 1.0, 2.0, 5.0
    K1 = size * K2 * 2.7 / (8 * (R1 + R2))
    ct, st, cp, sp = np.cos(th), np.sin(th), np.cos(ph), np.sin(ph)
    for i in range(n):
        A, B = i / n * 2 * math.pi, i / n * 2 * math.pi * 2.0
        cA, sA, cB, sB = math.cos(A), math.sin(A), math.cos(B), math.sin(B)
        cx_, cy_ = R2 + R1 * ct, R1 * st
        x = cx_ * (cB * cp + sA * sB * sp) - cy_ * cA * sB
        yy = cx_ * (sB * cp - sA * cB * sp) + cy_ * cA * cB
        z = K2 + cA * cx_ * sp + cy_ * sA
        ooz = 1 / z
        xp = np.round(size / 2 + K1 * ooz * x).astype(int)
        yp = np.round(size / 2 - K1 * ooz * yy).astype(int)
        Lum = cp * ct * sB - cA * ct * sp - sA * st + cB * (cA * st - ct * sA * sp)
        valid = (xp >= 0) & (xp < size) & (yp >= 0) & (yp < size)
        lin = (yp * size + xp)[valid]
        idx = np.nonzero(valid)[0]
        order = np.argsort(ooz[idx])           # far -> near; later writes (near) win
        winner = np.full(size * size, -1, dtype=np.int64)
        winner[lin[order]] = idx[order]
        mask = winner >= 0
        w_ = winner[mask]
        L = np.zeros(size * size, np.float32)
        H = np.zeros(size * size, np.float32)
        L[mask] = 0.30 + 0.70 * np.clip((np.maximum(Lum[w_], -0.2) + 0.2) / 1.6, 0, 1) ** 0.8
        H[mask] = (th[w_] / (2 * math.pi) + i / n) % 1
        L, H = L.reshape(size, size), H.reshape(size, size)
        hh = 0.52 + 0.20 * H
        hi = np.floor(hh * 6).astype(int) % 6
        f = hh * 6 - np.floor(hh * 6)
        v = L * 0.95 + 0.05
        s_ = 0.75
        p, q, t_ = v * (1 - s_), v * (1 - f * s_), v * (1 - (1 - f) * s_)
        choices = [(v, t_, p), (q, v, p), (p, v, t_), (p, q, v), (t_, p, v), (v, p, q)]
        rgb = np.zeros((size, size, 3), np.float32)
        for k in range(6):
            m = hi == k
            for c in range(3):
                rgb[..., c][m] = choices[k][c][m]
        rgb[~mask.reshape(size, size)] = 0
        frames.append(np.clip(rgb * 255, 0, 255).astype(np.uint8))
    return frames


# ----------------------------------------------------------------- "webcam" blob
def blob_frames(n=60, w=480, h=360):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    frames = []
    for i in range(n):
        a = i / n * 2 * math.pi
        field = np.zeros((h, w), np.float32)
        for k in range(5):
            cx = w * (0.5 + 0.28 * math.cos(a * (1 + k % 2) + k * 1.3))
            cy = h * (0.5 + 0.26 * math.sin(a * (1 + (k + 1) % 2) + k * 0.9))
            r = 52 + 14 * math.sin(a * 2 + k)
            field += r * r / ((x - cx) ** 2 + (y - cy) ** 2 + 1)
        L = np.clip((field - 0.6) / 1.4, 0, 1)
        rgb = np.stack([L * 255, 90 + L * 150, 255 * (0.4 + 0.6 * L)], -1)
        rgb *= (L > 0.05)[..., None]
        frames.append(np.clip(rgb, 0, 255).astype(np.uint8))
    return frames


# ----------------------------------------------------------------- conversion helpers
FONT = default_font_path()


def engine_for(charset, metric, preset="Balanced"):
    cache = GlyphCache(FONT, 12, charset)
    e = ConversionEngine(cache, metric=metric, preset=preset)
    return e


def pack(chars, colors=None):
    d = {"rows": ["".join(r) for r in chars], "cols": int(chars.shape[1]), "n": int(chars.shape[0])}
    if colors is not None:
        d["colors"] = base64.b64encode(colors.astype(np.uint8).tobytes()).decode()
    return d


def convert(img, cols, charset="ascii", metric="MSE", preset="Balanced", color=False, invert=False):
    e = engine_for(charset, metric, preset)
    e.invert = invert
    frame = np.array(img.convert("RGB"))
    res = e.convert(frame, cols=cols, color_mode=color)
    if color:
        ch, co = res
        return pack(ch, co)
    return pack(res)


if __name__ == "__main__":
    img = sunset()
    img.save(f"{OUT}/assets/sunset.jpg", quality=92)
    data = {}
    C = 120
    data["hero_mono"] = convert(img, C)
    data["hero_color"] = convert(img, C, color=True)
    data["hero_color_white"] = convert(img, C, color=True, invert=True)
    # presets (same image, 64 cols so tiles stay legible)
    data["preset_fast"] = convert(img, 70, "shades", "Brightness", "Fast", color=True)
    data["preset_balanced"] = convert(img, 70, "ascii", "MSE", "Balanced", color=True)
    data["preset_high"] = convert(img, 70, "ascii", "SSIM", "High Quality", color=True)
    data["preset_max"] = convert(img, 70, "braille", "SSIM", "Maximum Quality", color=True)
    # charsets (large)
    for name in ("ascii", "shades", "blocks", "braille"):
        data[f"cs_{name}"] = convert(img, C, name, "MSE" if name != "braille" else "SSIM", color=True)
    # donut video and webcam
    dframes = donut_frames()
    data["donut"] = [convert(Image.fromarray(f).filter(ImageFilter.GaussianBlur(1.4)), 84, "ascii", "MSE", color=True) for f in dframes]
    Image.fromarray(dframes[10]).save(f"{OUT}/assets/donut_raw.png")
    bframes = blob_frames()
    data["blob"] = [convert(Image.fromarray(f).filter(ImageFilter.GaussianBlur(1.2)), 90, "ascii", "Brightness", "Fast", color=True) for f in bframes]
    # store original donut frames as small jpg strip for the "original" half
    strip = Image.new("RGB", (240 * 10, 240))
    for i in range(10):
        strip.paste(Image.fromarray(dframes[i * 9]).resize((240, 240)), (i * 240, 0))
    strip.save(f"{OUT}/assets/donut_strip.jpg", quality=90)
    with open(f"{OUT}/assets/data.js", "w") as f:
        f.write("window.DATA = " + json.dumps(data, separators=(",", ":")) + ";")
    print("data.js", os.path.getsize(f"{OUT}/assets/data.js") // 1024, "KB")
