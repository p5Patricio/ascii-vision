import os
import tempfile
import numpy as np
import pytest
from PIL import Image

import subprocess
import sys

from ascii_vision.frame_provider import StaticImageFrameProvider
from ascii_vision.glyph_cache import GlyphCache
from ascii_vision.engine import ConversionEngine
from ascii_vision.config import ConfigManager
from ascii_vision.exporter import to_txt, to_html, to_svg, to_png, to_clipboard, ExportManager
from ascii_vision.cli import main as cli_main

TEST_FONT_PATH = "assets/fonts/JetBrainsMono-Regular.ttf"

def test_full_pipeline_integration():
    """
    Verifies the integration between ConfigManager, FrameProvider, 
    ConversionEngine, and Exporters.
    """
    # 1. Setup a test image
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "integration_test.png")
        img = Image.new("RGB", (60, 40), color=(100, 150, 200))
        img.save(img_path)
        
        config_data = {
            "font_path": TEST_FONT_PATH,
            "font_size": 10,
            "charset": "shades",
            "preset": "Custom",
            "metric": "MSE",
            "color_mode": False,
            "background_color": "Black",
            "preprocessing": {
                "brightness": 1.1,
                "contrast": 0.95,
                "sharpening": 0.2,
                "gaussian_blur": 0.5
            }
        }
        
        cm = ConfigManager()
        cm.set_config(config_data)
        assert cm.config["font_size"] == 10
        assert cm.config["preprocessing"]["brightness"] == 1.1
        
        # 3. Load frame via FrameProvider
        provider = StaticImageFrameProvider(img_path)
        assert provider.total_frames == 1
        frames = list(provider.get_frames())
        assert len(frames) == 1
        frame = frames[0]
        assert frame.shape == (40, 60, 3)
        
        # 4. Glyph Cache rendering
        cache = GlyphCache(
            font_path=cm.config["font_path"],
            font_size=cm.config["font_size"],
            charset=cm.config["charset"]
        )
        cache.render(target_size=(10, 10), as_float=True)
        assert cache.cache.shape[1:] == (10, 10)
        
        # 5. Conversion with various metrics
        for metric in ["MSE", "SSIM", "Brightness"]:
            engine = ConversionEngine(
                cache, 
                metric=metric, 
                preset="Custom", 
                preprocessing=cm.config["preprocessing"]
            )
            
            # Estimate workload
            est = engine.estimate_workload(60, 40, cols=12)
            assert est["columns"] == 12
            assert est["rows"] > 0
            
            # Execute conversion
            char_matrix = engine.convert(frame, cols=12)
            
            # Verify dimensions match
            rows, cols = engine.get_output_dimensions(60, 40, 12)
            assert char_matrix.shape == (rows, cols)
            assert char_matrix.dtype == 'U1'
            
            # 6. Export formats verification
            txt_out = to_txt(char_matrix)
            assert len(txt_out) > 0
            assert txt_out.count("\n") == rows - 1
            
            html_out = to_html(char_matrix, font_name="Courier", font_size=12)
            assert "Courier" in html_out
            assert "12px" in html_out
            
            svg_out = to_svg(char_matrix, font_name="Courier", font_size=12)
            assert "<svg" in svg_out
            assert "</svg>" in svg_out
            
            png_out = to_png(char_matrix, TEST_FONT_PATH, font_size=12)
            assert isinstance(png_out, Image.Image)
            assert png_out.size[0] > 0
            
            clipboard_res = to_clipboard(char_matrix)
            assert isinstance(clipboard_res, bool)


