"""QSS style definitions for the ASCII Vision GUI."""

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
QPlainTextEdit, QTextEdit {
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
