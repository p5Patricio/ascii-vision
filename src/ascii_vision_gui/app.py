"""Entry wiring for the ASCII Vision GUI application."""

import sys
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from ascii_vision.resources import bundled_asset_path

from ascii_vision_gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ASCII Vision")
    app.setOrganizationName("Symmetrical Code")
    icon = bundled_asset_path("icon.png")
    if icon:
        app.setWindowIcon(QIcon(icon))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
