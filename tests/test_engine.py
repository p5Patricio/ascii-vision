import os
import tempfile
import warnings
import numpy as np
import pytest
from PIL import Image

from ascii_vision.frame_provider import StaticImageFrameProvider
from ascii_vision.glyph_cache import GlyphCache
from ascii_vision.metrics import (
    brightness_mapping,
    brightness_mapping_vectorized,
    compute_mse,
    compute_ssim
)
from ascii_vision.exporter import to_txt, to_html, to_svg, to_png, to_clipboard
from ascii_vision.config import ConfigManager
from ascii_vision.engine import ConversionEngine

# Path to the bundled font for testing
TEST_FONT_PATH = "assets/fonts/JetBrainsMono-Regular.ttf"

# =====================================================================
# 1. Frame Provider Tests
# =====================================================================

def test_static_image_frame_provider_from_image():
    # Create a small red test image in memory
    img = Image.new("RGB", (30, 20), color="red")
    provider = StaticImageFrameProvider(img)
    
    assert provider.total_frames == 1
    frames = list(provider.get_frames())
    assert len(frames) == 1
    
    frame = frames[0]
    assert isinstance(frame, np.ndarray)
    assert frame.shape == (20, 30, 3)
    # Check it's red (RGB: [255, 0, 0])
    assert np.all(frame[:, :, 0] == 255)
    assert np.all(frame[:, :, 1] == 0)
    assert np.all(frame[:, :, 2] == 0)

def test_static_image_frame_provider_from_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "test.png")
        img = Image.new("RGB", (10, 15), color="blue")
        img.save(img_path)
        
        provider = StaticImageFrameProvider(img_path)
        assert provider.total_frames == 1
        
        frames = list(provider.get_frames())
        assert len(frames) == 1
        assert frames[0].shape == (15, 10, 3)

def test_static_image_frame_provider_invalid_source():
    with pytest.raises(TypeError):
        StaticImageFrameProvider(12345)


# =====================================================================
# 2. Glyph Cache Tests
# =====================================================================

def test_glyph_cache_initialization():
    # Bundled font must exist
    assert os.path.exists(TEST_FONT_PATH)
    cache = GlyphCache(font_path=TEST_FONT_PATH, font_size=12, charset="ascii")
    
    # Monospace font aspect ratio should be around 0.5-0.6
    assert 0.1 < cache.char_aspect_ratio < 1.0

def test_glyph_cache_render_float():
    cache = GlyphCache(font_path=TEST_FONT_PATH, font_size=10, charset="shades")
    cache.render(target_size=(12, 8), as_float=True)
    
    # Check shape: (len(" ░▒▓█"), height, width) -> (5, 12, 8)
    assert cache.cache.shape == (5, 12, 8)
    assert cache.cache.dtype == np.float32
    assert np.all(cache.cache >= 0.0) and np.all(cache.cache <= 1.0)
    assert len(cache.cache_dict) == 5
    assert '█' in cache.cache_dict
    assert cache.cache_dict[' '].shape == (12, 8)

def test_glyph_cache_render_bool():
    cache = GlyphCache(font_path=TEST_FONT_PATH, font_size=12, charset="blocks")
    cache.render(target_size=(10, 10), as_float=False)
    
    assert cache.cache.shape[1:] == (10, 10)
    assert cache.cache.dtype == bool
    assert isinstance(cache.cache_dict['■'], np.ndarray)


# =====================================================================
# 3. Metrics Tests
# =====================================================================

def test_brightness_mapping():
    # 2D Block
    block = np.zeros((10, 10), dtype=np.uint8)
    assert brightness_mapping(block, num_chars=10) == 0
    
    block_full = np.ones((10, 10), dtype=np.uint8) * 255
    assert brightness_mapping(block_full, num_chars=10) == 9
    
    # Grayscale float block
    block_float = np.ones((5, 5), dtype=np.float32) * 0.5
    assert brightness_mapping(block_float, num_chars=5) == 2

def test_brightness_mapping_vectorized():
    # Row of blocks (3 blocks, 4x4 size)
    blocks = np.zeros((3, 4, 4), dtype=np.uint8)
    blocks[1] = 128  # Mid brightness
    blocks[2] = 255  # Max brightness
    
    indices = brightness_mapping_vectorized(blocks, num_chars=5)
    assert indices.shape == (3,)
    assert indices[0] == 0
    assert indices[1] == 2
    assert indices[2] == 4

def test_compute_mse():
    # Target block: all ones (10x10)
    block = np.ones((10, 10), dtype=np.float32)
    # Glyph 0: all zeros; Glyph 1: all ones
    glyphs = np.zeros((2, 10, 10), dtype=np.float32)
    glyphs[1] = 1.0
    
    mse_scores = compute_mse(block, glyphs)
    assert mse_scores.shape == (2,)
    # MSE against zeros is 1.0, against itself is 0.0
    assert mse_scores[0] == pytest.approx(1.0)
    assert mse_scores[1] == pytest.approx(0.0)

