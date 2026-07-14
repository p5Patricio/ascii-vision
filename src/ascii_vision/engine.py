import cv2
import numpy as np
from .glyph_cache import GlyphCache
from .metrics import brightness_mapping_vectorized, compute_mse, compute_ssim

class ConversionEngine:
    """
    Coordinates the ASCII art conversion pipeline.
    Applies filters, resizes images, matches image blocks against the pre-rendered glyph cache,
    and handles workload estimation.
    """
    def __init__(self, glyph_cache: GlyphCache, metric: str = None, preset: str = "Balanced", preprocessing: dict = None):
        """
        Initializes the conversion engine.
        
        Parameters:
            glyph_cache: An instance of GlyphCache.
            metric: Algorithm to use ("MSE", "SSIM", "Brightness"). If None, set based on preset.
            preset: Performance/quality preset ("Fast", "Balanced", "High", "Max").
            preprocessing: Preprocessing parameters dict (brightness, contrast, sharpening, gaussian_blur).
        """
        self.glyph_cache = glyph_cache
        self.preset = preset
        
        # Determine metric and glyph resolution based on preset if not overridden
        preset_metrics = {
            "Fast": "Brightness",
            "Balanced": "MSE",
            "High": "SSIM",
            "Max": "SSIM"
        }
        self.metric = metric if metric is not None else preset_metrics.get(preset, "MSE")
        
        preset_sizes = {
            "Fast": (8, 8),
            "Balanced": (10, 10),
            "High": (10, 10),
            "Max": None  # Native resolution
        }
        self.glyph_size = preset_sizes.get(preset, (10, 10))
        
        # Load preprocessing defaults
        self.preprocessing = {
            "brightness": 1.0,
            "contrast": 1.0,
            "sharpening": 0.0,
            "gaussian_blur": 0.0
        }
        if preprocessing:
            self.preprocessing.update(preprocessing)
            
        # Initialize brightness mapping state
        self.sorted_charset = ""
        self.sorted_densities = np.array([])
        
        # Auto-Optimization: Pre-render glyph cache
        self.glyph_cache.render(target_size=self.glyph_size, as_float=True)

    def _prepare_brightness_mapping(self) -> None:
        """
        Sorts the active glyphs by their average density (brightness) for direct indexing.
        """
        if self.sorted_charset:
            return  # Already prepared
            
        # Calculate density (mean intensity) for each glyph in the cache
        # glyph_cache.cache has shape (N, H, W)
        densities = np.mean(self.glyph_cache.cache, axis=(1, 2))
        sorted_indices = np.argsort(densities)
        
        self.sorted_charset = "".join(self.glyph_cache.charset[i] for i in sorted_indices)
        self.sorted_densities = densities[sorted_indices]

    @staticmethod
    def preprocess_image(image: np.ndarray, brightness: float = 1.0, contrast: float = 1.0, sharpening: float = 0.0, gaussian_blur: float = 0.0) -> np.ndarray:
        """
        Applies brightness, contrast, Gaussian blur, and sharpening filters to the source frame.
        """
        # Convert RGB to Grayscale
        if image.ndim == 3:
            if image.dtype != np.uint8:
                image = np.clip(image, 0, 255).astype(np.uint8)
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
            if gray.dtype != np.uint8:
                gray = np.clip(gray, 0, 255).astype(np.uint8)

        # 1. Apply brightness
        if brightness != 1.0:
            gray = np.clip(gray.astype(float) * brightness, 0, 255).astype(np.uint8)

        # 2. Apply contrast
        if contrast != 1.0:
            gray = np.clip(128.0 + contrast * (gray.astype(float) - 128.0), 0, 255).astype(np.uint8)

        # 3. Apply Gaussian Blur
        if gaussian_blur > 0.0:
            # Kernel size must be odd and positive
            ksize = int(round(gaussian_blur * 3)) * 2 + 1
            gray = cv2.GaussianBlur(gray, (ksize, ksize), gaussian_blur)

        # 4. Apply Sharpening
        if sharpening > 0.0:
            s = sharpening
            kernel = np.array([
                [0, -s, 0],
                [-s, 1 + 4*s, -s],
                [0, -s, 0]
            ], dtype=np.float32)
            gray = cv2.filter2D(gray, -1, kernel)

        return gray

    def get_output_dimensions(self, img_width: int, img_height: int, cols: int) -> tuple[int, int]:
        """
        Calculates target output rows based on columns, original image size, and character aspect ratio.
        """
        ar_glyph = self.glyph_cache.char_aspect_ratio
        rows = int(round(cols * ar_glyph * (img_height / img_width)))
        return max(1, rows), cols

    def estimate_workload(self, img_width: int, img_height: int, cols: int) -> dict:
        """
        Estimates the processing workload (low, medium, high) based on dimension details.
        """
        rows, calculated_cols = self.get_output_dimensions(img_width, img_height, cols)
        total_blocks = rows * calculated_cols
        num_glyphs = len(self.glyph_cache.charset)
        
        # Scale resolution
        gh, gw = self.glyph_cache.cache.shape[1:] if self.glyph_cache.cache.size > 0 else (10, 10)
        comparisons = total_blocks * num_glyphs
        flops_est = comparisons * gh * gw
        
        if flops_est < 5000000:
            complexity = "Low"
        elif flops_est < 50000000:
            complexity = "Medium"
        elif flops_est < 200000000:
            complexity = "High"
        else:
            complexity = "Max"
            
        return {
            "rows": rows,
            "columns": calculated_cols,
            "total_blocks": total_blocks,
            "num_glyphs": num_glyphs,
            "estimated_flops": flops_est,
            "complexity": complexity
        }

    def convert(self, frame: np.ndarray, cols: int) -> np.ndarray:
        """
        Converts the source frame into a 2D matrix of ASCII/Unicode characters.
        """
        # 1. Preprocess image
        preprocessed = self.preprocess_image(
            frame, 
            brightness=self.preprocessing.get("brightness", 1.0),
            contrast=self.preprocessing.get("contrast", 1.0),
            sharpening=self.preprocessing.get("sharpening", 0.0),
            gaussian_blur=self.preprocessing.get("gaussian_blur", 0.0)
        )
        
        # 2. Determine target rows/columns
        img_height, img_width = preprocessed.shape
        rows, cols = self.get_output_dimensions(img_width, img_height, cols)
        
        # Get active glyph shape from pre-rendered cache
        gh, gw = self.glyph_cache.cache.shape[1:]
        
        # 3. Resize preprocessed image using area interpolation to exactly match output block grid
        target_h = rows * gh
        target_w = cols * gw
        resized = cv2.resize(preprocessed, (target_w, target_h), interpolation=cv2.INTER_AREA)
        
        # Normalize resized values to [0.0, 1.0]
        resized_normalized = resized.astype(np.float32) / 255.0
        
        # 4. Segment image into cell blocks using reshape & transpose tricks
        reshaped = resized_normalized.reshape(rows, gh, cols, gw)
        blocks = reshaped.transpose(0, 2, 1, 3)  # Shape: (rows, cols, gh, gw)
        
        # 5. Map blocks to glyphs
        char_matrix = np.empty((rows, cols), dtype='U1')
        glyphs = self.glyph_cache.cache
        
        if self.metric == "Brightness":
            self._prepare_brightness_mapping()
            # Vectorized mapping for all blocks
            indices = brightness_mapping_vectorized(blocks, len(self.sorted_charset))
            for r in range(rows):
                for c in range(cols):
                    char_matrix[r, c] = self.sorted_charset[indices[r, c]]
        else:
            # Compute similarity row-by-row to balance memory footprint and vectorized execution
            for r in range(rows):
                for c in range(cols):
                    block = blocks[r, c]
                    if self.metric == "MSE":
                        scores = compute_mse(block, glyphs)
                        best_idx = np.argmin(scores)
                    elif self.metric == "SSIM":
                        scores = compute_ssim(block, glyphs, dynamic_range=1.0)
                        best_idx = np.argmax(scores)
                    else:
                        scores = compute_mse(block, glyphs)
                        best_idx = np.argmin(scores)
                        
                    char_matrix[r, c] = self.glyph_cache.charset[best_idx]
                    
        return char_matrix
