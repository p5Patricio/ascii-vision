import threading
import time
import warnings
from typing import Generator
import numpy as np
from PySide6.QtCore import QObject, QSize, Signal, Slot
from PySide6.QtGui import QPixmap

from ascii_vision.frame_provider import FrameProvider, StaticImageFrameProvider, WebcamFrameProvider
from ascii_vision.exporter import to_txt
from ascii_vision_gui.rendering import AsciiToPixmap


class ConversionWorker(QObject):
    """
    Worker class executing the ASCII conversion pipeline on a background thread.

    Iterates over a FrameProvider and delegates each frame to ConversionEngine.convert().
    Emits progress, ETA, warnings, results, and errors. Supports cooperative cancellation.
    """
    progress = Signal(int, str)  # (percentage, stage_name)
    result = Signal(np.ndarray, int, int, object, str)  # (char_matrix, cols, rows, color_matrix, ascii_text)
    error = Signal(str)
    eta = Signal(str, str)  # (eta_string, elapsed_string)
    warning = Signal(str)
    finished = Signal()

    def __init__(self, image_source, engine, config: dict):
        """
        Parameters:
            image_source: A file path (str) or a FrameProvider instance.
            engine: A ConversionEngine instance.
            config: Conversion configuration dict.
        """
        super().__init__()
        self.image_source = image_source
        self.engine = engine
        self.config = config
        self._cancel_event = threading.Event()

    @property
    def is_cancelled(self):
        return self._cancel_event.is_set()

    def _create_provider(self) -> FrameProvider:
        """
        Build a FrameProvider from the configured image_source.
        """
        if isinstance(self.image_source, FrameProvider):
            return self.image_source
        return StaticImageFrameProvider(self.image_source)

    def _load_frames(self, provider: FrameProvider) -> Generator[np.ndarray, None, None]:
        """
        Yield frames from the provider while honoring cancellation.
        Ensures the provider is cleaned up when the generator closes.
        """
        try:
            for frame in provider.get_frames():
                if self.is_cancelled:
                    return
                yield frame
        finally:
            provider.cleanup()

    @Slot()
    def run(self):
        """
        Run the conversion loop. For each frame, delegate to the engine and keep
        the last result. The result signal is emitted once after all frames are
        processed, carrying the final char_matrix so consumers do not need to
        rebuild it from text.
        """
        try:
            start_time = time.time()
            self.progress.emit(0, "Initializing")

            if self.is_cancelled:
                self.finished.emit()
                return

            cols = self.config.get("columns", 100)
            color_mode = self.config.get("color_mode", False)

            provider = self._create_provider()
            total_frames = provider.total_frames
            frames = self._load_frames(provider)

            self.progress.emit(10, "Loading Frames")

            # Capture warnings during execution (e.g. font fallbacks)
            with warnings.catch_warnings(record=True) as caught_warnings:
                warnings.simplefilter("always")

                processed_count = 0
                final_char_matrix = None
                final_color_matrix = None
                final_ascii_text = ""

                for frame in frames:
                    if self.is_cancelled:
                        self.finished.emit()
                        return

                    processed_count += 1
                    self.progress.emit(
                        20,
                        f"Converting Frame {processed_count}/{total_frames}"
                        if total_frames > 1
                        else "Converting Frame",
                    )

                    engine_result = self.engine.convert(frame, cols=cols, color_mode=color_mode)
                    if color_mode and isinstance(engine_result, tuple):
                        char_matrix, color_matrix = engine_result
                    else:
                        char_matrix = engine_result
                        color_matrix = None

                    final_char_matrix = char_matrix
                    final_color_matrix = color_matrix
                    final_ascii_text = to_txt(char_matrix)

                    if total_frames > 1:
                        pct = 20 + int((processed_count / total_frames) * 70)
                    else:
                        pct = 50
                    elapsed = time.time() - start_time
                    eta_val = (elapsed / processed_count) * (total_frames - processed_count) if total_frames > processed_count else 0
                    self.progress.emit(pct, f"Frame {processed_count}/{total_frames}")
                    self.eta.emit(f"{eta_val:.1f}s", f"{elapsed:.1f}s")

                for w in caught_warnings:
                    self.warning.emit(str(w.message))

            if final_char_matrix is None:
                raise ValueError("No frames loaded from the image source.")

            if self.is_cancelled:
                self.finished.emit()
                return

            rows, cols = final_char_matrix.shape
            elapsed = time.time() - start_time
            self.eta.emit("0.0s", f"{elapsed:.1f}s")
            self.progress.emit(100, "Done")
            self.result.emit(final_char_matrix, cols, rows, final_color_matrix, final_ascii_text)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def cancel(self):
        """
        Request cooperative cancellation. The worker will stop at the next
        frame boundary.
        """
        self._cancel_event.set()


