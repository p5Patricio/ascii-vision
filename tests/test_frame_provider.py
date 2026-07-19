import os
import tempfile

import cv2
import numpy as np
import pytest
from PIL import Image

from ascii_vision.frame_provider import (
    FrameProvider,
    StaticImageFrameProvider,
    VideoFrameProvider,
    WebcamFrameProvider,
)


def _write_synthetic_video(path: str, size: tuple[int, int] = (8, 8), frames: int = 3) -> None:
    """Writes a small synthetic MP4 using OpenCV."""
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 10, size)
    for i in range(frames):
        frame = np.full((*size, 3), (i + 1) * 70, dtype=np.uint8)
        writer.write(frame)
    writer.release()


class TestStaticImageFrameProvider:
    def test_static_image_total_frames(self):
        img = Image.new("RGB", (10, 10), color="blue")
        provider = StaticImageFrameProvider(img)
        assert provider.total_frames == 1

    def test_static_image_yields_one_rgb_frame(self):
        img = Image.new("RGB", (10, 10), color="green")
        provider = StaticImageFrameProvider(img)
        frames = list(provider.get_frames())
        assert len(frames) == 1
        assert frames[0].shape == (10, 10, 3)


class TestVideoFrameProvider:
    def test_video_provider_yields_frames(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.mp4")
            _write_synthetic_video(path)

            provider = VideoFrameProvider(path)
            assert provider.total_frames == 3
            frames = list(provider.get_frames())
            assert len(frames) == 3
            for frame in frames:
                assert frame.shape == (8, 8, 3)

    def test_video_provider_releases_capture_on_cleanup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.mp4")
            _write_synthetic_video(path)

            provider = VideoFrameProvider(path)
            assert provider._cap is not None
            provider.cleanup()
            assert provider._cap is None

    def test_video_provider_releases_on_generator_close(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.mp4")
            _write_synthetic_video(path)

            provider = VideoFrameProvider(path)
            gen = provider.get_frames()
            next(gen)
            gen.close()
            assert provider._cap is None

    def test_video_provider_invalid_source_raises(self):
        with pytest.raises((IOError, OSError)):
            VideoFrameProvider("/definitely/not/a/file.mp4")

    def test_video_provider_context_manager(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.mp4")
            _write_synthetic_video(path)

            with VideoFrameProvider(path) as provider:
                frames = list(provider.get_frames())
                assert len(frames) == 3
            assert provider._cap is None

    def test_video_provider_av_backend(self):
        pytest.importorskip("av")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.mp4")
            _write_synthetic_video(path)

            provider = VideoFrameProvider(path, backend="av")
            assert provider._backend == "av"
            frames = list(provider.get_frames())
            assert len(frames) == 3
            provider.cleanup()
            assert provider._container is None


class TestWebcamFrameProvider:
    def test_webcam_no_camera_raises(self):
        with pytest.raises((IOError, OSError)):
            WebcamFrameProvider(9999)

    def test_webcam_total_frames_is_zero(self):
        # Only test the property without opening a real device.
        provider = WebcamFrameProvider.__new__(WebcamFrameProvider)
        provider._cap = None
        provider._stopped = False
        assert provider.total_frames == 0

    def test_webcam_stop_releases_capture(self):
        # Mock a capture so the provider can be instantiated without hardware.
        provider = WebcamFrameProvider.__new__(WebcamFrameProvider)
        provider._device_index = 0
        provider._stopped = False
        provider._cap = None
        provider.stop()
        assert provider._stopped is True

    def test_webcam_yields_rgb_frames_with_mocked_capture(self, monkeypatch):
        """Mock cv2.VideoCapture to return synthetic frames and verify RGB output."""
        from unittest.mock import Mock

        synthetic_bgr = np.full((4, 4, 3), (0, 255, 0), dtype=np.uint8)
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.side_effect = [
            (True, synthetic_bgr.copy()),
            (True, synthetic_bgr.copy()),
            (False, None),
        ]

        monkeypatch.setattr(cv2, "VideoCapture", lambda idx: mock_cap)

        provider = WebcamFrameProvider(0)
        frames = list(provider.get_frames())

        assert len(frames) == 2
        expected_rgb = cv2.cvtColor(synthetic_bgr, cv2.COLOR_BGR2RGB)
        for frame in frames:
            assert isinstance(frame, np.ndarray)
            assert frame.shape == (4, 4, 3)
            np.testing.assert_array_equal(frame, expected_rgb)
        mock_cap.release.assert_called()

    def test_webcam_stop_stops_iteration_and_cleanup_releases_capture(self, monkeypatch):
        """stop() halts iteration and cleanup() releases the capture."""
        from unittest.mock import Mock

        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.full((4, 4, 3), 255, dtype=np.uint8))

        monkeypatch.setattr(cv2, "VideoCapture", lambda idx: mock_cap)

        provider = WebcamFrameProvider(0)
        gen = provider.get_frames()
        frame = next(gen)
        assert frame is not None

        provider.stop()

        assert provider._stopped is True
        assert provider._cap is None
        mock_cap.release.assert_called()
        with pytest.raises(StopIteration):
            next(gen)


class TestFrameProviderBase:
    def test_base_methods_raise(self):
        provider = FrameProvider()
        with pytest.raises(NotImplementedError):
            list(provider.get_frames())
        with pytest.raises(NotImplementedError):
            _ = provider.total_frames

    def test_context_manager_calls_cleanup(self):
        provider = StaticImageFrameProvider(Image.new("RGB", (5, 5), color="white"))
        with provider as ctx:
            assert ctx is provider
        assert provider._frame is None
