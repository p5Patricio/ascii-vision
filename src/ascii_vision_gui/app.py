import os
import sys
import numpy as np
from PIL import Image

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QSlider, QComboBox, QCheckBox, QPushButton,
    QPlainTextEdit, QFileDialog, QProgressBar, QMessageBox, QSplitter,
    QStatusBar, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QSize, QRect, QRectF, QPoint, QTimer
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QFont, QFontDatabase

from ascii_vision.glyph_cache import GlyphCache, CHARSET_PRESETS
from ascii_vision.engine import ConversionEngine
from ascii_vision.config import ConfigManager
from ascii_vision_gui.worker import ConversionWorker

QSS_STYLE = """
QMainWindow {
    background-color: #1e1e1e;
}
QWidget {
    color: #d4d4d4;
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 12px;
}
QFrame#leftPanel {
    background-color: #252526;
    border-right: 1px solid #2d2d2d;
    max-width: 320px;
    min-width: 280px;
}
QFrame#dropZone {
    border: 2px dashed #3c3c3c;
    border-radius: 6px;
    background-color: #1e1e1e;
    min-height: 100px;
}
QFrame#dropZone:hover {
    border-color: #007acc;
    background-color: #252526;
}
QLabel#titleLabel {
    font-weight: bold;
    font-size: 14px;
    color: #ffffff;
}
QLabel#sectionLabel {
    font-weight: bold;
    color: #858585;
    text-transform: uppercase;
    font-size: 10px;
    margin-top: 10px;
    margin-bottom: 5px;
}
QPushButton {
    background-color: #0e639c;
    color: #ffffff;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #1177bb;
}
QPushButton:pressed {
    background-color: #0c5281;
}
QPushButton#generateBtn {
    background-color: #0e639c;
}
QPushButton#generateBtn:hover {
    background-color: #1177bb;
}
QPushButton#generateBtn[running="true"] {
    background-color: #ca5010;
}
QPushButton#generateBtn[running="true"]:hover {
    background-color: #e81123;
}
QComboBox, QSpinBox {
    background-color: #3c3c3c;
    border: 1px solid #2d2d2d;
    border-radius: 4px;
    padding: 4px;
    color: #ffffff;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #2d2d30;
    color: #d4d4d4;
    selection-background-color: #007acc;
}
QSlider::groove:horizontal {
    border: 1px solid #3c3c3c;
    height: 4px;
    background: #3c3c3c;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #007acc;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #0098ff;
}
QCheckBox {
    spacing: 5px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    background-color: #3c3c3c;
    border: 1px solid #2d2d2d;
    border-radius: 2px;
}
QCheckBox::indicator:checked {
    background-color: #007acc;
    border-color: #007acc;
}
QPlainTextEdit {
    background-color: #1e1e1e;
    border: 1px solid #2d2d2d;
    color: #d4d4d4;
}
QScrollBar:vertical {
    border: none;
    background: #1e1e1e;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #424242;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #4f4f4f;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
QStatusBar {
    background-color: #007acc;
    color: #ffffff;
}
"""

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
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                self.fileDropped.emit(file_path)
                break

    def mousePressEvent(self, event):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image File", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
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

    def mousePressEvent(self, event):
        if not self.original_pixmap:
            return
        
        widget_w = self.width()
        widget_h = self.height()
        img_w = self.original_pixmap.width()
        img_h = self.original_pixmap.height()
        scale = min(widget_w / img_w, widget_h / img_h)
        draw_w = int(img_w * scale)
        draw_x = (widget_w - draw_w) // 2
        
        split_x = draw_x + int(self.split_ratio * draw_w)
        
        if abs(event.position().x() - split_x) < 15:
            self.is_dragging = True

    def mouseMoveEvent(self, event):
        if self.is_dragging and self.original_pixmap:
            widget_w = self.width()
            widget_h = self.height()
            img_w = self.original_pixmap.width()
            img_h = self.original_pixmap.height()
            scale = min(widget_w / img_w, widget_h / img_h)
            draw_w = int(img_w * scale)
            draw_x = (widget_w - draw_w) // 2
            
            rel_x = event.position().x() - draw_x
            new_ratio = rel_x / draw_w
            self.split_ratio = max(0.0, min(1.0, new_ratio))
            self.update()
        elif self.original_pixmap:
            widget_w = self.width()
            widget_h = self.height()
            img_w = self.original_pixmap.width()
            img_h = self.original_pixmap.height()
            scale = min(widget_w / img_w, widget_h / img_h)
            draw_w = int(img_w * scale)
            draw_x = (widget_w - draw_w) // 2
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
            painter.drawText(self.rect(), Qt.AlignCenter, "No image loaded.\nDrop or select an image file to begin.")
            painter.end()
            return
            
        widget_w = self.width()
        widget_h = self.height()
        img_w = self.original_pixmap.width()
        img_h = self.original_pixmap.height()
        
        scale = min(widget_w / img_w, widget_h / img_h)
        draw_w = int(img_w * scale)
        draw_h = int(img_h * scale)
        draw_x = (widget_w - draw_w) // 2
        draw_y = (widget_h - draw_h) // 2
        
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ASCII Vision")
        self.resize(1100, 750)
        self.setStyleSheet(QSS_STYLE)
        
        self.image_path = None
        self.original_pixmap = None
        self.ascii_text = ""
        self.engine = None
        self.worker = None
        self.thread = None
        
        # Prepopulate font system fallback
        self.load_bundled_font()
        
        self.init_ui()
        
        # Load defaults
        self.on_preset_changed(self.preset_combo.currentText())

    def load_bundled_font(self):
        package_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(package_dir))
        font_file = os.path.abspath(os.path.join(project_root, "assets", "fonts", "JetBrainsMono-Regular.ttf"))
        if os.path.exists(font_file):
            QFontDatabase.addApplicationFont(font_file)

    def init_ui(self):
        # Master splitter
        main_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(main_splitter)
        
        # Left Panel (Settings)
        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(12)
        
        title = QLabel("ASCII Vision")
        title.setObjectName("titleLabel")
        left_layout.addWidget(title)
        
        # Drag & Drop Zone
        self.drop_zone = DropZoneWidget()
        self.drop_zone.fileDropped.connect(self.load_image)
        left_layout.addWidget(self.drop_zone)
        
        # Settings Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(12)
        
        # Preset control
        scroll_layout.addWidget(QLabel("Preset", objectName="sectionLabel"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Balanced", "Fast", "High Quality", "Maximum Quality", "Custom"])
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        scroll_layout.addWidget(self.preset_combo)
        
        # Scale control
        scroll_layout.addWidget(QLabel("Resolution Scale", objectName="sectionLabel"))
        scale_container = QHBoxLayout()
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(10, 200)
        self.scale_slider.setValue(100)
        self.scale_label = QLabel("100%")
        self.scale_slider.valueChanged.connect(lambda v: self.scale_label.setText(f"{v}%"))
        scale_container.addWidget(self.scale_slider)
        scale_container.addWidget(self.scale_label)
        scroll_layout.addLayout(scale_container)
        
        # Metric control
        scroll_layout.addWidget(QLabel("Similarity Metric", objectName="sectionLabel"))
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["MSE", "SSIM", "Brightness"])
        scroll_layout.addWidget(self.metric_combo)
        
        # Charset control
        scroll_layout.addWidget(QLabel("Character Set", objectName="sectionLabel"))
        self.charset_combo = QComboBox()
        self.charset_combo.addItems(["ASCII", "Shades", "Blocks", "Braille", "Custom"])
        self.charset_combo.currentTextChanged.connect(self.on_charset_changed)
        scroll_layout.addWidget(self.charset_combo)
        
        self.custom_charset_label = QLabel("Custom Char Set Matrix")
        self.custom_charset_input = QPlainTextEdit()
        self.custom_charset_input.setPlaceholderText("e.g.  .o(O#")
        self.custom_charset_input.setMaximumHeight(50)
        self.custom_charset_input.hide()
        self.custom_charset_label.hide()
        scroll_layout.addWidget(self.custom_charset_label)
        scroll_layout.addWidget(self.custom_charset_input)
        
        # Aspect Ratio overrides
        scroll_layout.addWidget(QLabel("Character Aspect Ratio Override", objectName="sectionLabel"))
        self.aspect_auto_cb = QCheckBox("Use Dynamic Font Metrics")
        self.aspect_auto_cb.setChecked(True)
        
        aspect_container = QHBoxLayout()
        self.aspect_slider = QSlider(Qt.Horizontal)
        self.aspect_slider.setRange(10, 200)  # Maps to 0.1 - 2.0
        self.aspect_slider.setValue(50)       # 0.5
        self.aspect_slider.setEnabled(False)
        self.aspect_label = QLabel("0.5")
        self.aspect_label.setEnabled(False)
        self.aspect_slider.valueChanged.connect(lambda v: self.aspect_label.setText(f"{v/100:.2f}"))
        
        self.aspect_auto_cb.toggled.connect(lambda checked: self.aspect_slider.setEnabled(not checked))
        self.aspect_auto_cb.toggled.connect(lambda checked: self.aspect_label.setEnabled(not checked))
        
        aspect_container.addWidget(self.aspect_slider)
        aspect_container.addWidget(self.aspect_label)
        
        scroll_layout.addWidget(self.aspect_auto_cb)
        scroll_layout.addLayout(aspect_container)
        
        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll)
        
        # Generate / Action Button
        self.generate_btn = QPushButton("Generate ASCII")
        self.generate_btn.setObjectName("generateBtn")
        self.generate_btn.setProperty("running", "false")
        self.generate_btn.clicked.connect(self.on_generate_clicked)
        left_layout.addWidget(self.generate_btn)
        
        main_splitter.addWidget(left_panel)
        
        # Center & Right Panel
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Notification Banner
        self.notification_banner = QLabel()
        self.notification_banner.setStyleSheet("background-color: #ca5010; color: #ffffff; padding: 8px; font-weight: bold; border-bottom: 1px solid #ca5010;")
        self.notification_banner.setAlignment(Qt.AlignCenter)
        self.notification_banner.hide()
        right_layout.addWidget(self.notification_banner)
        
        # Split Slider View
        center_splitter = QSplitter(Qt.Vertical)
        right_layout.addWidget(center_splitter)
        
        self.comparison_widget = ComparisonWidget()
        center_splitter.addWidget(self.comparison_widget)
        
        # Bottom Monospace Editor and Controls
        bottom_panel = QFrame()
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        bottom_layout.setSpacing(8)
        
        # Monospace Text Editor
        self.output_editor = QPlainTextEdit()
        self.output_editor.setReadOnly(True)
        # Apply standard monospace font settings
        mono_font = QFont("JetBrains Mono", 10)
        if not QFontDatabase.isFixedPitch(mono_font.family()):
            mono_font.setStyleHint(QFont.Monospace)
        self.output_editor.setFont(mono_font)
        bottom_layout.addWidget(self.output_editor)
        
        # Bottom Toolbar
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(12)
        
        self.copy_btn = QPushButton("Copy to Clipboard")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        toolbar_layout.addWidget(self.copy_btn)
        
        self.wrap_cb = QCheckBox("Word Wrap")
        self.wrap_cb.toggled.connect(self.on_wrap_toggled)
        toolbar_layout.addWidget(self.wrap_cb)
        
        toolbar_layout.addStretch()
        
        toolbar_layout.addWidget(QLabel("Font size:"))
        self.font_size_slider = QSlider(Qt.Horizontal)
        self.font_size_slider.setRange(4, 28)
        self.font_size_slider.setValue(10)
        self.font_size_slider.setFixedWidth(100)
        self.font_size_slider.valueChanged.connect(self.update_editor_font)
        toolbar_layout.addWidget(self.font_size_slider)
        
        toolbar_layout.addWidget(QLabel("Font family:"))
        self.font_family_combo = QComboBox()
        self.populate_fixed_pitch_fonts()
        self.font_family_combo.currentTextChanged.connect(self.update_editor_font)
        toolbar_layout.addWidget(self.font_family_combo)
        
        bottom_layout.addLayout(toolbar_layout)
        center_splitter.addWidget(bottom_panel)
        
        # Add Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background: #252526; border: none; height: 6px; border-radius: 3px; } QProgressBar::chunk { background: #007acc; border-radius: 3px; }")
        self.progress_bar.setTextVisible(False)
        right_layout.addWidget(self.progress_bar)
        
        main_splitter.addWidget(right_panel)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.status_chars = QLabel("Characters: 0")
        self.status_dims = QLabel("Dimensions: 0x0")
        self.status_time = QLabel("Time: 0.0s")
        
        self.status_bar.addPermanentWidget(self.status_chars)
        self.status_bar.addPermanentWidget(self.status_dims)
        self.status_bar.addPermanentWidget(self.status_time)
        
        # Set Splitter Ratios
        main_splitter.setSizes([300, 800])
        center_splitter.setSizes([450, 250])

    def show_notification(self, message: str):
        self.notification_banner.setText(message)
        self.notification_banner.show()
        QTimer.singleShot(6000, self.notification_banner.hide)

    def populate_fixed_pitch_fonts(self):
        families = QFontDatabase.families()
        fixed_fonts = [f for f in families if QFontDatabase.isFixedPitch(f)]
        
        # Add JetBrains Mono as fallback if not auto-populated
        if "JetBrains Mono" not in fixed_fonts:
            fixed_fonts.insert(0, "JetBrains Mono")
            
        self.font_family_combo.addItems(fixed_fonts)
        
        # Set selection to JetBrains Mono if available
        idx = self.font_family_combo.findText("JetBrains Mono")
        if idx != -1:
            self.font_family_combo.setCurrentIndex(idx)

    def update_editor_font(self):
        font_family = self.font_family_combo.currentText()
        font_size = self.font_size_slider.value()
        
        # Non-blocking font validation check
        available = QFontDatabase.families()
        if font_family not in available:
            self.show_notification(f"Font '{font_family}' is missing. Falling back to JetBrains Mono.")
            font_family = "JetBrains Mono"
            
        font = QFont(font_family, font_size)
        self.output_editor.setFont(font)
        
        # Re-render split preview when font choice affects aspect calculations
        if self.ascii_text and self.original_pixmap:
            self.on_ascii_text_ready(self.ascii_text, self.cols, self.rows)

    def on_wrap_toggled(self, checked):
        if checked:
            self.output_editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        else:
            self.output_editor.setLineWrapMode(QPlainTextEdit.NoWrap)

    def load_image(self, file_path):
        if not os.path.exists(file_path):
            return
            
        self.image_path = file_path
        self.original_pixmap = QPixmap(file_path)
        self.comparison_widget.set_original_pixmap(self.original_pixmap)
        self.comparison_widget.set_ascii_pixmap(None)
        self.output_editor.setPlainText("")
        self.ascii_text = ""
        
        self.status_bar.showMessage(f"Loaded image: {os.path.basename(file_path)}", 3000)

    def on_preset_changed(self, preset_name):
        if preset_name == "Custom":
            self.scale_slider.setEnabled(True)
            self.metric_combo.setEnabled(True)
            self.charset_combo.setEnabled(True)
            return
            
        # Standard configuration maps
        presets = {
            "Fast": {"scale": 40, "metric": "Brightness", "charset": "shades"},
            "Balanced": {"scale": 80, "metric": "MSE", "charset": "ascii"},
            "High Quality": {"scale": 100, "metric": "SSIM", "charset": "ascii"},
            "Maximum Quality": {"scale": 150, "metric": "SSIM", "charset": "braille"}
        }
        
        settings = presets.get(preset_name, presets["Balanced"])
        
        # Temporarily disable signals to avoid recursive changes
        self.scale_slider.setValue(settings["scale"])
        self.metric_combo.setCurrentText(settings["metric"])
        self.charset_combo.setCurrentText(settings["charset"])
        
        # Disable controls to enforce preset choices
        self.scale_slider.setEnabled(False)
        self.metric_combo.setEnabled(False)
        self.charset_combo.setEnabled(False)

    def on_charset_changed(self, charset_name):
        if charset_name == "Custom":
            self.custom_charset_label.show()
            self.custom_charset_input.show()
        else:
            self.custom_charset_label.hide()
            self.custom_charset_input.hide()

    def optimize_settings_automatically(self):
        changes = []
        
        # 1. Downgrade Resolution Scale to max 50%
        if self.scale_slider.value() > 50:
            self.scale_slider.setEnabled(True)
            self.scale_slider.setValue(50)
            changes.append("Downscaled resolution to 50%")
            
        # 2. Downgrade Metric from SSIM to MSE
        if self.metric_combo.currentText() == "SSIM":
            self.metric_combo.setEnabled(True)
            self.metric_combo.setCurrentText("MSE")
            changes.append("Downgraded metric from SSIM to MSE")
            
        # 3. Simplify glyph sets if Braille
        if self.charset_combo.currentText() == "Braille":
            self.charset_combo.setEnabled(True)
            self.charset_combo.setCurrentText("Shades")
            changes.append("Switched glyph set to Shades")
            
        # Automatically switch to Custom preset to reflect optimization changes
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentText("Custom")
        self.preset_combo.blockSignals(False)
        
        explanation = "Optimization adjustments applied:\n" + "\n".join(f"- {c}" for c in changes)
        QMessageBox.information(self, "Performance Optimized", explanation)

    def check_workload(self, img_width, img_height, cols) -> str:
        """
        Calculates FLOP workload estimation. Prompts user if computations are heavy.
        """
        # Read parameters
        charset_name = self.charset_combo.currentText()
        if charset_name == "Custom":
            charset_str = self.custom_charset_input.toPlainText() or " "
        else:
            charset_str = CHARSET_PRESETS.get(charset_name.lower(), "ascii")
            
        font_path = "assets/fonts/JetBrainsMono-Regular.ttf"
        font_size = 12
        
        # Resolve config manager
        cm = ConfigManager()
        resolved_font_path = cm.resolve_font_path(font_path)
        
        # Create GlyphCache temporarily to measure aspect ratio and count glyphs
        temp_cache = GlyphCache(resolved_font_path, font_size, charset_str)
        
        preset_sizes = {
            "Fast": (8, 8),
            "Balanced": (10, 10),
            "High Quality": (10, 10),
            "Maximum Quality": None,
            "Custom": (10, 10)
        }
        g_size = preset_sizes.get(self.preset_combo.currentText(), (10, 10))
        temp_cache.render(target_size=g_size, as_float=True)
        
        # Create temp ConversionEngine for workload estimation
        temp_engine = ConversionEngine(temp_cache, metric=self.metric_combo.currentText())
        
        est = temp_engine.estimate_workload(img_width, img_height, cols)
        comparisons = est["total_blocks"] * est["num_glyphs"]
        
        is_ssim = (self.metric_combo.currentText() == "SSIM")
        is_high_res = (g_size is None or g_size[0] * g_size[1] > 100)
        
        # Workload thresholds triggering dialog
        if comparisons > 10000000 or (is_ssim and is_high_res):
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Heavy Workload Warning")
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText(
                f"High computational complexity detected.\n\n"
                f"Estimated Comparisons: {comparisons:,}\n"
                f"Complexity: {est['complexity']}\n\n"
                f"Proceeding may slow down your system. Would you like to proceed, automatically optimize settings, or cancel?"
            )
            continue_btn = msg_box.addButton("Continue", QMessageBox.AcceptRole)
            optimize_btn = msg_box.addButton("Optimize Automatically", QMessageBox.AcceptRole)
            cancel_btn = msg_box.addButton("Cancel", QMessageBox.RejectRole)
            
            msg_box.exec()
            clicked = msg_box.clickedButton()
            
            if clicked == cancel_btn:
                return "cancel"
            elif clicked == optimize_btn:
                return "optimize"
            else:
                return "continue"
                
        return "continue"

    def on_generate_clicked(self):
        if self.worker:
            # Active worker exists -> click acts as Cancel request
            self.generate_btn.setEnabled(False)
            self.generate_btn.setText("Cancelling...")
            self.worker.cancel()
            return
            
        if not self.image_path or not self.original_pixmap:
            QMessageBox.warning(self, "No Image Loaded", "Please load an image file first.")
            return
            
        # Parse settings
        scale = self.scale_slider.value()
        metric = self.metric_combo.currentText()
        charset_name = self.charset_combo.currentText()
        
        if charset_name == "Custom":
            charset_str = self.custom_charset_input.toPlainText()
            if not charset_str:
                QMessageBox.warning(self, "Empty Charset", "Please specify custom characters.")
                return
        else:
            charset_str = CHARSET_PRESETS.get(charset_name.lower(), charset_name)
            
        # Determine number of columns based on scale and original image width
        original_w = self.original_pixmap.width()
        original_h = self.original_pixmap.height()
        
        # Approximate columns target
        glyph_w = 8 if self.preset_combo.currentText() == "Fast" else 10
        target_cols = max(10, int((original_w / glyph_w) * (scale / 100.0)))
        
        # Workload check
        decision = self.check_workload(original_w, original_h, target_cols)
        if decision == "cancel":
            return
        elif decision == "optimize":
            self.optimize_settings_automatically()
            # Re-read settings after optimization
            scale = self.scale_slider.value()
            metric = self.metric_combo.currentText()
            charset_name = self.charset_combo.currentText()
            charset_str = CHARSET_PRESETS.get(charset_name.lower(), charset_name)
            target_cols = max(10, int((original_w / glyph_w) * (scale / 100.0)))
            
        # Build configuration dict
        config = {
            "font_path": "assets/fonts/JetBrainsMono-Regular.ttf",
            "font_size": 12,
            "charset": charset_str,
            "preset": self.preset_combo.currentText() if self.preset_combo.currentText() != "Custom" else "Balanced",
            "metric": metric,
            "columns": target_cols,
            "preprocessing": {
                "brightness": 1.0,
                "contrast": 1.0,
                "sharpening": 0.0,
                "gaussian_blur": 0.0
            }
        }
        
        # Initialize ConfigManager
        cm = ConfigManager()
        try:
            cm.set_config(config)
        except Exception as e:
            QMessageBox.critical(self, "Configuration Error", f"Failed to initialize configuration: {e}")
            return
            
        # Build GlyphCache & ConversionEngine
        glyph_cache = GlyphCache(
            font_path=cm.config["font_path"],
            font_size=cm.config["font_size"],
            charset=cm.config["charset"]
        )
        
        # Apply aspect ratio override if unchecked
        if not self.aspect_auto_cb.isChecked():
            glyph_cache.char_aspect_ratio = self.aspect_slider.value() / 100.0
            
        preset_sizes = {
            "Fast": (8, 8),
            "Balanced": (10, 10),
            "High Quality": (10, 10),
            "Maximum Quality": None,
            "Custom": (10, 10)
        }
        g_size = preset_sizes.get(self.preset_combo.currentText(), (10, 10))
        
        # Instantiate engine
        try:
            engine = ConversionEngine(
                glyph_cache,
                metric=metric,
                preset=self.preset_combo.currentText() if self.preset_combo.currentText() != "Custom" else "Balanced",
                preprocessing=config["preprocessing"]
            )
            # Re-apply resolution size constraint
            engine.glyph_size = g_size
            engine.glyph_cache.render(target_size=g_size, as_float=True)
            self.engine = engine
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"Failed to start conversion engine: {e}")
            return
            
        # Lock UI
        self.set_ui_enabled(False)
        self.generate_btn.setText("Cancel Conversion")
        self.generate_btn.setProperty("running", "true")
        self.generate_btn.style().polish(self.generate_btn)
        
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # Setup worker thread
        self.thread = QThread()
        self.worker = ConversionWorker(self.image_path, self.engine, config)
        self.worker.moveToThread(self.thread)
        
        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.eta.connect(self.on_eta)
        self.worker.warning.connect(self.on_warning)
        self.worker.error.connect(self.on_error)
        self.worker.result.connect(self.on_result)
        self.worker.finished.connect(self.on_finished)
        self.worker.finished.connect(self.thread.quit)
        
        # Start thread
        self.thread.start()

    def set_ui_enabled(self, enabled):
        self.preset_combo.setEnabled(enabled)
        # Only enable settings controls if Custom preset is active
        if enabled and self.preset_combo.currentText() == "Custom":
            self.scale_slider.setEnabled(True)
            self.metric_combo.setEnabled(True)
            self.charset_combo.setEnabled(True)
        else:
            self.scale_slider.setEnabled(False)
            self.metric_combo.setEnabled(False)
            self.charset_combo.setEnabled(False)
            
        self.aspect_auto_cb.setEnabled(enabled)
        if enabled and not self.aspect_auto_cb.isChecked():
            self.aspect_slider.setEnabled(True)
        else:
            self.aspect_slider.setEnabled(False)
            
        self.drop_zone.setEnabled(enabled)

    @Slot(int, str)
    def on_progress(self, val, stage):
        self.progress_bar.setValue(val)
        self.status_bar.showMessage(f"Processing: {stage} ({val}%)")

    @Slot(str, str)
    def on_eta(self, eta_str, elapsed_str):
        self.status_time.setText(f"Elapsed: {elapsed_str} | ETA: {eta_str}")

    @Slot(str)
    def on_warning(self, msg):
        self.show_notification(f"Warning: {msg}")

    @Slot(str)
    def on_error(self, err_msg):
        QMessageBox.critical(self, "Conversion Error", f"An error occurred: {err_msg}")
        self.status_bar.showMessage("Conversion failed", 3000)

    @Slot(str, int, int)
    def on_result(self, ascii_text, cols, rows):
        self.ascii_text = ascii_text
        self.cols = cols
        self.rows = rows
        self.output_editor.setPlainText(ascii_text)
        
        # Update permanent labels
        char_count = len(ascii_text) - ascii_text.count("\n")
        self.status_chars.setText(f"Characters: {char_count:,}")
        self.status_dims.setText(f"Dimensions: {cols}x{rows}")
        
        # Render split slider preview
        self.on_ascii_text_ready(ascii_text, cols, rows)
        
        self.status_bar.showMessage("Conversion complete!", 3000)

    def on_ascii_text_ready(self, text, cols, rows):
        if not self.original_pixmap:
            return
            
        # Draw the ascii pixmap with matching dimensions
        ascii_pix = self.render_ascii_to_pixmap(text, self.original_pixmap.size(), cols, rows)
        self.comparison_widget.set_ascii_pixmap(ascii_pix)

    def render_ascii_to_pixmap(self, text: str, size: QSize, cols: int, rows: int) -> QPixmap:
        pixmap = QPixmap(size)
        pixmap.fill(QColor("#151515"))
        
        painter = QPainter(pixmap)
        font_family = self.font_family_combo.currentText()
        cell_w = size.width() / cols
        cell_h = size.height() / rows
        
        font = QFont(font_family)
        font.setPixelSize(max(1, int(cell_h)))
        painter.setFont(font)
        
        # Render style decoration based on metric choice
        if self.metric_combo.currentText() == "SSIM":
            painter.setPen(QColor("#a3e635"))  # Lime/green text
        elif self.metric_combo.currentText() == "Brightness":
            painter.setPen(QColor("#60a5fa"))  # Blue text
        else:
            painter.setPen(QColor("#d4d4d4"))  # Classic light gray text
            
        lines = text.split("\n")
        for r, line in enumerate(lines):
            if r >= rows:
                break
            for c, char in enumerate(line):
                if c >= cols:
                    break
                rect = QRectF(c * cell_w, r * cell_h, cell_w, cell_h)
                painter.drawText(rect, Qt.AlignCenter, char)
                
        painter.end()
        return pixmap

    @Slot()
    def on_finished(self):
        # Unlock UI
        self.set_ui_enabled(True)
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate ASCII")
        self.generate_btn.setProperty("running", "false")
        self.generate_btn.style().polish(self.generate_btn)
        
        self.progress_bar.setVisible(False)
        
        # Clean up background thread
        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
        self.worker = None

    def copy_to_clipboard(self):
        if not self.ascii_text:
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(self.ascii_text)
        self.status_bar.showMessage("Copied to clipboard!", 2000)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