def test_compute_ssim():
    # Simple block and identical glyph
    block = np.random.rand(10, 10).astype(np.float32)
    glyphs = np.zeros((2, 10, 10), dtype=np.float32)
    glyphs[0] = block
    glyphs[1] = 1.0 - block
    
    ssim_scores = compute_ssim(block, glyphs, dynamic_range=1.0)
    assert ssim_scores.shape == (2,)
    # SSIM against itself is 1.0
    assert ssim_scores[0] == pytest.approx(1.0, abs=1e-5)
    # SSIM against inverted is lower
    assert ssim_scores[1] < 1.0


# =====================================================================
# 4. Exporter Tests
# =====================================================================

def test_exporters():
    matrix = np.array([
        ['A', 'B', 'C'],
        ['D', 'E', 'F']
    ], dtype='U1')
    
    # 1. Plaintext
    txt = to_txt(matrix)
    assert txt == "ABC\nDEF"
    
    # 2. HTML
    html_out = to_html(matrix, "Courier", 14)
    assert "<html>" in html_out
    assert "Courier" in html_out
    assert "14px" in html_out
    assert "ABC\nDEF" in html_out or "ABC" in html_out
    
    # 3. SVG
    svg_out = to_svg(matrix, "JetBrains Mono", 12)
    assert "<svg" in svg_out
    assert "JetBrains Mono" in svg_out
    assert "</svg>" in svg_out
    
    # 4. PNG
    png_img = to_png(matrix, TEST_FONT_PATH, 12)
    assert isinstance(png_img, Image.Image)
    assert png_img.size[0] > 0
    assert png_img.size[1] > 0
    
    # 5. Clipboard (should not crash)
    res = to_clipboard(matrix)
    assert isinstance(res, bool)


# =====================================================================
# 5. Config Manager Tests
# =====================================================================

def test_config_manager_defaults():
    cm = ConfigManager()
    assert cm.config["font_size"] == 12
    assert cm.config["preset"] == "Balanced"
    assert "preprocessing" in cm.config

def test_config_manager_save_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        conf_path = os.path.join(tmpdir, "config.json")
        cm = ConfigManager()
        cm.config["font_size"] = 18
        cm.save(conf_path)
        
        assert os.path.exists(conf_path)
        
        cm2 = ConfigManager()
        cm2.load(conf_path)
        assert cm2.config["font_size"] == 18

def test_config_manager_fallback():
    cm = ConfigManager()
    # Trigger fallback check with a non-existent font
    with pytest.warns(RuntimeWarning) as record:
        resolved = cm.resolve_font_path("non_existent_font.ttf")
    
    # Should warning-fallback to bundled font
    assert len(record) > 0
    assert "not found" in str(record[0].message)
    assert os.path.exists(resolved)
    assert resolved.endswith("JetBrainsMono-Regular.ttf")


# =====================================================================
# 6. Conversion Engine Tests
# =====================================================================

def test_conversion_engine():
    cache = GlyphCache(TEST_FONT_PATH, 12, "shades")
    engine = ConversionEngine(cache, metric="MSE", preset="Balanced")
    
    # Test workload estimator
    est = engine.estimate_workload(img_width=100, img_height=100, cols=20)
    assert est["columns"] == 20
    assert est["rows"] > 0
    assert "complexity" in est
    
    # Test preprocessing filters
    test_img = np.random.randint(0, 256, (40, 40, 3), dtype=np.uint8)
    processed = engine.preprocess_image(
        test_img, brightness=1.2, contrast=0.9, sharpening=0.5, gaussian_blur=1.0
    )
    assert processed.ndim == 2  # Grayscale conversion
    assert processed.shape == (40, 40)
    
    # Test convert pipeline
    output_chars = engine.convert(test_img, cols=10)
    # Check that returned shape matches the target cols and calculated rows
    expected_rows, expected_cols = engine.get_output_dimensions(40, 40, 10)
    assert output_chars.shape == (expected_rows, expected_cols)
    assert output_chars.dtype == 'U1'


