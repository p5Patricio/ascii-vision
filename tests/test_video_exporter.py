import builtins
import os
import sys
import tempfile
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest
from PIL import Image

from ascii_vision.video_exporter import VideoExporter


def _build_frames(count: int = 3, size: tuple[int, int] = (16, 12)) -> list[np.ndarray]:
    """Returns a list of synthetic RGB frames."""
    frames = []
    for i in range(count):
        frame = np.full((*size, 3), (i + 1) * 60, dtype=np.uint8)
        frames.append(frame)
    return frames


class TestVideoExporter:
    def test_video_exporter_writes_mp4(self):
        exporter = VideoExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "out.mp4")
            frames = _build_frames(count=3)
            exporter.write(frames, output, fps=10)

            assert os.path.exists(output)
            assert os.path.getsize(output) > 0

            cap = cv2.VideoCapture(output)
            assert cap.isOpened()
            assert cap.get(cv2.CAP_PROP_FRAME_COUNT) == 3
            cap.release()

    def test_video_exporter_writes_gif(self):
        exporter = VideoExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "out.gif")
            frames = _build_frames(count=2, size=(10, 10))
            exporter.write(frames, output, fps=5)

            assert os.path.exists(output)
            with Image.open(output) as img:
                assert getattr(img, "n_frames", 1) >= 1

    def test_video_exporter_empty_frames_raises(self):
        exporter = VideoExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "out.mp4")
            with pytest.raises(ValueError):
                exporter.write([], output)

    def test_video_exporter_unsupported_format_raises(self):
        exporter = VideoExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "out.avi")
            with pytest.raises(ValueError):
                exporter.write(_build_frames(count=1), output)

    def test_video_exporter_missing_output_directory_raises(self):
        exporter = VideoExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "missing", "out.mp4")
            with pytest.raises(FileNotFoundError):
                exporter.write(_build_frames(count=1), output)

    def test_video_exporter_resizes_mismatched_frames(self):
        exporter = VideoExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "out.mp4")
            frames = [
                np.full((12, 16, 3), 100, dtype=np.uint8),
                np.full((24, 32, 3), 200, dtype=np.uint8),
            ]
            exporter.write(frames, output, fps=10, dimensions=(16, 12))
            assert os.path.exists(output)
            assert os.path.getsize(output) > 0

    def test_video_exporter_grayscale_frames(self):
        exporter = VideoExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "out.mp4")
            frames = [np.full((10, 10), 128, dtype=np.uint8) for _ in range(2)]
            exporter.write(frames, output, fps=10)
            assert os.path.exists(output)
            assert os.path.getsize(output) > 0

    # ------------------------------------------------------------------
    # Audio passthrough tests (PR E)
    # ------------------------------------------------------------------

    def test_audio_fallback_warning_when_av_missing(self, monkeypatch, caplog):
        """
        When PyAV is not importable and source_audio is given, a warning is
        logged and the video is written without audio (cv2 fallback).
        """
        import logging
        caplog.set_level(logging.WARNING)
        # Ensure av is not cached in sys.modules
        monkeypatch.delitem(sys.modules, "av", raising=False)

        real_import = builtins.__import__

        def fail_av_import(name, *args, **kwargs):
            if name == "av":
                raise ImportError("Mock: av not available")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fail_av_import)

        exporter = VideoExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "out.mp4")
            frames = _build_frames(count=3)
            exporter.write(frames, output, fps=10, source_audio="dummy.mp4")

            assert os.path.exists(output)
            assert os.path.getsize(output) > 0
            assert "PyAV not available" in caplog.text

    def test_audio_passthrough_calls_av_method(self, monkeypatch):
        """
        When PyAV is available and source_audio is provided,
        _write_mp4_with_av is invoked instead of the cv2 path.
        """
        monkeypatch.setitem(sys.modules, "av", MagicMock())

        exporter = VideoExporter()
        mock_av_method = MagicMock()
        monkeypatch.setattr(exporter, "_write_mp4_with_av", mock_av_method)

        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "out.mp4")
            frames = _build_frames(count=1)
            exporter.write(frames, output, fps=10, source_audio="dummy.mp4")
            mock_av_method.assert_called_once()

    def test_audio_passthrough_no_source_uses_cv2_path(self, monkeypatch):
        """
        When source_audio is None, the original cv2 path is used even if
        PyAV is available.
        """
        monkeypatch.setitem(sys.modules, "av", MagicMock())

        exporter = VideoExporter()
        mock_av_method = MagicMock()
        monkeypatch.setattr(exporter, "_write_mp4_with_av", mock_av_method)

        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "out.mp4")
            frames = _build_frames(count=1)
            # No source_audio → should skip av path
            exporter.write(frames, output, fps=10)
            mock_av_method.assert_not_called()