class WebcamWorker(QObject):
    """
    Streaming worker for live webcam preview.

    Captures frames from a :class:`WebcamFrameProvider`, delegates each frame
    to the engine, and emits a rendered :class:`QPixmap` for the GUI preview.
    The provider is released when the worker is cancelled or the generator
    exits.

    Accepts either a pre-built ``WebcamFrameProvider`` (backward compatible
    with tests) or an integer device index that will be used to create the
    provider lazily inside :meth:`run()` so the camera open does not block
    the calling (GUI) thread.
    """
    frame_ready = Signal(QPixmap)
    error = Signal(str)
    finished = Signal()
    ready = Signal()

    def __init__(
        self, provider_or_device, engine,
        cols: int = 40, color_mode: bool = True,
        target_fps: int = 15, adaptive: bool = False,
    ):
        """
        Parameters:
            provider_or_device:
                Either a :class:`WebcamFrameProvider` instance (for testing or
                pre-opened cameras) or an ``int`` device index that will be
                opened lazily in :meth:`run`.
            engine: A :class:`~ascii_vision.engine.ConversionEngine` instance.
            cols: Target number of ASCII columns.
            color_mode: Whether to preserve colour information.
            target_fps: Target frame rate for streaming preview (1-60).
            adaptive: When True, dynamically adjust quality to meet target FPS.
        """
        super().__init__()
        if isinstance(provider_or_device, WebcamFrameProvider):
            self.provider = provider_or_device
            self._device_index = None
        else:
            self._device_index = int(provider_or_device)
            self.provider = None
        self.engine = engine
        self.cols = cols
        self.color_mode = color_mode
        self.target_fps = target_fps
        self.adaptive = adaptive
        self._cancel_event = threading.Event()
        # -- Adaptive quality state ---------------------------------------------
        self._adapted_cols: float = float(cols)
        self._frame_times: list[float] = []
        self._skip_counter: int = 0

    @property
    def is_cancelled(self):
        return self._cancel_event.is_set()

    @Slot()
    def run(self):
        try:
            # --- Lazily open the camera on the worker thread ------------------
            if self.is_cancelled:
                return
            if self.provider is None:
                try:
                    self.provider = WebcamFrameProvider(self._device_index)
                except Exception as exc:
                    self.error.emit(f"Could not open camera: {exc}")
                    self.provider = None
                    return
                self.ready.emit()

            frame_start = time.time()
            frame_count = 0
            for frame in self.provider.get_frames():
                if self.is_cancelled:
                    return

                # -- Adaptive frame skip ----------------------------------
                if self._skip_counter > 0:
                    self._skip_counter -= 1
                    frame_start = time.time()
                    continue

                # Use adapted cols (may be lower when throttled)
                result = self.engine.convert(
                    frame, cols=int(self._adapted_cols), color_mode=self.color_mode,
                )

                # -- FPS measurement --------------------------------------
                elapsed = time.time() - frame_start
                self._frame_times.append(elapsed)
                if len(self._frame_times) > 30:
                    self._frame_times.pop(0)
                frame_count += 1

                # -- Adaptive quality adjustment --------------------------
                if self.adaptive and self.target_fps > 0 and len(self._frame_times) >= 5:
                    avg_time = sum(self._frame_times) / len(self._frame_times)
                    actual_fps = 1.0 / avg_time if avg_time > 0 else 999.0

                    if actual_fps < self.target_fps * 0.85:
                        # Behind target → reduce quality
                        new_cols = int(self._adapted_cols * 0.8)
                        self._adapted_cols = max(20.0, float(new_cols))

                        # Metric downgrade: SSIM → MSE → Brightness
                        metric = getattr(self.engine, "metric", "MSE")
                        if metric == "SSIM":
                            self.engine.metric = "MSE"
                        elif metric == "MSE":
                            self.engine.metric = "Brightness"

                        # Persistent deficit → skip every other frame
                        if actual_fps < self.target_fps * 0.5:
                            self._skip_counter = 1  # skip next frame

                    elif actual_fps > self.target_fps * 1.2:
                        # Headroom available → restore quality
                        if self._adapted_cols < self.cols:
                            restored = int(self._adapted_cols * 1.25)
                            self._adapted_cols = min(float(self.cols), float(restored))
                        # Restore metric priority if possible
                        current = getattr(self.engine, "metric", "")
                        if current == "Brightness":
                            self.engine.metric = "MSE"
                        elif current == "MSE":
                            self.engine.metric = "SSIM"
                        self._skip_counter = 0

                # -- Render and emit -------------------------------------------
                if self.color_mode and isinstance(result, tuple):
                    char_matrix, color_matrix = result
                else:
                    char_matrix = result
                    color_matrix = None
                renderer = AsciiToPixmap("JetBrains Mono", bg_color="Black")
                text = to_txt(char_matrix)
                out_rows, out_cols = char_matrix.shape
                pixmap = renderer.render(
                    text, self._preview_size(), out_cols, out_rows,
                    color_matrix, metric=self.engine.metric,
                )
                self.frame_ready.emit(pixmap)

                frame_start = time.time()
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            if self.provider is not None:
                self.provider.cleanup()
            self.finished.emit()

    def _preview_size(self):
        return QSize(640, 480)

    def cancel(self):
        self._cancel_event.set()
        if self.provider is not None:
            self.provider.stop()
