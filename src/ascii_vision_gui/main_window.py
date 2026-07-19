"""Main window for the ASCII Vision GUI."""

import os
import numpy as np
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QSlider,
    QComboBox,
    QCheckBox,
    QPushButton,
    QPlainTextEdit,
    QTextEdit,
    QProgressBar,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QScrollArea,
    QFileDialog,
    QSpinBox,
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QSize, QTimer
from PySide6.QtGui import QPixmap, QFont, QFontDatabase

from ascii_vision.glyph_cache import GlyphCache, CHARSET_PRESETS
from ascii_vision.engine import ConversionEngine
from ascii_vision.config import ConfigManager
from ascii_vision.exporter import to_html, to_txt, ExportManager
from ascii_vision_gui.worker import ConversionWorker, WebcamWorker
from ascii_vision_gui.widgets import DropZoneWidget, ComparisonWidget
from ascii_vision_gui.rendering import AsciiToPixmap
from ascii_vision_gui.style import QSS_STYLE


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
        self.export_manager = ExportManager()
        self.webcam_worker = None
        self.webcam_thread = None
        self.webcam_provider = None

        self._load_bundled_font()
        self._init_ui()
        self.on_preset_changed(self.preset_combo.currentText())

    def _load_bundled_font(self):
        package_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(package_dir))
        font_file = os.path.abspath(
            os.path.join(project_root, "assets", "fonts", "JetBrainsMono-Regular.ttf")
        )
        if os.path.exists(font_file):
            QFontDatabase.addApplicationFont(font_file)

    def _init_ui(self):
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

        self.drop_zone = DropZoneWidget()
        self.drop_zone.fileDropped.connect(self.load_image)
        left_layout.addWidget(self.drop_zone)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(12)

        # Profile selector
        scroll_layout.addWidget(QLabel("Profile", objectName="sectionLabel"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("Default")
        self.profile_combo.currentTextChanged.connect(self.on_profile_changed)
        scroll_layout.addWidget(self.profile_combo)

        # Preset
        scroll_layout.addWidget(QLabel("Preset", objectName="sectionLabel"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Balanced", "Fast", "High Quality", "Maximum Quality", "Custom"])
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        scroll_layout.addWidget(self.preset_combo)

        # Scale
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

        # Metric
        scroll_layout.addWidget(QLabel("Similarity Metric", objectName="sectionLabel"))
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["MSE", "SSIM", "Brightness"])
        scroll_layout.addWidget(self.metric_combo)

        # Charset
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

        # Aspect ratio
        scroll_layout.addWidget(QLabel("Character Aspect Ratio Override", objectName="sectionLabel"))
        self.aspect_auto_cb = QCheckBox("Use Dynamic Font Metrics")
        self.aspect_auto_cb.setChecked(True)

        aspect_container = QHBoxLayout()
        self.aspect_slider = QSlider(Qt.Horizontal)
        self.aspect_slider.setRange(10, 200)
        self.aspect_slider.setValue(50)
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

        # Color Options
        scroll_layout.addWidget(QLabel("Color Options", objectName="sectionLabel"))
        self.color_mode_cb = QCheckBox("Color Mode")
        scroll_layout.addWidget(self.color_mode_cb)

        bg_container = QHBoxLayout()
        bg_container.addWidget(QLabel("Background:"))
        self.bg_color_combo = QComboBox()
        self.bg_color_combo.addItems(["Black", "White", "Transparent"])
        bg_container.addWidget(self.bg_color_combo)
        scroll_layout.addLayout(bg_container)

        # Streaming controls (webcam preview)
        scroll_layout.addWidget(QLabel("Streaming", objectName="sectionLabel"))

        fps_container = QHBoxLayout()
        fps_container.addWidget(QLabel("Target FPS:"))
        self.fps_spinner = QSpinBox()
        self.fps_spinner.setRange(1, 60)
        self.fps_spinner.setValue(15)
        self.fps_spinner.setToolTip("Target frame rate for live webcam preview")
        fps_container.addWidget(self.fps_spinner)
        fps_container.addStretch()
        scroll_layout.addLayout(fps_container)

        self.adaptive_cb = QCheckBox("Adaptive Quality")
        self.adaptive_cb.setToolTip("Dynamically adjust quality to maintain target FPS")
        scroll_layout.addWidget(self.adaptive_cb)

        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll)

        # Generate Button
        self.generate_btn = QPushButton("Generate ASCII")
        self.generate_btn.setObjectName("generateBtn")
        self.generate_btn.setProperty("running", "false")
        self.generate_btn.clicked.connect(self.on_generate_clicked)
        left_layout.addWidget(self.generate_btn)

        main_splitter.addWidget(left_panel)

        # Right Panel
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.notification_banner = QLabel()
        self.notification_banner.setStyleSheet(
            "background-color: #ca5010; color: #ffffff; padding: 8px; font-weight: bold; border-bottom: 1px solid #ca5010;"
        )
        self.notification_banner.setAlignment(Qt.AlignCenter)
        self.notification_banner.hide()
        right_layout.addWidget(self.notification_banner)

        center_splitter = QSplitter(Qt.Vertical)
        right_layout.addWidget(center_splitter)

        self.comparison_widget = ComparisonWidget()
        center_splitter.addWidget(self.comparison_widget)

        bottom_panel = QFrame()
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        bottom_layout.setSpacing(8)

        self.output_editor = QTextEdit()
        self.output_editor.setReadOnly(True)
        mono_font = QFont("JetBrains Mono", 10)
        if not QFontDatabase.isFixedPitch(mono_font.family()):
            mono_font.setStyleHint(QFont.Monospace)
        self.output_editor.setFont(mono_font)
        bottom_layout.addWidget(self.output_editor)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(12)

        self.save_txt_btn = QPushButton("Save TXT")
        self.save_txt_btn.clicked.connect(lambda: self.save_result("txt"))
        toolbar_layout.addWidget(self.save_txt_btn)

        self.save_html_btn = QPushButton("Save HTML")
        self.save_html_btn.clicked.connect(lambda: self.save_result("html"))
        toolbar_layout.addWidget(self.save_html_btn)

        self.save_svg_btn = QPushButton("Save SVG")
        self.save_svg_btn.clicked.connect(lambda: self.save_result("svg"))
        toolbar_layout.addWidget(self.save_svg_btn)

        self.save_png_btn = QPushButton("Save PNG")
        self.save_png_btn.clicked.connect(lambda: self.save_result("png"))
        toolbar_layout.addWidget(self.save_png_btn)

        self.webcam_btn = QPushButton("Start Webcam")
        self.webcam_btn.setCheckable(True)
        self.webcam_btn.clicked.connect(self.toggle_webcam)
        toolbar_layout.addWidget(self.webcam_btn)

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
        self._populate_fixed_pitch_fonts()
        self.font_family_combo.currentTextChanged.connect(self.update_editor_font)
        toolbar_layout.addWidget(self.font_family_combo)

        bottom_layout.addLayout(toolbar_layout)
        center_splitter.addWidget(bottom_panel)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background: #252526; border: none; height: 6px; border-radius: 3px; } "
            "QProgressBar::chunk { background: #007acc; border-radius: 3px; }"
        )
        self.progress_bar.setTextVisible(False)
        right_layout.addWidget(self.progress_bar)

        main_splitter.addWidget(right_panel)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_chars = QLabel("Characters: 0")
        self.status_dims = QLabel("Dimensions: 0x0")
        self.status_time = QLabel("Time: 0.0s")

        self.status_bar.addPermanentWidget(self.status_chars)
        self.status_bar.addPermanentWidget(self.status_dims)
        self.status_bar.addPermanentWidget(self.status_time)

        main_splitter.setSizes([300, 800])
        center_splitter.setSizes([450, 250])

        self._refresh_profiles()

    def show_notification(self, message: str):
        self.notification_banner.setText(message)
        self.notification_banner.show()
        QTimer.singleShot(6000, self.notification_banner.hide)

    def _populate_fixed_pitch_fonts(self):
        families = QFontDatabase.families()
        fixed_fonts = [f for f in families if QFontDatabase.isFixedPitch(f)]

        if "JetBrains Mono" not in fixed_fonts:
            fixed_fonts.insert(0, "JetBrains Mono")

        self.font_family_combo.addItems(fixed_fonts)

        idx = self.font_family_combo.findText("JetBrains Mono")
        if idx != -1:
            self.font_family_combo.setCurrentIndex(idx)

    def update_editor_font(self):
        font_family = self.font_family_combo.currentText()
        font_size = self.font_size_slider.value()

        available = QFontDatabase.families()
        if font_family not in available:
            self.show_notification(f"Font '{font_family}' is missing. Falling back to JetBrains Mono.")
            font_family = "JetBrains Mono"

        font = QFont(font_family, font_size)
        self.output_editor.setFont(font)

        if self.ascii_text and self.original_pixmap:
            self.on_ascii_text_ready(self.ascii_text, self.cols, self.rows)

    def on_wrap_toggled(self, checked):
        if checked:
            self.output_editor.setLineWrapMode(QTextEdit.WidgetWidth)
        else:
            self.output_editor.setLineWrapMode(QTextEdit.NoWrap)

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

        presets = {
            "Fast": {"scale": 40, "metric": "Brightness", "charset": "shades"},
            "Balanced": {"scale": 80, "metric": "MSE", "charset": "ascii"},
            "High Quality": {"scale": 100, "metric": "SSIM", "charset": "ascii"},
            "Maximum Quality": {"scale": 150, "metric": "SSIM", "charset": "braille"},
        }

        settings = presets.get(preset_name, presets["Balanced"])

        self.scale_slider.setValue(settings["scale"])
        self.metric_combo.setCurrentText(settings["metric"])
        self.charset_combo.setCurrentText(settings["charset"])

        self.scale_slider.setEnabled(False)
        self.metric_combo.setEnabled(False)
        self.charset_combo.setEnabled(False)

    def _refresh_profiles(self):
        """Reload the profile combo box from ConfigManager."""
        current = self.profile_combo.currentText()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem("Default")
        cm = ConfigManager()
        for name in cm.list_profiles():
            self.profile_combo.addItem(name)
        idx = self.profile_combo.findText(current)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)
        self.profile_combo.blockSignals(False)

    def on_profile_changed(self, profile_name: str):
        """Load a named profile and apply its settings to the UI controls."""
        if profile_name == "Default":
            return
        cm = ConfigManager()
        try:
            cm.load_profile(profile_name)
            self._apply_config_to_ui(cm.config)
        except Exception as e:
            self.show_notification(f"Failed to load profile '{profile_name}': {e}")
            self._refresh_profiles()

    def _apply_config_to_ui(self, config: dict):
        """Mirror a config dict onto the active UI controls."""
        # Preset
        preset = config.get("preset", "Balanced")
        # Map internal preset names to GUI combo labels
        preset_map = {
            "Fast": "Fast",
            "Balanced": "Balanced",
            "High": "High Quality",
            "Max": "Maximum Quality",
            "Custom": "Custom",
        }
        gui_preset = preset_map.get(preset, "Balanced")
        self.preset_combo.setCurrentText(gui_preset)
        self.preset_combo.setEnabled(gui_preset == "Custom")

        # Metric
        metric = config.get("metric", "MSE")
        self.metric_combo.setCurrentText(metric)

        # Charset
        charset = config.get("charset", "ascii")
        charset_map = {
            "ascii": "ASCII",
            "shades": "Shades",
            "blocks": "Blocks",
            "braille": "Braille",
        }
        gui_charset = charset_map.get(charset.lower(), "ASCII")
        self.charset_combo.setCurrentText(gui_charset)
        if gui_charset == "Custom":
            self.custom_charset_label.show()
            self.custom_charset_input.show()
        else:
            self.custom_charset_label.hide()
            self.custom_charset_input.hide()

        # Color mode
        self.color_mode_cb.setChecked(config.get("color_mode", False))

        # Background colour
        bg = config.get("background_color", "Black")
        self.bg_color_combo.setCurrentText(bg)

        self.show_notification(f"Loaded profile with preset '{gui_preset}'")

    def on_charset_changed(self, charset_name):
        if charset_name == "Custom":
            self.custom_charset_label.show()
            self.custom_charset_input.show()
        else:
            self.custom_charset_label.hide()
            self.custom_charset_input.hide()

    def optimize_settings_automatically(self):
        changes = []

        if self.scale_slider.value() > 50:
            self.scale_slider.setEnabled(True)
            self.scale_slider.setValue(50)
            changes.append("Downscaled resolution to 50%")

        if self.metric_combo.currentText() == "SSIM":
            self.metric_combo.setEnabled(True)
            self.metric_combo.setCurrentText("MSE")
            changes.append("Downgraded metric from SSIM to MSE")

        if self.charset_combo.currentText() == "Braille":
            self.charset_combo.setEnabled(True)
            self.charset_combo.setCurrentText("Shades")
            changes.append("Switched glyph set to Shades")

        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentText("Custom")
        self.preset_combo.blockSignals(False)

        explanation = "Optimization adjustments applied:\n" + "\n".join(f"- {c}" for c in changes)
        QMessageBox.information(self, "Performance Optimized", explanation)

    def check_workload(self, img_width, img_height, cols) -> str:
        charset_name = self.charset_combo.currentText()
        if charset_name == "Custom":
            charset_str = self.custom_charset_input.toPlainText() or " "
        else:
            charset_str = CHARSET_PRESETS.get(charset_name.lower(), "ascii")

        font_path = "assets/fonts/JetBrainsMono-Regular.ttf"
        font_size = 12

        cm = ConfigManager()
        resolved_font_path = cm.resolve_font_path(font_path)

        temp_cache = GlyphCache(resolved_font_path, font_size, charset_str)

        preset_sizes = {
            "Fast": (8, 8),
            "Balanced": (10, 10),
            "High Quality": (10, 10),
            "Maximum Quality": None,
            "Custom": (10, 10),
        }
        g_size = preset_sizes.get(self.preset_combo.currentText(), (10, 10))
        temp_cache.render(target_size=g_size, as_float=True)

        temp_engine = ConversionEngine(temp_cache, metric=self.metric_combo.currentText())

        est = temp_engine.estimate_workload(img_width, img_height, cols)
        comparisons = est["total_blocks"] * est["num_glyphs"]

        is_ssim = self.metric_combo.currentText() == "SSIM"
        is_high_res = g_size is None or g_size[0] * g_size[1] > 100

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
            self.generate_btn.setEnabled(False)
            self.generate_btn.setText("Cancelling...")
            self.worker.cancel()
            return

        if not self.image_path or not self.original_pixmap:
            QMessageBox.warning(self, "No Image Loaded", "Please load an image file first.")
            return

        scale = self.scale_slider.value()
        metric = self.metric_combo.currentText()
        charset_name = self.charset_combo.currentText()

        if charset_name == "Custom":
            charset_str = self.custom_charset_input.toPlainText()
            if not charset_str:
                QMessageBox.warning(self, "Empty Charset", "Please specify custom characters.")
                return
            if len(charset_str) > 256:
                QMessageBox.warning(self, "Charset Too Long", "Custom character set must be at most 256 characters.")
                return
        else:
            charset_str = CHARSET_PRESETS.get(charset_name.lower(), charset_name)

        original_w = self.original_pixmap.width()
        original_h = self.original_pixmap.height()

        glyph_w = 8 if self.preset_combo.currentText() == "Fast" else 10
        target_cols = max(10, int((original_w / glyph_w) * (scale / 100.0)))

        decision = self.check_workload(original_w, original_h, target_cols)
        if decision == "cancel":
            return
        elif decision == "optimize":
            self.optimize_settings_automatically()
            scale = self.scale_slider.value()
            metric = self.metric_combo.currentText()
            charset_name = self.charset_combo.currentText()
            charset_str = CHARSET_PRESETS.get(charset_name.lower(), charset_name)
            target_cols = max(10, int((original_w / glyph_w) * (scale / 100.0)))

        config = {
            "font_path": "assets/fonts/JetBrainsMono-Regular.ttf",
            "font_size": 12,
            "charset": charset_str,
            "preset": self.preset_combo.currentText() if self.preset_combo.currentText() != "Custom" else "Balanced",
            "metric": metric,
            "columns": target_cols,
            "color_mode": self.color_mode_cb.isChecked(),
            "background_color": self.bg_color_combo.currentText(),
            "preprocessing": {
                "brightness": 1.0,
                "contrast": 1.0,
                "sharpening": 0.0,
                "gaussian_blur": 0.0,
            },
        }

        cm = ConfigManager()
        try:
            cm.set_config(config)
        except Exception as e:
            QMessageBox.critical(self, "Configuration Error", f"Failed to initialize configuration: {e}")
            return

        glyph_cache = GlyphCache(
            font_path=cm.config["font_path"],
            font_size=cm.config["font_size"],
            charset=cm.config["charset"],
        )

        if not self.aspect_auto_cb.isChecked():
            glyph_cache.char_aspect_ratio = self.aspect_slider.value() / 100.0

        preset_sizes = {
            "Fast": (8, 8),
            "Balanced": (10, 10),
            "High Quality": (10, 10),
            "Maximum Quality": None,
            "Custom": (10, 10),
        }
        g_size = preset_sizes.get(self.preset_combo.currentText(), (10, 10))

        try:
            engine = ConversionEngine(
                glyph_cache,
                metric=metric,
                preset=self.preset_combo.currentText() if self.preset_combo.currentText() != "Custom" else "Balanced",
                preprocessing=config["preprocessing"],
            )
            engine.glyph_size = g_size
            engine.glyph_cache.render(target_size=g_size, as_float=True)
            self.engine = engine
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"Failed to start conversion engine: {e}")
            return

        self.set_ui_enabled(False)
        self.generate_btn.setText("Cancel Conversion")
        self.generate_btn.setProperty("running", "true")
        self.generate_btn.style().polish(self.generate_btn)

        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        self.thread = QThread()
        self.worker = ConversionWorker(self.image_path, self.engine, config)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.eta.connect(self.on_eta)
        self.worker.warning.connect(self.on_warning)
        self.worker.error.connect(self.on_error)
        self.worker.result.connect(self.on_result)
        self.worker.finished.connect(self.on_finished)

        self.thread.start()

    def set_ui_enabled(self, enabled):
        self.preset_combo.setEnabled(enabled)
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
        self.color_mode_cb.setEnabled(enabled)
        self.bg_color_combo.setEnabled(enabled)

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

    @Slot(np.ndarray, int, int, object, str)
    def on_result(self, char_matrix, cols, rows, color_matrix, ascii_text):
        self.char_matrix = char_matrix
        self.ascii_text = ascii_text
        self.cols = cols
        self.rows = rows
        self.color_matrix = color_matrix

        font = self.font_family_combo.currentText()
        size = self.font_size_slider.value()
        bg_color = self.bg_color_combo.currentText()

        if color_matrix is not None:
            html_content = to_html(char_matrix, font, size, color_matrix, bg_color)
            self.output_editor.setHtml(html_content)
        else:
            self.output_editor.setPlainText(ascii_text)

        char_count = len(ascii_text) - ascii_text.count("\n")
        self.status_chars.setText(f"Characters: {char_count:,}")
        self.status_dims.setText(f"Dimensions: {cols}x{rows}")

        self.on_ascii_text_ready(ascii_text, cols, rows)

        self.status_bar.showMessage("Conversion complete!", 3000)

    def on_ascii_text_ready(self, text, cols, rows):
        if not self.original_pixmap:
            return

        renderer = AsciiToPixmap(
            self.font_family_combo.currentText(),
            self.bg_color_combo.currentText(),
        )
        ascii_pix = renderer(
            text,
            self.original_pixmap.size(),
            cols,
            rows,
            getattr(self, "color_matrix", None),
            metric=self.metric_combo.currentText(),
        )
        self.comparison_widget.set_ascii_pixmap(ascii_pix)

    @Slot()
    def on_finished(self):
        self.set_ui_enabled(True)
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate ASCII")
        self.generate_btn.setProperty("running", "false")
        self.generate_btn.style().polish(self.generate_btn)

        self.progress_bar.setVisible(False)

        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
        self.worker = None

    def copy_to_clipboard(self):
        if not self.ascii_text:
            return

        color_mode_active = getattr(self, "color_matrix", None) is not None
        char_matrix = getattr(self, "char_matrix", None)
        if color_mode_active and char_matrix is not None:
            text_to_copy = to_txt(char_matrix, self.color_matrix)
        else:
            text_to_copy = self.ascii_text

        clipboard = QApplication.clipboard()
        clipboard.setText(text_to_copy)
        self.status_bar.showMessage("Copied to clipboard!", 2000)

    def save_result(self, fmt: str):
        char_matrix = getattr(self, "char_matrix", None)
        if char_matrix is None:
            QMessageBox.warning(self, "No Output", "Generate ASCII art before saving.")
            return

        filters = {
            "txt": "Text Files (*.txt)",
            "html": "HTML Files (*.html)",
            "svg": "SVG Files (*.svg)",
            "png": "PNG Images (*.png)",
        }
        ext = fmt
        path, _ = QFileDialog.getSaveFileName(
            self, f"Save {fmt.upper()}", f"ascii_output.{ext}", filters[fmt]
        )
        if not path:
            return

        try:
            self.export_manager.save(
                char_matrix,
                path,
                font_name=self.font_family_combo.currentText(),
                font_size=self.font_size_slider.value(),
                color_matrix=getattr(self, "color_matrix", None),
                bg_color=self.bg_color_combo.currentText(),
                format=fmt,
                font_path=self._resolved_font_path(),
            )
            self.status_bar.showMessage(f"Saved {fmt.upper()}: {path}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", f"Could not save {fmt.upper()}: {exc}")

    def _resolved_font_path(self):
        package_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(package_dir))
        return os.path.abspath(os.path.join(project_root, "assets", "fonts", "JetBrainsMono-Regular.ttf"))

    def toggle_webcam(self, checked: bool):
        if checked:
            # Camera is opened on the worker thread so it does not block the GUI.
            self.webcam_btn.setText("Stop Webcam")
            self.webcam_thread = QThread()
            cache = GlyphCache(self._resolved_font_path(), 10, CHARSET_PRESETS.get("shades", "shades"))
            engine = ConversionEngine(cache, metric="Brightness", preset="Fast")
            self.webcam_worker = WebcamWorker(
                0, engine, cols=40, color_mode=self.color_mode_cb.isChecked(),
                target_fps=self.fps_spinner.value(), adaptive=self.adaptive_cb.isChecked()
            )
            self.webcam_worker.moveToThread(self.webcam_thread)
            self.webcam_thread.started.connect(self.webcam_worker.run)
            self.webcam_worker.frame_ready.connect(self.on_webcam_frame)
            self.webcam_worker.error.connect(self.on_webcam_error)
            self.webcam_worker.ready.connect(self._on_webcam_ready)
            self.webcam_worker.finished.connect(self.webcam_thread.quit)
            self.webcam_thread.start()
        else:
            self.stop_webcam()

    def _on_webcam_ready(self):
        """Called when the webcam camera has been successfully opened in the background."""
        self.status_bar.showMessage("Webcam ready", 2000)

    def on_webcam_frame(self, pixmap: QPixmap):
        self.comparison_widget.set_ascii_pixmap(pixmap)

    def on_webcam_error(self, msg: str):
        self.status_bar.showMessage(f"Webcam error: {msg}", 3000)
        self.stop_webcam()

    def stop_webcam(self):
        if self.webcam_worker:
            self.webcam_worker.cancel()
            self.webcam_worker = None
        if self.webcam_thread:
            self.webcam_thread.quit()
            self.webcam_thread.wait()
            self.webcam_thread = None
        # The WebcamWorker owns the provider and cleans it up in its own
        # ``run()`` ``finally`` block, so there is nothing to release here.
        self.webcam_btn.setChecked(False)
        self.webcam_btn.setText("Start Webcam")

    def closeEvent(self, event):
        self.stop_webcam()
        if self.worker:
            self.worker.cancel()
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        event.accept()
