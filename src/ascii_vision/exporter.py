import html
import logging
import os
import platform
import numpy as np
from PIL import Image, ImageFont, ImageDraw

logger = logging.getLogger(__name__)

def _quantize_color(rgb: np.ndarray) -> tuple:
    """
    Quantize an RGB channel triple to the nearest multiple of 16.
    Returns a (R, G, B) tuple of ints clipped to [0, 255].
    """
    return (
        int(np.clip(np.round(float(rgb[0]) / 16.0) * 16, 0, 255)),
        int(np.clip(np.round(float(rgb[1]) / 16.0) * 16, 0, 255)),
        int(np.clip(np.round(float(rgb[2]) / 16.0) * 16, 0, 255)),
    )


def _resolve_bg_color(bg_color: str) -> dict:
    """
    Normalise the background colour string to per-exporter rendering values.
    
    Returns a dict with keys for CSS (css_bg, css_text), SVG (svg_fill,
    svg_text), and PNG (png_mode, png_bg, png_text).
    """
    lower = bg_color.lower() if isinstance(bg_color, str) else "black"
    if lower == "white":
        return {
            "css_bg": "#ffffff", "css_text": "#000000",
            "svg_fill": "#ffffff", "svg_text": "#000000",
            "png_mode": "RGB", "png_bg": (255, 255, 255), "png_text": (0, 0, 0),
        }
    if lower == "transparent":
        return {
            "css_bg": "transparent", "css_text": "#ffffff",
            "svg_fill": "none", "svg_text": "#ffffff",
            "png_mode": "RGBA", "png_bg": (0, 0, 0, 0), "png_text": (255, 255, 255, 255),
        }
    # Default: black
    return {
        "css_bg": "#000000", "css_text": "#ffffff",
        "svg_fill": "#000000", "svg_text": "#ffffff",
        "png_mode": "RGB", "png_bg": (0, 0, 0), "png_text": (255, 255, 255),
    }


def _rle_color_spans(char_matrix: np.ndarray, color_matrix: np.ndarray):
    """
    Yield per-row lists of ``(text_run, quantized_rgb_tuple)`` for RLE-compressed
    colour spans.
    """
    rows, cols = char_matrix.shape
    for r in range(rows):
        runs = []
        cur_color = None
        cur_run = []
        for c in range(cols):
            ch = char_matrix[r, c]
            q_rgb = _quantize_color(color_matrix[r, c])
            if cur_color is None:
                cur_color = q_rgb
                cur_run.append(ch)
            elif q_rgb == cur_color:
                cur_run.append(ch)
            else:
                runs.append(("".join(cur_run), cur_color))
                cur_color = q_rgb
                cur_run = [ch]
        if cur_run:
            runs.append(("".join(cur_run), cur_color))
        yield runs


def to_txt(char_matrix: np.ndarray, color_matrix: np.ndarray = None) -> str:
    """
    Converts character matrix into a single newline-separated plaintext string.
    If color_matrix is provided, injects true 24-bit ANSI escape codes at color boundaries.
    """
    if char_matrix.ndim != 2:
        raise ValueError("char_matrix must be a 2D numpy array of strings/characters")
    
    if color_matrix is None:
        return "\n".join("".join(row) for row in char_matrix)
        
    if color_matrix.shape[:2] != char_matrix.shape:
        raise ValueError("color_matrix shape must match char_matrix shape")
        
    rows, cols = char_matrix.shape
    lines = []
    
    for r in range(rows):
        line_parts = []
        active_color = None
        
        for c in range(cols):
            char = char_matrix[r, c]
            qr, qg, qb = _quantize_color(color_matrix[r, c])
            color_tuple = (qr, qg, qb)
            
            if active_color is None or color_tuple != active_color:
                line_parts.append(f"\033[38;2;{qr};{qg};{qb}m")
                active_color = color_tuple
            
            line_parts.append(char)
            
        line_parts.append("\033[0m")
        lines.append("".join(line_parts))
        
    return "\n".join(lines)


