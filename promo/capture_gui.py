"""Capture the real ASCII Vision window for the landing page.

Loads the comparer scene (site/assets/compare-original.webp), converts it with the High Quality preset in colour and
saves a grab of the window to site/assets/app-screenshot.png. Run promo/gen_compare.py first if the scene changed.

    pip install -e .                 # from the repository root
    python promo/capture_gui.py
"""
import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")      # no window pops up while capturing

from PIL import Image
from PySide6.QtWidgets import QApplication, QMessageBox

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "site", "assets")
SIZE = (1558, 820)
SCALE = 170
SPLIT = 0.5                     # divider position (half original, half ASCII)


def wait_for_conversion(window, timeout=60):
    # Pump events by hand: a plain sleep would starve the worker thread's signals.
    deadline = time.time() + timeout
    while time.time() < deadline:
        QApplication.processEvents()
        if window.worker is None and window.thread is None:
            return True
        time.sleep(0.01)
    return False


def main():
    app = QApplication(sys.argv)
    # A modal dialog would block forever without a display, so report it and carry on.
    for kind in ("critical", "warning", "information"):
        setattr(QMessageBox, kind, staticmethod(lambda *a, _k=kind, **k: print(f"[{_k}]", a[1:3], file=sys.stderr)))
    from ascii_vision_gui.main_window import MainWindow

    window = MainWindow()
    window.check_workload = lambda *a, **k: "continue"       # never show the "heavy workload" dialog
    window.resize(*SIZE)
    window.show()
    out = os.path.join(ASSETS, "app-screenshot.png")
    with tempfile.TemporaryDirectory() as tmp:                # the app re-reads the file on every conversion
        scene = os.path.join(tmp, "scene.png")
        Image.open(os.path.join(ASSETS, "compare-original.webp")).convert("RGB").save(scene)
        window.load_image(scene)
        window.preset_combo.setCurrentText("High Quality")
        window.color_mode_cb.setChecked(True)
        window.scale_slider.setValue(SCALE)
        window.generate_btn.click()
        if not wait_for_conversion(window):
            sys.exit("conversion did not finish")
        window.comparison_widget.split_ratio = SPLIT
        for _ in range(20):
            app.processEvents()
            time.sleep(0.02)
        ok = window.grab().save(out, "PNG")
        window.close()
    if not ok:
        sys.exit("could not save the screenshot")
    print(out, Image.open(out).size, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main()
