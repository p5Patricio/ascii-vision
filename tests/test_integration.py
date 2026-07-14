import os
import tempfile
import numpy as np
import pytest
from PIL import Image

from ascii_vision.frame_provider import StaticImageFrameProvider
from ascii_vision.glyph_cache import GlyphCache
from ascii_vision.engine import ConversionEngine
from ascii_vision.config import ConfigManager
from ascii_vision.exporter import to_txt, to_html, to_svg, to_png, to_clipboard

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
        
        # 2. Check Configuration Management
        config_data = {
            "font_path": TEST_FONT_PATH,
            "font_size": 10,
            "charset": "shades",
            "preset": "Custom",
            "metric": "MSE",
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
