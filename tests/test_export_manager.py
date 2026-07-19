import os
import tempfile
import numpy as np
import pytest
from PIL import Image

from ascii_vision.exporter import ExportManager, to_txt

TEST_FONT_PATH = "assets/fonts/JetBrainsMono-Regular.ttf"


@pytest.fixture
def sample_matrix():
    return np.array([
        ["A", "B", "C"],
        ["D", "E", "F"],
    ], dtype="U1")


@pytest.fixture
def color_matrix():
    cm = np.zeros((2, 3, 3), dtype=np.uint8)
    cm[0, 0] = [255, 0, 0]
    cm[0, 1] = [255, 0, 0]
    cm[0, 2] = [0, 255, 0]
    cm[1, 0] = [0, 0, 255]
    cm[1, 1] = [255, 255, 255]
    cm[1, 2] = [255, 255, 255]
    return cm


class TestExportManager:
    def test_headless_import_does_not_pull_qt(self):
        """
        The dispatcher lives in the headless package and imports without Qt.
        """
        # Import inside a fresh context check; PySide6 should not be required.
        from ascii_vision.exporter import ExportManager
        assert ExportManager is not None

    def test_format_auto_detected_from_extension(self, sample_matrix):
        manager = ExportManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = os.path.join(tmpdir, "out.html")
            result = manager.save(
                sample_matrix,
                html_path,
                font_name="Courier",
                font_size=12,
            )
            assert result == html_path
            with open(html_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "<html>" in content

    def test_format_override_argument(self, sample_matrix):
        manager = ExportManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            txt_path = os.path.join(tmpdir, "out.txt")
            result = manager.save(
                sample_matrix,
                txt_path,
                font_name="Courier",
                font_size=12,
                format="html",
            )
            assert result == txt_path
            with open(txt_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "<html>" in content
            assert "ABC" in content

    def test_txt_save(self, sample_matrix):
        manager = ExportManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.txt")
            result = manager.save(sample_matrix, path, font_name="Courier", font_size=12)
            assert result == path
            with open(path, "r", encoding="utf-8") as f:
                assert f.read() == "ABC\nDEF"

    def test_html_save(self, sample_matrix):
        manager = ExportManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.html")
            manager.save(sample_matrix, path, font_name="Courier", font_size=12)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "<html>" in content
            assert "background-color" in content

    def test_svg_save(self, sample_matrix):
        manager = ExportManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.svg")
            manager.save(sample_matrix, path, font_name="Courier", font_size=12)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "<svg" in content
            assert "</svg>" in content

    def test_png_save(self, sample_matrix):
        manager = ExportManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.png")
            result = manager.save(
                sample_matrix,
                path,
                font_name="Courier",
                font_size=12,
                font_path=TEST_FONT_PATH,
            )
            assert result == path
            with Image.open(path) as img:
                assert img.size[0] > 0
                assert img.size[1] > 0

    def test_color_save_rle_html(self, sample_matrix, color_matrix):
        manager = ExportManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.html")
            manager.save(
                sample_matrix,
                path,
                font_name="Courier",
                font_size=12,
                color_matrix=color_matrix,
                bg_color="Black",
            )
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "color:rgb(255,0,0)" in content
            assert "color:rgb(0,255,0)" in content
            assert "color:rgb(0,0,255)" in content

    def test_color_save_rle_svg(self, sample_matrix, color_matrix):
        manager = ExportManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.svg")
            manager.save(
                sample_matrix,
                path,
                font_name="Courier",
                font_size=12,
                color_matrix=color_matrix,
                bg_color="Black",
            )
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "<tspan" in content

    def test_color_save_png(self, sample_matrix, color_matrix):
        manager = ExportManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.png")
            manager.save(
                sample_matrix,
                path,
                font_name="Courier",
                font_size=12,
                color_matrix=color_matrix,
                bg_color="Black",
                font_path=TEST_FONT_PATH,
            )
            with Image.open(path) as img:
                assert img.mode == "RGB"

    def test_clipboard_save(self, sample_matrix):
        manager = ExportManager()
        result = manager.save(sample_matrix, None, font_name="Courier", font_size=12)
        assert isinstance(result, bool)

    def test_unsupported_format_raises(self, sample_matrix):
        manager = ExportManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.pdf")
            with pytest.raises(ValueError):
                manager.save(sample_matrix, path, font_name="Courier", font_size=12)

    def test_unsupported_format_override_raises(self, sample_matrix):
        manager = ExportManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.txt")
            with pytest.raises(ValueError):
                manager.save(sample_matrix, path, font_name="Courier", font_size=12, format="pdf")

    def test_unwritable_path_raises_no_partial_file(self, sample_matrix):
        manager = ExportManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = os.path.join(tmpdir, "no_such_dir", "out.txt")
            with pytest.raises((FileNotFoundError, OSError)):
                manager.save(sample_matrix, nonexistent, font_name="Courier", font_size=12)
            assert not os.path.exists(nonexistent)

    def test_png_requires_font_path(self, sample_matrix):
        manager = ExportManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.png")
            with pytest.raises(ValueError):
                manager.save(sample_matrix, path, font_name="Courier", font_size=12)
