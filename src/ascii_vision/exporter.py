import html
import os
import platform
import numpy as np
from PIL import Image, ImageFont, ImageDraw

def to_txt(char_matrix: np.ndarray) -> str:
    """
    Converts character matrix into a single newline-separated plaintext string.
    """
    if char_matrix.ndim != 2:
        raise ValueError("char_matrix must be a 2D numpy array of strings/characters")
    return "\n".join("".join(row) for row in char_matrix)


def to_html(char_matrix: np.ndarray, font_name: str, font_size: int) -> str:
    """
    Formats the character matrix into a self-contained, CSS-styled HTML page.
    """
    text_content = to_txt(char_matrix)
    escaped_content = html.escape(text_content)
    
    html_template = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>ASCII Art Export</title>
<style>
  body {{
    background-color: #000000;
    color: #ffffff;
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


def to_svg(char_matrix: np.ndarray, font_name: str, font_size: int, char_aspect_ratio: float = 0.6) -> str:
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

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}">')
    lines.append('  <rect width="100%" height="100%" fill="#000000"/>')
    lines.append(f'  <g font-family="{font_name}" font-size="{font_size}" fill="#ffffff" xml:space="preserve">')

    for i, row in enumerate(char_matrix):
        # Escape special characters for SVG/XML
        text_line = html.escape("".join(row))
        # SVG baseline positioning starts at (i + 1) * char_height
        y_pos = (i + 1) * char_height
        lines.append(f'    <text x="0" y="{y_pos}">{text_line}</text>')

    lines.append('  </g>')
    lines.append('</svg>')
    return "\n".join(lines)


def to_png(char_matrix: np.ndarray, font_path: str, font_size: int) -> Image.Image:
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

    # Create black canvas
    img = Image.new("RGB", (img_width, img_height), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    for r in range(rows):
        for c in range(cols):
            char = char_matrix[r, c]
            if char != ' ':
                # Draw character at its grid cell top-left
                draw.text((c * cell_width, r * cell_height), char, font=font, fill=(255, 255, 255))

    return img


def to_clipboard(char_matrix: np.ndarray) -> bool:
    """
    Copies the ASCII character matrix as text to the system clipboard.
    First attempts native Windows API calls (if on Windows) to avoid PySide6 overhead,
    then falls back to PySide6.
    """
    text = to_txt(char_matrix)
    
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
        except Exception:
            pass

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
    except Exception:
        pass

    return False
