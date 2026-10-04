"""Regression tests for bugs found during the pre-release quality audit."""

import os
import warnings

import numpy as np
import pytest
from PIL import Image

from ascii_vision.cli import main
from ascii_vision.config import ConfigManager
from ascii_vision.engine import MAX_OUTPUT_CELLS, ConversionEngine
from ascii_vision.exporter import ExportManager, to_html, to_svg
from ascii_vision.frame_provider import StaticImageFrameProvider
from ascii_vision.glyph_cache import CHARSET_PRESETS, GlyphCache
from ascii_vision.resources import default_font_path, missing_glyphs

FONT = default_font_path()


@pytest.fixture
def photo(tmp_path):
    """An 80x60 gradient image saved as PNG."""
    y, x = np.mgrid[0:60, 0:80]
    arr = np.stack([x * 3, y * 4, (x + y) * 2], axis=-1).clip(0, 255).astype(np.uint8)
    path = tmp_path / "photo.png"
    Image.fromarray(arr).save(path)
    return str(path)


# --- Resources / fonts --------------------------------------------------------

def test_bundled_font_is_found_without_a_checkout_relative_path():
    assert os.path.isfile(FONT)
    assert os.path.basename(FONT) == "JetBrainsMono-Regular.ttf"


def test_default_font_resolves_silently():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        resolved = ConfigManager().resolve_font_path(ConfigManager.DEFAULT_FONT_RELATIVE_PATH)
    assert os.path.isfile(resolved)


def test_braille_is_missing_from_default_font_but_cache_falls_back():
    braille = CHARSET_PRESETS["braille"]
    assert missing_glyphs(FONT, braille)
    with pytest.warns(RuntimeWarning, match="DejaVuSans"):
        cache = GlyphCache(FONT, 12, "braille")
    assert os.path.basename(cache.font_path) == "DejaVuSans.ttf"
    cache.render(target_size=(10, 10))
    densities = cache.cache.mean(axis=(1, 2))
    assert densities.max() > densities.min(), "all braille glyphs rendered identically"


def test_braille_conversion_produces_varied_output():
    y, x = np.mgrid[0:60, 0:80]
    frame = np.stack([x * 3] * 3, axis=-1).clip(0, 255).astype(np.uint8)
    with pytest.warns(RuntimeWarning):
        engine = ConversionEngine(GlyphCache(FONT, 12, "braille"), metric="Brightness", preset="Fast")
    chars = engine.convert(frame, cols=40)
    assert len(set(chars.ravel().tolist())) > 3


# --- Config / profiles --------------------------------------------------------

@pytest.mark.parametrize("preset", ["High Quality", "Maximum Quality", "High", "Max", "Fast", "Balanced"])
def test_schema_accepts_every_preset_the_gui_offers(preset):
    config = ConfigManager.get_default_config()
    config["preset"] = preset
    ConfigManager().set_config(config)


@pytest.mark.parametrize("name", ["../evil", "a/b", "a\\b", "", ".", "..", "x" * 100, "trailing "])
def test_profile_names_cannot_escape_the_profiles_dir(tmp_path, name):
    cm = ConfigManager(profiles_dir=tmp_path)
    with pytest.raises(ValueError):
        cm.save_profile(name)
    with pytest.raises(ValueError):
        cm.load_profile(name)


def test_saved_profile_is_portable(tmp_path):
    cm = ConfigManager(profiles_dir=tmp_path)
    cm.set_config(ConfigManager.get_default_config())
    path = cm.save_profile("mine")
    assert ConfigManager.DEFAULT_FONT_RELATIVE_PATH in path.read_text()


# --- Image loading ------------------------------------------------------------

def test_exif_orientation_is_applied(tmp_path):
    img = Image.new("RGB", (60, 40), "red")  # stored landscape
    exif = img.getexif()
    exif[0x0112] = 6  # display rotated 90 degrees
    path = tmp_path / "rot.jpg"
    img.save(path, exif=exif)
    frame = next(StaticImageFrameProvider(str(path)).get_frames())
    assert frame.shape[:2] == (60, 40)


def test_pathlike_input_is_accepted(photo):
    from pathlib import Path
    frame = next(StaticImageFrameProvider(Path(photo)).get_frames())
    assert frame.shape == (60, 80, 3)


# --- Engine -------------------------------------------------------------------

