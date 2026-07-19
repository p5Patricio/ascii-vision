"""Custom widgets for the ASCII Vision GUI."""

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QFileDialog,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap


class DropZoneWidget(QFrame):
    fileDropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        self.label = QLabel("Drag & Drop Image Here\nor Click to Browse", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #858585; font-size: 12px;")
        layout.addWidget(self.label)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("border-color: #007acc; background-color: #252526;")

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event):
        self.setStyleSheet("")
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")):
                self.fileDropped.emit(file_path)
                break

    def mousePressEvent(self, event):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image File",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)",
        )
        if file_path:
            self.fileDropped.emit(file_path)


class ComparisonWidget(QWidget):
    """
    Renders pixel image on the left and ASCII preview on the right
    with a draggable divider.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_pixmap = None
        self.ascii_pixmap = None
        self.split_ratio = 0.5
        self.is_dragging = False
        self.setMouseTracking(True)
        self.setMinimumSize(320, 240)

    def set_original_pixmap(self, pixmap):
        self.original_pixmap = pixmap
        self.update()

    def set_ascii_pixmap(self, pixmap):
        self.ascii_pixmap = pixmap
        self.update()

    def _image_rect(self):
        widget_w = self.width()
        widget_h = self.height()
        img_w = self.original_pixmap.width()
        img_h = self.original_pixmap.height()
        scale = min(widget_w / img_w, widget_h / img_h)
        draw_w = int(img_w * scale)
        draw_h = int(img_h * scale)
        draw_x = (widget_w - draw_w) // 2
        draw_y = (widget_h - draw_h) // 2
        return draw_x, draw_y, draw_w, draw_h

    def mousePressEvent(self, event):
        if not self.original_pixmap:
            return
        draw_x, _, draw_w, _ = self._image_rect()
        split_x = draw_x + int(self.split_ratio * draw_w)
        if abs(event.position().x() - split_x) < 15:
            self.is_dragging = True

    def mouseMoveEvent(self, event):
        if self.is_dragging and self.original_pixmap:
            draw_x, _, draw_w, _ = self._image_rect()
            rel_x = event.position().x() - draw_x
            new_ratio = rel_x / draw_w
            self.split_ratio = max(0.0, min(1.0, new_ratio))
            self.update()
        elif self.original_pixmap:
            draw_x, _, draw_w, _ = self._image_rect()
            split_x = draw_x + int(self.split_ratio * draw_w)
            if abs(event.position().x() - split_x) < 15:
                self.setCursor(Qt.SplitHCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self.is_dragging = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self.original_pixmap or self.original_pixmap.isNull():
            painter.setPen(QColor("#808080"))
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "No image loaded.\nDrop or select an image file to begin.",
            )
            painter.end()
            return

        draw_x, draw_y, draw_w, draw_h = self._image_rect()
        target_rect = QRect(draw_x, draw_y, draw_w, draw_h)
        split_x = draw_x + int(self.split_ratio * draw_w)

        # 1. Left clipping (Original)
        painter.save()
        left_clip = QRect(draw_x, draw_y, max(0, split_x - draw_x), draw_h)
        painter.setClipRect(left_clip)
        painter.drawPixmap(target_rect, self.original_pixmap)
        painter.restore()

        # 2. Right clipping (ASCII Rendered)
        painter.save()
        right_clip = QRect(split_x, draw_y, max(0, draw_x + draw_w - split_x), draw_h)
        painter.setClipRect(right_clip)

        if self.ascii_pixmap and not self.ascii_pixmap.isNull():
            painter.drawPixmap(target_rect, self.ascii_pixmap)
        else:
            painter.fillRect(right_clip, QColor("#151515"))
            painter.setPen(QColor("#555555"))
            painter.drawText(right_clip, Qt.AlignCenter, "Generate ASCII\nto compare")

        painter.restore()

        # 3. Slider line & handle
        painter.setPen(QPen(QColor("#007acc"), 2))
        painter.drawLine(split_x, draw_y, split_x, draw_y + draw_h)

        handle_y = draw_y + draw_h // 2
        painter.setBrush(QColor("#007acc"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(split_x, handle_y), 8, 8)
        painter.end()
