import time
import warnings
import numpy as np
import cv2
from PySide6.QtCore import QObject, Signal, Slot

from ascii_vision.frame_provider import StaticImageFrameProvider
from ascii_vision.metrics import brightness_mapping_vectorized, compute_mse, compute_ssim
from ascii_vision.exporter import to_txt

class ConversionWorker(QObject):
    """
    Worker class executing the ASCII conversion pipeline on a background thread.
    Emits progress, ETA, warnings, results, and errors.
    Supports cooperative cancellation.
    """
    progress = Signal(int, str)  # (percentage, stage_name)
    result = Signal(str, int, int)  # (ascii_text, cols, rows)
    error = Signal(str)
    eta = Signal(str, str)  # (eta_string, elapsed_string)
    warning = Signal(str)
    finished = Signal()

    def __init__(self, image_source, engine, config: dict):
        super().__init__()
        self.image_source = image_source
        self.engine = engine
        self.config = config
        self.is_cancelled = False

    @Slot()
    def run(self):
        try:
            start_time = time.time()
            self.progress.emit(0, "Initializing")

            if self.is_cancelled:
                self.finished.emit()
                return

            # Capture warnings during execution (e.g. font fallbacks)
            with warnings.catch_warnings(record=True) as caught_warnings:
                warnings.simplefilter("always")

                self.progress.emit(10, "Loading Image")
                provider = StaticImageFrameProvider(self.image_source)
                frames = list(provider.get_frames())
                if not frames:
                    raise ValueError("No frames loaded from the image source.")
                frame = frames[0]

                if self.is_cancelled:
                    self.finished.emit()
                    return

                # Check if there were warnings during loading or rendering
                for w in caught_warnings:
                    self.warning.emit(str(w.message))

            if self.is_cancelled:
                self.finished.emit()
                return

            # Determine columns from config
            cols = self.config.get("columns", 100)

            # Preprocess image
            self.progress.emit(20, "Preprocessing Image")
            preprocessed = self.engine.preprocess_image(
                frame,
                brightness=self.engine.preprocessing.get("brightness", 1.0),
                contrast=self.engine.preprocessing.get("contrast", 1.0),
                sharpening=self.engine.preprocessing.get("sharpening", 0.0),
                gaussian_blur=self.engine.preprocessing.get("gaussian_blur", 0.0)
            )

            if self.is_cancelled:
                self.finished.emit()
                return

            # Determine dimensions
            img_height, img_width = preprocessed.shape
            rows, cols = self.engine.get_output_dimensions(img_width, img_height, cols)

            gh, gw = self.engine.glyph_cache.cache.shape[1:]

            # Resize to block grid
            target_h = rows * gh
            target_w = cols * gw
            resized = cv2.resize(preprocessed, (target_w, target_h), interpolation=cv2.INTER_AREA)

            resized_normalized = resized.astype(np.float32) / 255.0
            reshaped = resized_normalized.reshape(rows, gh, cols, gw)
            blocks = reshaped.transpose(0, 2, 1, 3)

            char_matrix = np.empty((rows, cols), dtype='U1')
            glyphs = self.engine.glyph_cache.cache

            self.progress.emit(30, "Converting Blocks")
            
            # Row-by-row processing loop to support progress reporting, ETA, and cancellation
            if self.engine.metric == "Brightness":
                self.engine._prepare_brightness_mapping()
                indices = brightness_mapping_vectorized(blocks, len(self.engine.sorted_charset))
                
                for r in range(rows):
                    if self.is_cancelled:
                        self.finished.emit()
                        return
                    
                    for c in range(cols):
                        char_matrix[r, c] = self.engine.sorted_charset[indices[r, c]]

                    # Calculate progress (from 30% to 90%)
                    pct = 30 + int((r + 1) / rows * 60)
                    elapsed = time.time() - start_time
                    eta_val = (elapsed / (r + 1)) * (rows - (r + 1)) if r >= 0 else 0
                    
                    self.progress.emit(pct, f"Converting Row {r+1}/{rows}")
                    self.eta.emit(f"{eta_val:.1f}s", f"{elapsed:.1f}s")
            else:
                for r in range(rows):
                    if self.is_cancelled:
                        self.finished.emit()
                        return
                    
                    for c in range(cols):
                        block = blocks[r, c]
                        if self.engine.metric == "MSE":
                            scores = compute_mse(block, glyphs)
                            best_idx = np.argmin(scores)
                        elif self.engine.metric == "SSIM":
                            scores = compute_ssim(block, glyphs, dynamic_range=1.0)
                            best_idx = np.argmax(scores)
                        else:
                            scores = compute_mse(block, glyphs)
                            best_idx = np.argmin(scores)
                            
                        char_matrix[r, c] = self.engine.glyph_cache.charset[best_idx]

                    # Calculate progress (from 30% to 90%)
                    pct = 30 + int((r + 1) / rows * 60)
                    elapsed = time.time() - start_time
                    eta_val = (elapsed / (r + 1)) * (rows - (r + 1)) if r >= 0 else 0
                    
                    self.progress.emit(pct, f"Converting Row {r+1}/{rows}")
                    self.eta.emit(f"{eta_val:.1f}s", f"{elapsed:.1f}s")

            if self.is_cancelled:
                self.finished.emit()
                return

            self.progress.emit(95, "Generating Output Text")
            ascii_text = to_txt(char_matrix)

            elapsed = time.time() - start_time
            self.eta.emit("0.0s", f"{elapsed:.1f}s")
            self.progress.emit(100, "Done")
            self.result.emit(ascii_text, cols, rows)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def cancel(self):
        self.is_cancelled = True
