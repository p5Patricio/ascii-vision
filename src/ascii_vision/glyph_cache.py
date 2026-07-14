import numpy as np
from PIL import Image, ImageFont, ImageDraw

CHARSET_PRESETS = {
    "ascii": "".join(chr(i) for i in range(32, 127)),
    "shades": " ░▒▓█",
    "blocks": " ▄▖▗▘▙▚▛▜▝▞▟■",
    "braille": "".join(chr(i) for i in range(0x2800, 0x28FF + 1))
}

class GlyphCache:
    """
    Pre-rendered glyph matrix representation for character matching.
    Supports monospace fonts and aspect-ratio calculation.
    """
    def __init__(self, font_path: str, font_size: int, charset: str = "ascii"):
        self.font_path = font_path
        self.font_size = font_size
        
        # Resolve charset preset or use the provided string directly
        self.charset = CHARSET_PRESETS.get(charset.lower(), charset)
        
        self.char_aspect_ratio: float = 0.5
        self.cache: np.ndarray = np.array([])  # Shape: (N, glyph_height, glyph_width)
        self.cache_dict: dict[str, np.ndarray] = {}
        
        # Load the font and calculate aspect ratio
        self._load_font_and_metrics()

    def _load_font_and_metrics(self) -> None:
        """
        Loads the TrueType font and calculates the dynamic glyph aspect ratio using 'M' or 'X'.
        """
        self.font = ImageFont.truetype(self.font_path, self.font_size)
        
        # Measure bounding box of character 'M' (or 'X' as fallback)
        try:
            bbox = self.font.getbbox("M")
            # bbox is (left, top, right, bottom)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            if w <= 0 or h <= 0:
                # Try 'X'
                bbox = self.font.getbbox("X")
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
            
            self.char_aspect_ratio = w / h if h > 0 else 0.5
        except Exception:
            self.char_aspect_ratio = 0.5

    def render(self, target_size: tuple[int, int] = None, as_float: bool = True) -> None:
        """
        Fills the cache and computes the glyph matrix representations.
        
        Parameters:
            target_size: Optional tuple of (height, width) to force each glyph matrix.
                         If None, the native font dimensions are used.
            as_float: If True, renders glyphs as float matrices in range [0.0, 1.0].
                      If False, renders as boolean matrices.
        """
        # Determine native dimensions of the font cell
        try:
            ascent, descent = self.font.getmetrics()
            native_height = ascent + descent
        except Exception:
            bbox = self.font.getbbox("M")
            native_height = bbox[3] - bbox[1]

        try:
            native_width = int(self.font.getlength("M"))
        except Exception:
            bbox = self.font.getbbox("M")
            native_width = bbox[2] - bbox[0]

        if native_width <= 0:
            native_width = int(self.font_size * 0.6)
        if native_height <= 0:
            native_height = self.font_size

        # Output shape for each matrix
        out_h, out_w = target_size if target_size is not None else (native_height, native_width)

        # Clear existing caches
        self.cache_dict = {}
        matrices = []

        # Determine resize filter based on PIL version
        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            # Fallback for older PIL versions
            resample_filter = Image.LANCZOS

        for char in self.charset:
            # Render character in native resolution first
            img = Image.new("L", (native_width, native_height), color=0)
            draw = ImageDraw.Draw(img)
            draw.text((0, 0), char, font=self.font, fill=255)
            
            # Resize if a target size is requested
            if target_size is not None and (native_height != out_h or native_width != out_w):
                img = img.resize((out_w, out_h), resample=resample_filter)
            
            # Convert to NumPy array
            arr = np.array(img)
            if as_float:
                matrix = arr.astype(np.float32) / 255.0
            else:
                matrix = arr > 127
            
            self.cache_dict[char] = matrix
            matrices.append(matrix)

        self.cache = np.array(matrices)
