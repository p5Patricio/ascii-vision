"""GUI import smoke tests — verify no circular imports and module discovery."""

import sys



def test_gui_modules_importable():
    sys.path.insert(0, "src")
    try:
        pass
    finally:
        sys.path.remove("src")


def test_no_circular_imports():
    sys.path.insert(0, "src")
    try:
        import ascii_vision_gui.app

        # Force main window and its dependencies to load
        import ascii_vision_gui.main_window
        import ascii_vision_gui.widgets
        import ascii_vision_gui.rendering
        import ascii_vision_gui.style

        assert ascii_vision_gui.app is not None
        assert ascii_vision_gui.main_window is not None
    finally:
        sys.path.remove("src")


def test_ascii_to_pixmap_render_runs(qapp):
    """Instantiate AsciiToPixmap and render a small colored grid."""
    sys.path.insert(0, "src")
    try:
        import numpy as np
        from PySide6.QtCore import QSize
        from ascii_vision_gui.rendering import AsciiToPixmap

        renderer = AsciiToPixmap("JetBrains Mono", bg_color="Black")
        text = "AB\nCD"
        color_matrix = np.array([
            [[255, 0, 0], [0, 255, 0]],
            [[0, 0, 255], [255, 255, 255]],
        ], dtype=np.uint8)
        pixmap = renderer.render(text, QSize(40, 40), cols=2, rows=2, color_matrix=color_matrix)
        assert pixmap is not None
        assert not pixmap.isNull()
    finally:
        sys.path.remove("src")
