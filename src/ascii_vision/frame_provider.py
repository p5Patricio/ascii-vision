import glob as _glob
import os
from typing import Generator, Union
import cv2
import numpy as np
from PIL import Image


# Maximum media file size: 500 MB
_MAX_MEDIA_SIZE = 500 * 1024 * 1024

# Known magic byte prefixes for image and video formats
_IMAGE_VIDEO_MAGIC_PREFIXES = [
    b"\x89PNG\r\n\x1a\n",     # PNG
    b"\xff\xd8",               # JPEG
    b"GIF8",                   # GIF
    b"BM",                     # BMP
    b"\x49\x49\x2a\x00",      # TIFF (little-endian)
    b"\x4d\x4d\x00\x2a",      # TIFF (big-endian)
    b"\x1a\x45\xdf\xa3",       # Matroska / WebM
    b"OggS",                   # OGG / OGV
]


def validate_media_file(path: str, max_size: int = _MAX_MEDIA_SIZE) -> None:
    """
    Validates that *path* points to a real, non-malicious media file.

    Checks:
    - File exists (raises ``FileNotFoundError``).
    - File size is under *max_size* (raises ``ValueError``).
    - File starts with known image / video magic bytes (raises ``ValueError``).

    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If the file is too large or does not appear to be a valid
            image or video file.
    """
    path_str = str(path)
    if not os.path.exists(path_str):
        raise FileNotFoundError(f"Media file not found: {path_str}")

    file_size = os.path.getsize(path_str)
    if file_size > max_size:
        raise ValueError(
            f"Media file too large: {file_size} bytes "
            f"(max {max_size} bytes): {path_str}"
        )

    _validate_magic_bytes(path_str)


def _validate_magic_bytes(path: str) -> None:
    """Check the first 16 bytes of *path* against known media magic numbers."""
    with open(path, "rb") as f:
        header = f.read(16)

    if len(header) < 2:
        raise ValueError(f"File is too small to be a valid media file: {path}")

    # 1. Check fixed magic prefixes
    for magic in _IMAGE_VIDEO_MAGIC_PREFIXES:
        if header.startswith(magic):
            return

    # 2. ISO Base Media (MP4 / M4V / MOV / 3GP): <4-byte-big-endian-size>ftyp…
    if len(header) >= 8 and header[4:8] == b"ftyp":
        return

    # 3. RIFF-based containers (AVI, WEBP): RIFF + 4-byte size + FOURCC
    if header.startswith(b"RIFF") and len(header) >= 12:
        if header[8:12] in (b"WEBP", b"AVI "):
            return

    raise ValueError(
        f"File does not appear to be a valid image or video file: {path}"
    )


class FrameProvider:
    """
    Abstract base class for retrieving frames iteratively.
    """
    def get_frames(self) -> Generator[np.ndarray, None, None]:
        """
        Yields frames sequentially.
        """
        raise NotImplementedError("Subclasses must implement get_frames()")

    @property
    def total_frames(self) -> int:
        """
        Returns the total number of frames.
        """
        raise NotImplementedError("Subclasses must implement total_frames")

    def cleanup(self) -> None:
        """
        Releases any native capture resources held by the provider.
        Safe to call multiple times; subclasses may override.
        """
        pass

    def stop(self) -> None:
        """
        Signals a live provider to stop yielding frames and release resources.
        Safe to call multiple times; subclasses may override.
        """
        pass

    def __enter__(self):
        """
        Context manager entry. Returns the provider instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit. Ensures cleanup() is called.
        """
        self.cleanup()
        return False


class StaticImageFrameProvider(FrameProvider):
    """
    FrameProvider implementation for loading a single static image using Pillow.
    Yields exactly one frame and terminates.
    """
    def __init__(self, image_source: Union[str, Image.Image]):
        """
        Initializes the provider with a file path or a PIL Image instance.
        """
        if not isinstance(image_source, (str, Image.Image)):
            raise TypeError("image_source must be a file path (str) or PIL.Image.Image instance")
        # Validate file-based sources upfront before delegating to PIL
        if isinstance(image_source, str):
            validate_media_file(image_source)
        self.image_source = image_source
        self._frame = None

    def _load_frame(self) -> np.ndarray:
        if self._frame is not None:
            return self._frame

        if isinstance(self.image_source, str):
            if not os.path.exists(self.image_source):
                raise FileNotFoundError(f"Image path not found: {self.image_source}")
            with Image.open(self.image_source) as img:
                # Convert to RGB to ensure a consistent 3D NumPy array shape
                img_rgb = img.convert("RGB")
                self._frame = np.array(img_rgb)
        elif isinstance(self.image_source, Image.Image):
            img_rgb = self.image_source.convert("RGB")
            self._frame = np.array(img_rgb)
        else:
            raise TypeError("image_source must be a file path (str) or PIL.Image.Image instance")

        return self._frame

    def get_frames(self) -> Generator[np.ndarray, None, None]:
        """
        Yields exactly 1 frame of the loaded image and terminates.
        """
        yield self._load_frame()

    @property
    def total_frames(self) -> int:
        """
        Returns 1 for a static image.
        """
        return 1

    def cleanup(self) -> None:
        """
        Static image provider has no native resources to release.
        """
        self._frame = None