def test_conversion_engine_color_mode():
    cache = GlyphCache(TEST_FONT_PATH, 12, "shades")
    engine = ConversionEngine(cache, metric="MSE", preset="Balanced")
    
    # Test with solid color image (100, 150, 200)
    # 3 channels (RGB)
    h, w = 40, 40
    test_img = np.zeros((h, w, 3), dtype=np.uint8)
    test_img[:, :, 0] = 100
    test_img[:, :, 1] = 150
    test_img[:, :, 2] = 200
    
    # Run convert with color_mode=True
    char_matrix, color_matrix = engine.convert(test_img, cols=10, color_mode=True)
    
    # Verify shape
    expected_rows, expected_cols = engine.get_output_dimensions(w, h, 10)
    assert char_matrix.shape == (expected_rows, expected_cols)
    assert color_matrix.shape == (expected_rows, expected_cols, 3)
    
    # Verify values are quantized to multiples of 16
    assert np.all(color_matrix % 16 == 0)
    
    # Verify specific quantized values
    expected_color = np.array([96, 144, 192], dtype=np.uint8)
    assert np.all(color_matrix == expected_color)

    # Test with grayscale image frame (2D)
    test_gray = np.ones((h, w), dtype=np.uint8) * 128
    char_matrix_g, color_matrix_g = engine.convert(test_gray, cols=10, color_mode=True)
    assert color_matrix_g.shape == (expected_rows, expected_cols, 3)
    assert np.all(color_matrix_g == 128)


def test_config_manager_color_fields():
    cm = ConfigManager()
    # Check default values
    assert cm.config["color_mode"] is False
    assert cm.config["background_color"] == "Black"
    
    # Check saving and loading
    with tempfile.TemporaryDirectory() as tmpdir:
        conf_path = os.path.join(tmpdir, "config_color.json")
        cm.config["color_mode"] = True
        cm.config["background_color"] = "White"
        cm.save(conf_path)
        
        cm2 = ConfigManager()
        cm2.load(conf_path)
        assert cm2.config["color_mode"] is True
        assert cm2.config["background_color"] == "White"
        
    # Check validation fails if color_mode is invalid type
    bad_config = cm.get_default_config()
    bad_config["color_mode"] = "not a bool"
    assert cm.validate_config(bad_config) is False
    
    # Check validation fails if background_color is invalid type
    bad_config2 = cm.get_default_config()
    bad_config2["background_color"] = 123
    assert cm.validate_config(bad_config2) is False
    
    # Check validation fails if keys are missing
    bad_config3 = cm.get_default_config()
    del bad_config3["color_mode"]
    assert cm.validate_config(bad_config3) is False


def test_exporters_color_mode():
    char_matrix = np.array([
        ['A', 'A', 'B'],
        ['C', 'D', 'D']
    ], dtype='U1')
    
    color_matrix = np.zeros((2, 3, 3), dtype=np.uint8)
    color_matrix[0, 0] = [255, 0, 0]      # Red
    color_matrix[0, 1] = [255, 0, 0]      # Red
    color_matrix[0, 2] = [0, 255, 0]      # Green
    color_matrix[1, 0] = [0, 0, 255]      # Blue
    color_matrix[1, 1] = [255, 255, 255]  # White
    color_matrix[1, 2] = [255, 255, 255]  # White
    
    # 1. Plaintext (ANSI escape codes)
    txt_out = to_txt(char_matrix, color_matrix)
    expected_line_0 = "\033[38;2;255;0;0mAA\033[38;2;0;255;0mB\033[0m"
    expected_line_1 = "\033[38;2;0;0;255mC\033[38;2;255;255;255mDD\033[0m"
    assert txt_out == f"{expected_line_0}\n{expected_line_1}"
    
    # 2. HTML output
    html_black = to_html(char_matrix, "Courier", 14, color_matrix, bg_color="Black")
    assert "background-color: #000000" in html_black
    assert '<span style="color:rgb(255,0,0)">AA</span>' in html_black
    assert '<span style="color:rgb(0,255,0)">B</span>' in html_black
    assert '<span style="color:rgb(0,0,255)">C</span>' in html_black
    assert '<span style="color:rgb(255,255,255)">DD</span>' in html_black
    
    html_white = to_html(char_matrix, "Courier", 14, color_matrix, bg_color="White")
    assert "background-color: #ffffff" in html_white
    
    html_trans = to_html(char_matrix, "Courier", 14, color_matrix, bg_color="Transparent")
    assert "background-color: transparent" in html_trans

    # 3. SVG output
    svg_black = to_svg(char_matrix, "Courier", 14, char_aspect_ratio=0.6, color_matrix=color_matrix, bg_color="Black")
    assert 'fill="#000000"' in svg_black
    assert '<tspan fill="rgb(255,0,0)">AA</tspan>' in svg_black
    assert '<tspan fill="rgb(0,255,0)">B</tspan>' in svg_black
    
    svg_trans = to_svg(char_matrix, "Courier", 14, char_aspect_ratio=0.6, color_matrix=color_matrix, bg_color="Transparent")
    assert 'fill="none"' in svg_trans

    # 4. PNG output
    png_black = to_png(char_matrix, TEST_FONT_PATH, 14, color_matrix, bg_color="Black")
    assert png_black.mode == "RGB"
    
    png_trans = to_png(char_matrix, TEST_FONT_PATH, 14, color_matrix, bg_color="Transparent")
    assert png_trans.mode == "RGBA"
    
    # 5. Clipboard
    res = to_clipboard(char_matrix, color_matrix)
    assert isinstance(res, bool)