def to_html(
    char_matrix: np.ndarray,
    font_name: str,
    font_size: int,
    color_matrix: np.ndarray = None,
    bg_color: str = "Black"
) -> str:
    """
    Formats the character matrix into a self-contained, CSS-styled HTML page.
    """
    if char_matrix.ndim != 2:
        raise ValueError("char_matrix must be a 2D numpy array")

    bg = _resolve_bg_color(bg_color)
    bg_css = bg["css_bg"]
    text_css = bg["css_text"]

    if color_matrix is None:
        text_content = to_txt(char_matrix)
        escaped_content = html.escape(text_content)
    else:
        if color_matrix.shape[:2] != char_matrix.shape:
            raise ValueError("color_matrix shape must match char_matrix shape")
        html_lines = []
        for runs in _rle_color_spans(char_matrix, color_matrix):
            row_spans = []
            for text, color in runs:
                escaped_run = html.escape(text)
                row_spans.append(f'<span style="color:rgb({color[0]},{color[1]},{color[2]})">{escaped_run}</span>')
            html_lines.append("".join(row_spans))
        escaped_content = "\n".join(html_lines)
    
    html_template = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>ASCII Art Export</title>
<style>
  body {{
    background-color: {bg_css};
    color: {text_css};
    margin: 0;
    padding: 20px;
    display: flex;
    justify-content: center;
    align-items: center;
  }}
  pre {{
    font-family: "{font_name}", "Courier New", monospace;
    font-size: {font_size}px;
    line-height: 1.0;
    letter-spacing: 0px;
    white-space: pre;
    margin: 0;
    padding: 0;
  }}
