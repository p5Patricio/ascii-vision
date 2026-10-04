"""Locate bundled resources (fonts) and pick a font that covers a character set.

Resources live inside the ``ascii_vision`` package (``assets/fonts``) so they are
found in a source checkout, in a regular ``pip install`` and in a frozen
(PyInstaller) build alike.
"""

import os
import sys
import warnings
from functools import lru_cache

from PIL import ImageFont

DEFAULT_FONT_NAME = "JetBrainsMono-Regular.ttf"
FALLBACK_FONT_NAME = "DejaVuSans.ttf"

# A code point no font defines, so it always renders as the font's "missing glyph".
_UNASSIGNED_CODEPOINT = "\U0010FFFF"


def _candidate_font_dirs() -> list[str]:
    package_dir = os.path.dirname(os.path.abspath(__file__))
    dirs = [os.path.join(package_dir, "assets", "fonts")]
    frozen_root = getattr(sys, "_MEIPASS", None)  # PyInstaller
    if frozen_root:
        dirs.insert(0, os.path.join(frozen_root, "ascii_vision", "assets", "fonts"))
    return dirs


def bundled_font_path(name: str = DEFAULT_FONT_NAME) -> str | None:
    """Absolute path of a bundled font file, or ``None`` if it cannot be found."""
    for directory in _candidate_font_dirs():
        path = os.path.join(directory, name)
        if os.path.isfile(path):
            return path
    return None


def default_font_path() -> str:
    """Path of the bundled default font (falls back to the bare file name)."""
    return bundled_font_path(DEFAULT_FONT_NAME) or DEFAULT_FONT_NAME


@lru_cache(maxsize=32)
def _notdef_signature(font_path: str) -> tuple[bytes, tuple[int, int]]:
    font = ImageFont.truetype(font_path, 24)
    mask = font.getmask(_UNASSIGNED_CODEPOINT)
    return bytes(mask), mask.size


def missing_glyphs(font_path: str, charset: str) -> list[str]:
    """Characters of *charset* that *font_path* cannot draw.

    A glyph counts as missing when it renders exactly like the font's
    "missing glyph" box. Blank characters (space, braille blank) are never
    reported because they legitimately render empty.
    """
    try:
        font = ImageFont.truetype(font_path, 24)
        notdef_bytes, notdef_size = _notdef_signature(font_path)
    except OSError:
        return []
    missing = []
    for ch in dict.fromkeys(charset):
        if ch.isspace() or ch == "⠀":
            continue
        mask = font.getmask(ch)
        if mask.size == notdef_size and bytes(mask) == notdef_bytes:
            missing.append(ch)
    return missing


def font_for_charset(font_path: str, charset: str) -> str:
    """Return *font_path*, or a bundled fallback font when it lacks glyphs.

    Without this, characters the font cannot draw (Braille in JetBrains Mono) all
    render as the same "missing glyph" box, so the conversion silently produces
    blank or meaningless output.
    """
    missing = missing_glyphs(font_path, charset)
    if not missing:
        return font_path

    fallback = bundled_font_path(FALLBACK_FONT_NAME)
    if fallback and not missing_glyphs(fallback, charset):
        warnings.warn(
            f"Font '{os.path.basename(font_path)}' has no glyphs for {len(missing)} "
            f"character(s) in this character set; using '{FALLBACK_FONT_NAME}' instead.",
            RuntimeWarning,
            stacklevel=2,
        )
        return fallback

    warnings.warn(
        f"Font '{os.path.basename(font_path)}' has no glyphs for {len(missing)} "
        "character(s) in this character set and no bundled font covers them; "
        "the output may be inaccurate.",
        RuntimeWarning,
        stacklevel=2,
    )
    return font_path
