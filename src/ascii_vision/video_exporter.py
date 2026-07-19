import logging
import os
from typing import Iterable, Optional
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class VideoExporter:
    """
    Encodes a sequence of rendered ASCII frames into a playable video file.

    MP4 output is produced through ``cv2.VideoWriter``. GIF output uses Pillow
    because OpenCV's GIF writer is not reliably available across builds; this
    keeps the behavior consistent while still honoring the requested format.
    """

    SUPPORTED_FORMATS = {"mp4", "gif"}
    DEFAULT_FPS = 30

    def _resolve_codec(self, ext: str, codec: Optional[str]) -> Optional[int]:
        """
        Returns the OpenCV fourcc code for MP4, or None for GIF.
        """
        if ext != "mp4":
            return None
        if codec is None:
            codec = "mp4v"
        if isinstance(codec, str):
            if len(codec) != 4:
                raise ValueError(f"Codec must be a four-character code, got '{codec}'")
            return cv2.VideoWriter_fourcc(*codec)
        return codec

    def write(
        self,
        frames: Iterable[np.ndarray],
        output_path: str,
        fps: int = DEFAULT_FPS,
        dimensions: Optional[tuple[int, int]] = None,
        codec: Optional[str] = None,
        source_audio: Optional[str] = None,
    ) -> None:
        """
        Writes a sequence of frames to a video file.

        Parameters:
            frames: Iterable of RGB or grayscale NumPy arrays.
            output_path: Destination file path. Supported extensions: .mp4, .gif.
            fps: Frames per second for the output video.
            dimensions: Optional (width, height) for the output. If omitted,
                the dimensions of the first frame are used.
            codec: Optional four-character OpenCV codec code for MP4 output.
            source_audio: Optional path to source video with audio track.
                When PyAV is available, audio is re-muxed without re-encoding.
                Falls back to video-only with a warning if PyAV is not installed.

        Raises:
            ValueError: If the format is unsupported or the frame sequence is empty.
            RuntimeError: If the video writer cannot be initialized.
        """
        ext = os.path.splitext(output_path)[1].lower().lstrip(".")
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported video format '.{ext}'. "
                f"Supported: {', '.join(sorted(self.SUPPORTED_FORMATS))}"
            )

        frames_iter = iter(frames)
        try:
            first_frame = next(frames_iter)
        except StopIteration:
            raise ValueError("Cannot write video from empty frame sequence") from None

        if dimensions is None:
            height, width = first_frame.shape[:2]
            dimensions = (width, height)

        parent_dir = os.path.dirname(os.path.abspath(output_path))
        if parent_dir and not os.path.exists(parent_dir):
            raise FileNotFoundError(f"Output directory does not exist: {parent_dir}")

        if ext == "mp4":
            self._write_mp4(first_frame, frames_iter, output_path, fps, dimensions, codec, source_audio)
        else:
            self._write_gif(first_frame, frames_iter, output_path, fps)

    def _frame_iter(
        self, first_frame: np.ndarray, frames_iter: Iterable[np.ndarray]
    ) -> Iterable[np.ndarray]:
        """
        Yields the first frame followed by the rest of the iterator.
        """
        yield first_frame
        yield from frames_iter

    def _write_mp4(
        self,
        first_frame: np.ndarray,
        frames_iter: Iterable[np.ndarray],
        output_path: str,
        fps: int,
        dimensions: tuple[int, int],
        codec: Optional[str],
        source_audio: Optional[str] = None,
    ) -> None:
        # When source audio is provided, use the PyAV pipeline for audio passthrough
        if source_audio is not None:
            try:
                import av  # type: ignore[import-untyped]  # noqa: F811
                self._write_mp4_with_av(
                    first_frame, frames_iter, output_path, fps, dimensions, codec, source_audio,
                )
                return
            except ImportError:
                logger.warning(
                    "PyAV not available; audio passthrough disabled. "
                    "Install the 'av' library for audio support."
                )

        fourcc = self._resolve_codec("mp4", codec)
        writer = cv2.VideoWriter(output_path, fourcc, fps, dimensions)
        if not writer.isOpened():
            raise RuntimeError(f"Could not open VideoWriter for {output_path}")

        try:
            for frame in self._frame_iter(first_frame, frames_iter):
                frame = self._ensure_bgr(frame, dimensions)
                writer.write(frame)
        finally:
            writer.release()

    def _write_mp4_with_av(
        self,
        first_frame: np.ndarray,
        frames_iter: Iterable[np.ndarray],
        output_path: str,
        fps: int,
        dimensions: tuple[int, int],
        codec: Optional[str],
        source_audio: str,
    ) -> None:
        """
        Writes MP4 using PyAV with video encoding + audio passthrough.

        Audio is copied from *source_audio* without re-encoding (stream copy).
        """
        import av  # type: ignore[import-untyped]

        output = av.open(output_path, mode="w")

        # -- Video stream configuration -------------------------------------------
        video_stream = output.add_stream("libx264", rate=fps)
        video_stream.width = dimensions[0]
        video_stream.height = dimensions[1]
        video_stream.pix_fmt = "yuv420p"

        # -- Open source audio container ------------------------------------------
        src = av.open(source_audio)
        src_audio_streams = [s for s in src.streams if s.type == "audio"]
        audio_map: list[tuple[av.stream.Stream, av.stream.Stream]] = []

        for s in src_audio_streams:
            out_audio = output.add_stream(template=s)
            audio_map.append((s, out_audio))

        # -- Encode video frames --------------------------------------------------
        try:
            for idx, frame in enumerate(self._frame_iter(first_frame, frames_iter)):
                frame_bgr = self._ensure_bgr(frame, dimensions)
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                av_frame = av.VideoFrame.from_ndarray(frame_rgb, format="rgb24")
                av_frame.pts = idx
                for packet in video_stream.encode(av_frame):
                    output.mux(packet)

            # Flush video encoder
            for packet in video_stream.encode():
                output.mux(packet)

            # -- Copy audio packets (stream copy, no re-encode) -------------------
            for src_stream, out_stream in audio_map:
                for packet in src.demux(src_stream):
                    if packet.dts is None:
                        continue
                    packet.stream = out_stream
                    output.mux(packet)
        finally:
            src.close()
            output.close()

    def _write_gif(
        self,
        first_frame: np.ndarray,
        frames_iter: Iterable[np.ndarray],
        output_path: str,
        fps: int,
    ) -> None:
        images = []
        for frame in self._frame_iter(first_frame, frames_iter):
            if frame.ndim == 2:
                images.append(Image.fromarray(frame, mode="L"))
            elif frame.shape[2] == 4:
                images.append(Image.fromarray(frame, mode="RGBA"))
            else:
                images.append(Image.fromarray(frame, mode="RGB"))

        if not images:
            raise ValueError("Cannot write GIF from empty frame sequence")

        duration_ms = int(1000 / fps) if fps > 0 else 100
        images[0].save(
            output_path,
            save_all=True,
            append_images=images[1:],
            duration=duration_ms,
            loop=0,
        )

    def _ensure_bgr(
        self, frame: np.ndarray, dimensions: tuple[int, int]
    ) -> np.ndarray:
        """
        Resizes the frame to the target dimensions and converts it to BGR
        for OpenCV's VideoWriter.
        """
        if frame.shape[1] != dimensions[0] or frame.shape[0] != dimensions[1]:
            frame = cv2.resize(frame, dimensions, interpolation=cv2.INTER_AREA)

        if frame.ndim == 2:
            return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        if frame.shape[2] == 4:
            return cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        if frame.shape[2] == 3:
            return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        raise ValueError(f"Unsupported frame channel count: {frame.shape[2]}")