</style>
</head>
<body>
<pre>{escaped_content}</pre>
</body>
</html>
"""
    return html_template


def to_svg(
    char_matrix: np.ndarray,
    font_name: str,
    font_size: int,
    char_aspect_ratio: float = 0.6,
    color_matrix: np.ndarray = None,
    bg_color: str = "Black"
) -> str:
    """
    Renders the character matrix into a vector SVG document containing <text> lines.
    """
    if char_matrix.ndim != 2:
        raise ValueError("char_matrix must be a 2D numpy array")
        
    rows, cols = char_matrix.shape
    char_width = char_aspect_ratio * font_size
    char_height = font_size

    svg_width = cols * char_width
    svg_height = rows * char_height

    bg = _resolve_bg_color(bg_color)
    bg_fill = bg["svg_fill"]
    text_fill = bg["svg_text"]

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}">')
    lines.append(f'  <rect width="100%" height="100%" fill="{bg_fill}"/>')
    lines.append(f'  <g font-family="{font_name}" font-size="{font_size}" fill="{text_fill}" xml:space="preserve">')

    span_gen = _rle_color_spans(char_matrix, color_matrix) if color_matrix is not None else None
    for i in range(rows):
        y_pos = (i + 1) * char_height
        
        if color_matrix is None:
            text_content = html.escape("".join(char_matrix[i]))
        else:
            if color_matrix.shape[:2] != char_matrix.shape:
                raise ValueError("color_matrix shape must match char_matrix shape")
            runs = next(span_gen)
            row_tspans = []
            for text, color in runs:
                escaped_run = html.escape(text)
                row_tspans.append(f'<tspan fill="rgb({color[0]},{color[1]},{color[2]})">{escaped_run}</tspan>')
            text_content = "".join(row_tspans)
            
        lines.append(f'    <text x="0" y="{y_pos}">{text_content}</text>')

    lines.append('  </g>')
    lines.append('</svg>')
    return "\n".join(lines)


def to_png(
    char_matrix: np.ndarray,
    font_path: str,
    font_size: int,
    color_matrix: np.ndarray = None,
    bg_color: str = "Black"
) -> Image.Image:
    """
    Draws the character matrix back onto a bitmap PNG image using Pillow and a TTF font.
    """
    if char_matrix.ndim != 2:
        raise ValueError("char_matrix must be a 2D numpy array")
        
    # Load the font
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Font file not found: {font_path}")
        
    font = ImageFont.truetype(font_path, font_size)

    # Determine monospace cell dimensions
    try:
        ascent, descent = font.getmetrics()
        cell_height = ascent + descent
    except Exception:
        bbox = font.getbbox("M")
        cell_height = bbox[3] - bbox[1]

    try:
        cell_width = int(font.getlength("M"))
    except Exception:
        bbox = font.getbbox("M")
        cell_width = bbox[2] - bbox[0]

    if cell_width <= 0:
        cell_width = int(font_size * 0.6)
    if cell_height <= 0:
        cell_height = font_size

    rows, cols = char_matrix.shape
    img_width = cols * cell_width
    img_height = rows * cell_height

    bg = _resolve_bg_color(bg_color)
    img_mode = bg["png_mode"]
    bg_fill = bg["png_bg"]
    default_text_fill = bg["png_text"]

    img = Image.new(img_mode, (img_width, img_height), color=bg_fill)
    draw = ImageDraw.Draw(img)

    for r in range(rows):
        for c in range(cols):
            char = char_matrix[r, c]
            if char != ' ':
                if color_matrix is not None:
                    if color_matrix.shape[:2] != char_matrix.shape:
                        raise ValueError("color_matrix shape must match char_matrix shape")
                    qr, qg, qb = _quantize_color(color_matrix[r, c])
                    if img_mode == "RGBA":
                        cell_color = (qr, qg, qb, 255)
                    else:
                        cell_color = (qr, qg, qb)
                else:
                    cell_color = default_text_fill
                
                # Draw character at its grid cell top-left
                draw.text((c * cell_width, r * cell_height), char, font=font, fill=cell_color)

    return img


def to_clipboard(char_matrix: np.ndarray, color_matrix: np.ndarray = None) -> bool:
    """
    Copies the ASCII character matrix as text to the system clipboard.
    First attempts native Windows API calls (if on Windows) to avoid PySide6 overhead,
    then falls back to PySide6.
    """
    text = to_txt(char_matrix, color_matrix)

    # 1. Native Windows Clipboard Implementation
    if platform.system() == "Windows":
        try:
            import ctypes
            from ctypes import wintypes

            OpenClipboard = ctypes.windll.user32.OpenClipboard
            OpenClipboard.argtypes = [wintypes.HWND]
            OpenClipboard.restype = wintypes.BOOL

            EmptyClipboard = ctypes.windll.user32.EmptyClipboard
            EmptyClipboard.argtypes = []
            EmptyClipboard.restype = wintypes.BOOL

            SetClipboardData = ctypes.windll.user32.SetClipboardData
            SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
            SetClipboardData.restype = wintypes.HANDLE

            CloseClipboard = ctypes.windll.user32.CloseClipboard
            CloseClipboard.argtypes = []
            CloseClipboard.restype = wintypes.BOOL

            GlobalAlloc = ctypes.windll.kernel32.GlobalAlloc
            GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
            GlobalAlloc.restype = wintypes.HANDLE

            GlobalLock = ctypes.windll.kernel32.GlobalLock
            GlobalLock.argtypes = [wintypes.HANDLE]
            GlobalLock.restype = ctypes.c_void_p

            GlobalUnlock = ctypes.windll.kernel32.GlobalUnlock
            GlobalUnlock.argtypes = [wintypes.HANDLE]
            GlobalUnlock.restype = wintypes.BOOL

            GlobalFree = ctypes.windll.kernel32.GlobalFree
            GlobalFree.argtypes = [wintypes.HANDLE]
            GlobalFree.restype = wintypes.HANDLE

            memmove = ctypes.cdll.msvcrt.memmove
            memmove.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
            memmove.restype = ctypes.c_void_p

            GMEM_MOVEABLE = 0x0002
            CF_UNICODETEXT = 13

            if OpenClipboard(None):
                try:
                    EmptyClipboard()
                    encoded = text.encode('utf-16le') + b'\x00\x00'
                    h_mem = GlobalAlloc(GMEM_MOVEABLE, len(encoded))
                    if h_mem:
                        ptr = GlobalLock(h_mem)
                        if ptr:
                            memmove(ptr, encoded, len(encoded))
                            GlobalUnlock(h_mem)
                            if SetClipboardData(CF_UNICODETEXT, h_mem):
                                return True
                            else:
                                GlobalFree(h_mem)
                        else:
                            GlobalFree(h_mem)
                finally:
                    CloseClipboard()
        except Exception as exc:
            logger.warning("Native clipboard API failed: %s", exc)

    # 2. PySide6 Fallback
    try:
        from PySide6.QtGui import QGuiApplication
        app = QGuiApplication.instance()
        if app is None:
            # Create a temporary headless instance if not already running
            app = QGuiApplication([])
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        return True
    except Exception as exc:
        logger.warning("PySide6 clipboard fallback failed: %s", exc)

    return False


class ExportManager:
    """
    Shared dispatcher for ASCII conversion results.

    Routes a character matrix (and optional color matrix) to TXT, HTML, SVG,
    PNG, or Clipboard. CLI and GUI use the same path so identical settings
    produce identical output.
    """

    SUPPORTED_FORMATS = {"txt", "html", "svg", "png", "clipboard"}

    def _resolve_format(self, output_path: str | None, format: str | None) -> str:
        """
        Determine the target format from the explicit format argument or the
        output path extension. Clipboard is selected when output_path is None.
        """
        if format is not None:
            fmt = format.lower().lstrip(".")
            if fmt not in self.SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported format '{format}'. Supported: {', '.join(sorted(self.SUPPORTED_FORMATS))}")
            return fmt

        if output_path is None:
            return "clipboard"

        ext = os.path.splitext(output_path)[1].lower().lstrip(".")
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported output extension '.{ext}'. Supported: {', '.join(sorted(self.SUPPORTED_FORMATS))}"
            )
        return ext

    def save(
        self,
        char_matrix: np.ndarray,
        output_path: str | None,
        font_name: str,
        font_size: int,
        color_matrix: np.ndarray | None = None,
        bg_color: str = "Black",
        format: str | None = None,
        font_path: str | None = None,
    ) -> str | bool:
        """
        Save a character matrix to the requested output format.

        Parameters:
            char_matrix: 2D array of characters.
            output_path: Destination path. None for clipboard.
            font_name: Font family name for HTML/SVG.
            font_size: Font size in pixels for HTML/SVG.
            color_matrix: Optional per-cell RGB colors.
            bg_color: Background color ("Black", "White", "Transparent").
            format: Optional format override.
            font_path: Required for PNG output.

        Returns:
            output_path on file saves, True/False for clipboard.

        Raises:
            ValueError: For unsupported format or missing required arguments.
            OSError: If the destination cannot be written.
        """
        fmt = self._resolve_format(output_path, format)

        if fmt == "clipboard":
            return to_clipboard(char_matrix, color_matrix)

        if output_path is None:
            raise ValueError("output_path is required for file-based formats")

        # Ensure parent directory exists before creating any file.
        parent_dir = os.path.dirname(os.path.abspath(output_path))
        if parent_dir and not os.path.exists(parent_dir):
            raise FileNotFoundError(f"Output directory does not exist: {parent_dir}")

        try:
            if fmt == "txt":
                content = to_txt(char_matrix, color_matrix)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
            elif fmt == "html":
                content = to_html(char_matrix, font_name, font_size, color_matrix, bg_color)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
            elif fmt == "svg":
                content = to_svg(char_matrix, font_name, font_size, color_matrix=color_matrix, bg_color=bg_color)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
            elif fmt == "png":
                if font_path is None:
                    raise ValueError("font_path is required for PNG export")
                img = to_png(char_matrix, font_path, font_size, color_matrix, bg_color)
                img.save(output_path)
        except Exception as exc:
            # Remove any partial file if one was created.
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            raise

        return output_path