def _engine(metric="MSE", charset="ascii", preset="Balanced"):
    return ConversionEngine(GlyphCache(FONT, 12, charset), metric=metric, preset=preset)


def test_char_aspect_ratio_is_the_cell_ratio_not_the_ink_ratio():
    cache = GlyphCache(FONT, 12, "ascii")
    assert 0.35 < cache.char_aspect_ratio < 0.65


def test_png_export_preserves_image_proportions(photo, tmp_path):
    out = tmp_path / "out.png"
    assert main(["--input", photo, "--output", str(out), "--columns", "80"]) == 0
    width, height = Image.open(out).size
    assert (width / height) == pytest.approx(80 / 60, rel=0.08)


def test_invalid_column_counts_are_rejected():
    engine = _engine()
    frame = np.zeros((20, 20, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="at least 1"):
        engine.convert(frame, cols=0)


def test_absurdly_large_output_is_refused():
    engine = _engine()
    thin = np.zeros((4000, 3, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="too large"):
        engine.convert(thin, cols=200)
    assert MAX_OUTPUT_CELLS > 0


@pytest.mark.parametrize("metric", ["MSE", "SSIM"])
def test_vectorized_matching_agrees_with_per_block_metrics(metric):
    from ascii_vision.metrics import compute_mse, compute_ssim

    rng = np.random.default_rng(0)
    frame = rng.integers(0, 256, size=(60, 80, 3), dtype=np.uint8)
    engine = _engine(metric)
    engine.tone_weight = 1.0  # reference functions have no tone weighting
    out = engine.convert(frame, cols=20)

    glyphs = engine.glyph_cache.cache
    gh, gw = glyphs.shape[1:]
    rows, cols = out.shape
    import cv2
    gray = engine.preprocess_image(frame)
    low, high = glyphs.mean(axis=(1, 2)).min(), glyphs.mean(axis=(1, 2)).max()
    resized = cv2.resize(gray, (cols * gw, rows * gh), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    resized = low + resized * (high - low)
    blocks = resized.reshape(rows, gh, cols, gw).transpose(0, 2, 1, 3)
    for r in range(rows):
        for c in range(cols):
            if metric == "MSE":
                best = np.argmin(compute_mse(blocks[r, c], glyphs))
            else:
                best = np.argmax(compute_ssim(blocks[r, c], glyphs, 1.0))
            assert out[r, c] == engine.glyph_cache.charset[best]


def test_bright_areas_are_not_all_collapsed_onto_one_glyph():
    """Mid and bright tones must map onto different densities, not saturate at '@'."""
    ramp = np.tile(np.linspace(40, 255, 160, dtype=np.uint8), (30, 1))
    frame = np.stack([ramp] * 3, axis=-1)
    chars = _engine().convert(frame, cols=60)
    assert len(set(chars.ravel().tolist())) >= 6


def test_white_background_inverts_tones():
    ramp = np.tile(np.linspace(0, 255, 160, dtype=np.uint8), (30, 1))
    frame = np.stack([ramp] * 3, axis=-1)
    dark, light = _engine(), _engine()
    light.invert = True
    density = {c: m.mean() for c, m in dark.glyph_cache.cache_dict.items()}
    left_dark = np.mean([density[c] for c in dark.convert(frame, cols=60)[:, :10].ravel()])
    left_light = np.mean([density[c] for c in light.convert(frame, cols=60)[:, :10].ravel()])
    assert left_light > left_dark  # dark pixels need dense ink on a light page


# --- Exporters ----------------------------------------------------------------

def test_font_name_is_escaped_in_html_and_svg():
    chars = np.array([["a"]], dtype="U1")
    evil = 'x"><script>alert(1)</script>'
    assert "<script>" not in to_html(chars, evil, 12)
    assert "<script>" not in to_svg(chars, evil, 12)


def test_html_and_svg_use_the_same_cell_grid_as_png(tmp_path):
    chars = np.array([["a", "b"], ["c", "d"]], dtype="U1")
    manager = ExportManager()
    html_path, svg_path = tmp_path / "o.html", tmp_path / "o.svg"
    manager.save(chars, str(html_path), "JetBrains Mono", 12, font_path=FONT, format="html")
    manager.save(chars, str(svg_path), "JetBrains Mono", 12, font_path=FONT, format="svg")
    assert "line-height: 1.0000" not in html_path.read_text()
    assert 'height="' in svg_path.read_text()


# --- CLI ----------------------------------------------------------------------

def test_cli_profile_values_are_not_overridden_by_defaults(photo, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "platformdirs.user_config_dir", lambda *a, **k: str(tmp_path / "cfg"), raising=True
    )
    monkeypatch.setattr("ascii_vision.config.user_config_dir", lambda *a, **k: str(tmp_path / "cfg"))
    assert main(["--save-profile", "narrow", "--columns", "33", "--preset", "Fast"]) == 0
    out = tmp_path / "out.txt"
    assert main(["--profile", "narrow", "--input", photo, "--output", str(out)]) == 0
    assert len(out.read_text().splitlines()[0]) == 33
    out2 = tmp_path / "out2.txt"
    assert main(["--profile", "narrow", "--columns", "20", "--input", photo, "--output", str(out2)]) == 0
    assert len(out2.read_text().splitlines()[0]) == 20


@pytest.mark.parametrize("preset", ["High Quality", "maximum quality", "max", "FAST"])
def test_cli_accepts_gui_preset_names_in_any_case(photo, tmp_path, preset):
    assert main(["--input", photo, "--output", str(tmp_path / "o.txt"), "--preset", preset]) == 0


@pytest.mark.parametrize("columns", ["0", "-5", "abc"])
def test_cli_rejects_bad_columns(photo, tmp_path, columns):
    with pytest.raises(SystemExit) as exc:
        main(["--input", photo, "--output", str(tmp_path / "o.txt"), "--columns", columns])
    assert exc.value.code == 2


def test_cli_reports_oversized_output_cleanly(tmp_path, capsys):
    thin = tmp_path / "thin.png"
    Image.new("RGB", (3, 3000), "white").save(thin)
    assert main(["--input", str(thin), "--output", str(tmp_path / "o.txt"), "--columns", "200"]) == 1
    assert "too large" in capsys.readouterr().err


def test_cli_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "ascii-vision" in capsys.readouterr().out


def test_cli_video_keeps_source_fps_and_audio(tmp_path):
    av = pytest.importorskip("av")
    from fractions import Fraction

    src = tmp_path / "src.mp4"
    with av.open(str(src), "w") as out:
        v = out.add_stream("libx264", rate=25)
        v.width, v.height, v.pix_fmt = 64, 48, "yuv420p"
        a = out.add_stream("aac", rate=44100)
        a.layout = "mono"
        for i in range(25):
            frame = av.VideoFrame.from_ndarray(np.full((48, 64, 3), i * 9, dtype=np.uint8), format="rgb24")
            frame.pts = i
            for p in v.encode(frame):
                out.mux(p)
        for p in v.encode():
            out.mux(p)
        samples = (np.sin(np.arange(44100) * 0.05) * 3000).astype(np.int16).reshape(1, -1)
        afr = av.AudioFrame.from_ndarray(samples, format="s16", layout="mono")
        afr.sample_rate = 44100
        afr.pts = 0
        for p in a.encode(afr):
            out.mux(p)
        for p in a.encode():
            out.mux(p)

    dst = tmp_path / "ascii.mp4"
    assert main(["--input", str(src), "--output", str(dst), "--columns", "30"]) == 0
    with av.open(str(dst)) as result:
        video = next(s for s in result.streams if s.type == "video")
        assert video.codec_context.name == "h264"
        assert video.average_rate == Fraction(25)
        assert video.width % 2 == 0 and video.height % 2 == 0
        assert any(s.type == "audio" for s in result.streams)


def test_cli_reports_success_for_single_file(photo, tmp_path, capsys):
    out = tmp_path / "art.txt"
    assert main(["--input", photo, "--output", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "Saved" in printed and str(out) in printed


def test_cli_batch_prints_a_summary(photo, tmp_path, capsys):
    out_dir = tmp_path / "out"
    assert main(["--input-glob", photo, "--output", str(out_dir) + "/", "--format", "txt"]) == 0
    assert "1 file converted" in capsys.readouterr().out


def test_cli_success_marker_falls_back_on_ascii_consoles(monkeypatch):
    import io
    from ascii_vision import cli

    monkeypatch.setattr("sys.stdout", io.TextIOWrapper(io.BytesIO(), encoding="ascii"))
    assert cli._ok("done") == "OK done"