class VideoFrameProvider(FrameProvider):
    """
    FrameProvider implementation that yields frames from a video file.

    Uses PyAV (``av``) when it is installed and the caller requests it,
    otherwise falls back to ``cv2.VideoCapture``. The fallback keeps the
    core package usable without FFmpeg/PyAV native libraries.
    """
    def __init__(self, source: Union[str, os.PathLike], backend: str = "auto"):
        """
        Initializes the provider with a video file path.

        Parameters:
            source: Path to the video file.
            backend: Decoding backend to use. ``"auto"`` prefers PyAV when
                available, otherwise ``cv2.VideoCapture``. ``"av"`` forces
                PyAV and raises if it is not installed.
        """
        self._source = source
        validate_media_file(source)
        self._cap = None
        self._container = None
        self._stream = None
        self._backend = self._init_backend(backend)

    def _init_backend(self, backend: str) -> str:
        """
        Resolves and initializes the requested decoding backend.
        """
        if backend == "av":
            try:
                import av  # noqa: F401
            except Exception as exc:
                raise RuntimeError(
                    "PyAV backend requested but 'av' is not installed. "
                    "Install the optional [video] extra to use it."
                ) from exc
            self._init_av()
            return "av"

        if backend == "auto":
            try:
                import av  # noqa: F401
                self._init_av()
                return "av"
            except Exception:
                pass

        self._init_cv2()
        return "cv2"

    def _init_cv2(self) -> None:
        """
        Opens the video source with OpenCV's VideoCapture.
        """
        self._cap = cv2.VideoCapture(str(self._source))
        if not self._cap.isOpened():
            self._cap = None
            raise IOError(f"Could not open video source with OpenCV: {self._source}")

    def _init_av(self) -> None:
        """
        Opens the video source with PyAV.
        """
        import av
        try:
            self._container = av.open(str(self._source))
        except Exception as exc:
            self._container = None
            raise IOError(f"Could not open video source with PyAV: {self._source}") from exc

        video_streams = [s for s in self._container.streams if s.type == "video"]
        if not video_streams:
            self._container.close()
            self._container = None
            raise IOError(f"No video stream found in {self._source}")
        self._stream = video_streams[0]

    @property
    def total_frames(self) -> int:
        """
        Returns the reported frame count, or 0 when it cannot be determined.
        """
        if self._backend == "cv2" and self._cap is not None:
            count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
            return max(0, count)
        if self._backend == "av" and self._stream is not None:
            frames = getattr(self._stream, "frames", 0)
            return max(0, int(frames)) if frames is not None else 0
        return 0

    def get_frames(self) -> Generator[np.ndarray, None, None]:
        """
        Yields every video frame as an RGB NumPy array.
        """
        try:
            if self._backend == "av":
                yield from self._get_frames_av()
            else:
                yield from self._get_frames_cv2()
        finally:
            self.cleanup()

    def _get_frames_cv2(self) -> Generator[np.ndarray, None, None]:
        while self._cap is not None:
            ret, frame = self._cap.read()
            if not ret:
                break
            yield cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def _get_frames_av(self) -> Generator[np.ndarray, None, None]:
        for packet in self._container.demux(self._stream):
            for frame in packet.decode():
                yield frame.to_ndarray(format="rgb24")

    def stop(self) -> None:
        """
        Stops decoding and releases native resources.
        """
        self.cleanup()

    def cleanup(self) -> None:
        """
        Releases the native video capture or PyAV container.
        """
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        if self._container is not None:
            self._container.close()
            self._container = None
        self._stream = None


class WebcamFrameProvider(FrameProvider):
    """
    FrameProvider implementation that yields live frames from a camera device.

    Supports optional frame skipping via *skip_interval* and a *target_fps* hint
    for adaptive quality consumers downstream.
    """
    def __init__(self, device_index: int = 0, *, skip_interval: int = 0, target_fps: Optional[int] = None):
        """
        Initializes the provider with a camera device index.

        Parameters:
            device_index: Index of the camera device to open.
            skip_interval: When > 0, yield only every Nth frame (e.g. 2 = every
                other frame). 0 means yield every frame.
            target_fps: Hint for adaptive quality consumers. Does not affect the
                provider's capture behaviour directly.

        Raises:
            IOError: If the camera device cannot be opened.
        """
        self._device_index = device_index
        self.skip_interval = skip_interval
        self.target_fps = target_fps
        self._cap = cv2.VideoCapture(device_index)
        self._stopped = False
        if not self._cap.isOpened():
            self._cap = None
            raise IOError(f"Could not open camera device {device_index}")

    @property
    def total_frames(self) -> int:
        """
        Live sources have no fixed frame count.
        """
        return 0

    def get_frames(self) -> Generator[np.ndarray, None, None]:
        """
        Yields live camera frames as RGB NumPy arrays until stopped.

        When *skip_interval* > 0, only every Nth frame is yielded
        (frame indices 0, N, 2N, …).
        """
        try:
            frame_idx = 0
            while not self._stopped and self._cap is not None:
                ret, frame = self._cap.read()
                if not ret or self._stopped:
                    break
                if self.skip_interval > 0 and frame_idx % self.skip_interval != 0:
                    frame_idx += 1
                    continue
                frame_idx += 1
                yield cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        finally:
            self.cleanup()

    def stop(self) -> None:
        """
        Signals the provider to stop capturing and releases the camera.
        """
        self._stopped = True
        self.cleanup()

    def cleanup(self) -> None:
        """
        Releases the native camera capture.
        """
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class BatchFrameProvider:
    """
    Expands glob patterns into sorted file lists for batch processing.

    Provides a convenient interface for discovering input files matching
    a glob pattern, with optional recursive directory traversal.
    """

    def __init__(self, pattern: str, recursive: bool = False):
        """
        Initializes the provider with a glob pattern.

        Args:
            pattern: Glob pattern to match files against.
            recursive: If True, enables ``**`` recursive matching
                       via ``glob.glob(..., recursive=True)``.
        """
        self.pattern = pattern
        self.recursive = recursive

    def get_files(self) -> list[str]:
        """
        Returns a sorted list of file paths matching the glob pattern.
        """
        return sorted(_glob.glob(self.pattern, recursive=self.recursive))
