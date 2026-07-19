"""ASCII-to-QPixmap rendering utilities for colored preview."""

import numpy as np
from PySide6.QtCore import QSize, QRectF, Qt
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont


class AsciiToPixmap:
    """
    Render ASCII text into a QPixmap using a monospaced font and optional
    per-cell color matrix.
    """

    def __init__(self, font_family: str, bg_color: str = "Black"):
        self.font_family = font_family
        self.bg_color = bg_color

    def render(
        self,
        text: str,
        size: QSize,
        cols: int,
        rows: int,
        color_matrix: np.ndarray | None = None,
        metric: str = "MSE",
    ) -> QPixmap:
        pixmap = QPixmap(size)

        bg_color_str = self.bg_color.lower()
        if color_matrix is not None:
            if bg_color_str == "white":
                pixmap.fill(QColor(255, 255, 255))
            elif bg_color_str == "transparent":
                pixmap.fill(QColor(0, 0, 0, 0))
            else:
                pixmap.fill(QColor(0, 0, 0))
        else:
            pixmap.fill(QColor("#151515"))

        painter = QPainter(pixmap)
        cell_w = size.width() / cols
        cell_h = size.height() / rows

        font = QFont(self.font_family)
        font.setPixelSize(max(1, int(cell_h)))
        painter.setFont(font)

        default_pen = QColor("#d4d4d4")
        if metric == "SSIM":
            default_pen = QColor("#a3e635")
        elif metric == "Brightness":
            default_pen = QColor("#60a5fa")

        painter.setPen(default_pen)

        lines = text.split("\n")
        for r, line in enumerate(lines):
            if r >= rows:
                break
            for c, char in enumerate(line):
                if c >= cols:
                    break
                if color_matrix is not None and r < color_matrix.shape[0] and c < color_matrix.shape[1]:
                    rgb = color_matrix[r, c]
                    qr = int(np.clip(np.round(rgb[0] / 16.0) * 16, 0, 255))
                    qg = int(np.clip(np.round(rgb[1] / 16.0) * 16, 0, 255))
                    qb = int(np.clip(np.round(rgb[2] / 16.0) * 16, 0, 255))
                    painter.setPen(QColor(qr, qg, qb))
                else:
                    painter.setPen(default_pen)

                rect = QRectF(c * cell_w, r * cell_h, cell_w, cell_h)
                painter.drawText(rect, Qt.AlignCenter, char)

        painter.end()
        return pixmap

    def __call__(self, *args, **kwargs) -> QPixmap:
        return self.render(*args, **kwargs)
