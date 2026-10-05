"""Render the landing page's before/after pair.

A small numpy ray tracer draws glossy spheres on a checkered floor (soft gradients, sharp edges, reflections and
specular highlights: the content ASCII Vision shows off best). The ASCII half is produced by the real CLI, so the page
shows the tool's own output. No third-party photos are involved.

Writes site/assets/compare-original.webp and site/assets/compare-ascii.webp (both 960x720).

    pip install -e .                 # from the repository root
    python promo/gen_compare.py [columns]
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site", "assets")
W, H, SS = 960, 720, 2          # final size and supersampling factor (anti-aliasing)
COLUMNS = int(sys.argv[1]) if len(sys.argv) > 1 else 190
EPS = 1e-3

EYE = np.array([0.0, 1.7, -7.4], np.float32)
TARGET = np.array([0.0, 0.85, 0.0], np.float32)
FOV_Y = 38.0
LIGHT = np.array([-0.55, 0.85, -0.55], np.float32)
LIGHT /= np.linalg.norm(LIGHT)

# center, radius, colour, mirror reflectivity, specular strength
SPHERES = [
    ((0.0, 1.2, 0.0), 1.2, (0.00, 0.72, 1.00), 0.16, 0.9),
    ((-2.65, 0.8, -0.9), 0.8, (1.00, 0.08, 0.52), 0.12, 0.8),
    ((2.55, 0.9, -0.5), 0.9, (0.12, 1.00, 0.30), 0.14, 0.8),
    ((0.95, 0.42, -2.3), 0.42, (0.92, 0.94, 1.00), 0.85, 1.0),
    ((-1.2, 0.36, -2.7), 0.36, (1.00, 0.58, 0.00), 0.12, 0.8),
]
FLOOR_DARK = np.array([0.012, 0.016, 0.04], np.float32)
FLOOR_LIGHT = np.array([0.95, 0.98, 1.00], np.float32)
HORIZON = np.array([0.025, 0.010, 0.012], np.float32)
ZENITH = np.array([0.0, 0.0, 0.012], np.float32)
SUN_DIR = np.array([0.04, 0.16, 1.0], np.float32)
SUN_DIR /= np.linalg.norm(SUN_DIR)


def sky(d):
    t = np.clip(d[:, 1], 0, 1)[:, None] ** 0.45
    col = HORIZON * (1 - t) + ZENITH * t
    cos_sun = d @ SUN_DIR
    col += np.exp((cos_sun - 1) * 70)[:, None] * np.array([1.0, 0.62, 0.30], np.float32) * 0.45
    col += (cos_sun > 0.9985)[:, None] * np.array([1.0, 0.92, 0.7], np.float32)
    return col


def intersect(o, d):
    """Nearest hit per ray: distance and object id (-2 floor, -1 miss, k sphere)."""
    t = np.full(len(o), np.inf, np.float32)
    idx = np.full(len(o), -1, np.int8)
    with np.errstate(divide="ignore", invalid="ignore"):
        tp = -o[:, 1] / d[:, 1]
    floor = (d[:, 1] < 0) & (tp > EPS)
    t[floor], idx[floor] = tp[floor], -2
    for k, (c, r, *_rest) in enumerate(SPHERES):
        oc = o - np.array(c, np.float32)
        b = (oc * d).sum(1)
        disc = b * b - ((oc * oc).sum(1) - r * r)
        hit = disc > 0
        ts = np.where(hit, -b - np.sqrt(np.where(hit, disc, 0)), np.inf)
        closer = hit & (ts > EPS) & (ts < t)
        t[closer], idx[closer] = ts[closer], k
    return t, idx


def shade(o, d, depth):
    t, idx = intersect(o, d)
    col = sky(d)
    hit = idx != -1
    if not hit.any():
        return col
    oh, dh, th, ih = o[hit], d[hit], t[hit], idx[hit]
    p = oh + dh * th[:, None]
    n = np.zeros_like(p)
    base = np.zeros_like(p)
    refl = np.zeros(len(p), np.float32)
    spec_k = np.zeros(len(p), np.float32)

    f = ih == -2
    n[f] = (0, 1, 0)
    check = (np.floor(p[f, 0] / 1.3) + np.floor(p[f, 2] / 1.3)) % 2
    fc = np.where(check[:, None] > 0, FLOOR_LIGHT, FLOOR_DARK)
    fade = np.exp(-np.clip(th[f] - 6, 0, None) / 22)[:, None]       # blend into the horizon glow
    base[f] = fc * fade + HORIZON * 0.18 * (1 - fade)
    refl[f], spec_k[f] = 0.28, 0.25
    for k, (c, r, colour, rf, sp) in enumerate(SPHERES):
        m = ih == k
        n[m] = (p[m] - np.array(c, np.float32)) / r
        base[m], refl[m], spec_k[m] = colour, rf, sp

    diff = np.clip(n @ LIGHT, 0, None)
    shadow_t, _ = intersect(p + n * EPS * 4, np.broadcast_to(LIGHT, p.shape).copy())
    lit = np.isinf(shadow_t)
    half = LIGHT - dh
    half /= np.linalg.norm(half, axis=1, keepdims=True)
    spec = np.clip((n * half).sum(1), 0, None) ** 90 * spec_k * lit
    ambient = np.array([0.22, 0.26, 0.36], np.float32)
    rim = (np.clip(1 + (n * dh).sum(1), 0, 1) ** 3)[:, None] * np.array([0.25, 0.45, 0.7], np.float32) * (ih >= 0)[:, None] * 0.5
    out = base * (ambient + (diff * lit)[:, None] * 1.25) + spec[:, None] + rim * 0.5

    if depth > 0:
        cos_t = np.clip(-(n * dh).sum(1), 0, 1)
        kr = refl + (1 - refl) * (1 - cos_t) ** 5 * 0.4
        rd = dh - 2 * (dh * n).sum(1, keepdims=True) * n
        rc = shade(p + n * EPS * 4, rd, depth - 1)
        out = out * (1 - kr[:, None]) + rc * kr[:, None]
    col[hit] = out
    return col


def render():
    w, h = W * SS, H * SS
    fwd = TARGET - EYE
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, np.array([0, 1, 0], np.float32))
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    half_h = np.tan(np.radians(FOV_Y) / 2)
    xs = (np.arange(w, dtype=np.float32) + 0.5) / w * 2 - 1
    ys = 1 - (np.arange(h, dtype=np.float32) + 0.5) / h * 2
    gx, gy = np.meshgrid(xs * half_h * (w / h), ys * half_h)
    d = fwd + gx[..., None] * right + gy[..., None] * up
    d = (d / np.linalg.norm(d, axis=2, keepdims=True)).reshape(-1, 3).astype(np.float32)
    o = np.broadcast_to(EYE, d.shape).copy()
    img = np.empty((h * w, 3), np.float32)
    step = 400_000                                # keep peak memory modest
    for i in range(0, len(d), step):
        img[i:i + step] = shade(o[i:i + step], d[i:i + step], 2)
    img = img.reshape(h, w, 3)
    # vignette + filmic-ish tone curve + gamma
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r2 = ((xx / w - 0.5) ** 2 + (yy / h - 0.5) ** 2) * 1.6
    img *= (1 - r2)[..., None]
    img = img / (1 + 0.15 * img)
    img = np.clip(img, 0, 1) ** (1 / 2.2)
    img = img.reshape(H, SS, W, SS, 3).mean(axis=(1, 3))      # box-filter downsample
    return Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))


def main():
    os.makedirs(OUT, exist_ok=True)
    original = render()
    original.save(os.path.join(OUT, "compare-original.webp"), quality=90, method=6)
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = os.path.join(tmp, "scene.png"), os.path.join(tmp, "ascii.png")
        original.save(src)
        subprocess.run(
            [sys.executable, "-c", "import sys; from ascii_vision.cli import main; sys.exit(main())",
             "--input", src, "--output", dst, "--preset", "High Quality",
             "--columns", str(COLUMNS), "--color"],
            check=True,
        )
        ascii_img = Image.open(dst).convert("RGB")
        print("cli output", ascii_img.size)
        ascii_img.resize((W, H), Image.LANCZOS).save(os.path.join(OUT, "compare-ascii.webp"), quality=90, method=6)
    for name in ("compare-original.webp", "compare-ascii.webp"):
        print(name, os.path.getsize(os.path.join(OUT, name)) // 1024, "KB")


if __name__ == "__main__":
    main()