def test_color_pipeline_integration():
    """
    Verifies the integration when color_mode is active.
    """
    # Setup a test image
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "color_integration_test.png")
        img = Image.new("RGB", (60, 40), color=(100, 150, 200))
        img.save(img_path)
        
        config_data = {
            "font_path": TEST_FONT_PATH,
            "font_size": 10,
            "charset": "shades",
            "preset": "Custom",
            "metric": "MSE",
            "color_mode": True,
            "background_color": "White",
            "preprocessing": {
                "brightness": 1.0,
                "contrast": 1.0,
                "sharpening": 0.0,
                "gaussian_blur": 0.0
            }
        }
        
        cm = ConfigManager()
        cm.set_config(config_data)
        assert cm.config["color_mode"] is True
        assert cm.config["background_color"] == "White"
        
        provider = StaticImageFrameProvider(img_path)
        frames = list(provider.get_frames())
        frame = frames[0]
        
        cache = GlyphCache(
            font_path=cm.config["font_path"],
            font_size=cm.config["font_size"],
            charset=cm.config["charset"]
        )
        cache.render(target_size=(10, 10), as_float=True)
        
        engine = ConversionEngine(
            cache, 
            metric="MSE", 
            preset="Custom", 
            preprocessing=cm.config["preprocessing"]
        )
        
        # Execute conversion in color mode
        char_matrix, color_matrix = engine.convert(frame, cols=12, color_mode=True)
        
        rows, cols = engine.get_output_dimensions(60, 40, 12)
        assert char_matrix.shape == (rows, cols)
        assert color_matrix.shape == (rows, cols, 3)
        assert color_matrix.dtype == np.uint8
        
        # Test exports with color matrix
        txt_out = to_txt(char_matrix, color_matrix)
        assert "\033[38;2;" in txt_out  # ANSI escape code verification
        
        html_out = to_html(char_matrix, font_name="Courier", font_size=12, color_matrix=color_matrix, bg_color="White")
        assert "color:rgb" in html_out
        assert "#ffffff" in html_out  # white bg color CSS
        
        svg_out = to_svg(char_matrix, font_name="Courier", font_size=12, color_matrix=color_matrix, bg_color="White")
        assert "fill=\"rgb" in svg_out
        
        png_out = to_png(char_matrix, TEST_FONT_PATH, font_size=12, color_matrix=color_matrix, bg_color="White")
        assert isinstance(png_out, Image.Image)
        
        clipboard_res = to_clipboard(char_matrix, color_matrix)
        assert isinstance(clipboard_res, bool)


def test_cli_image_roundtrip():
    """Run the CLI on a synthetic image and verify the output file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "input.png")
        out_path = os.path.join(tmpdir, "output.html")
        img = Image.new("RGB", (80, 60), color=(120, 80, 160))
        img.save(img_path)

        exit_code = cli_main(["--input", img_path, "--output", out_path, "--columns", "20"])
        assert exit_code == 0
        assert os.path.exists(out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "<html>" in content or "<!DOCTYPE html>" in content


def test_cli_video_roundtrip():
    """Run the CLI on a synthetic video and verify the output MP4."""
    import cv2
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "input.mp4")
        out_path = os.path.join(tmpdir, "output.mp4")

        writer = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*"mp4v"), 5, (40, 30))
        for _ in range(5):
            frame = np.full((30, 40, 3), 128, dtype=np.uint8)
            writer.write(frame)
        writer.release()

        exit_code = cli_main([
            "--input", video_path,
            "--output", out_path,
            "--columns", "10",
            "--fps", "5",
            "--preset", "Fast",
        ])
        assert exit_code == 0
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 0


def test_export_manager_save_roundtrip():
    """Save a conversion result through ExportManager and read it back."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "em_test.png")
        out_txt = os.path.join(tmpdir, "out.txt")
        out_html = os.path.join(tmpdir, "out.html")
        img = Image.new("RGB", (60, 40), color=(200, 100, 50))
        img.save(img_path)

        provider = StaticImageFrameProvider(img_path)
        frame = next(provider.get_frames())
        cache = GlyphCache(TEST_FONT_PATH, 10, "ascii")
        engine = ConversionEngine(cache, metric="Brightness", preset="Fast")
        char_matrix = engine.convert(frame, cols=12)

        manager = ExportManager()
        assert manager.save(char_matrix, out_txt, font_name="Courier", font_size=12) == out_txt
        with open(out_txt, "r", encoding="utf-8") as f:
            assert len(f.read()) > 0

        html_path = manager.save(char_matrix, out_html, font_name="Courier", font_size=12)
        assert html_path == out_html
        with open(out_html, "r", encoding="utf-8") as f:
            assert "<html>" in f.read() or "<!DOCTYPE html>" in f.read()
