"""GUI regression tests for bugs found during the pre-release quality audit."""

import time

import numpy as np
import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication, QMessageBox


@pytest.fixture
def window(qapp, monkeypatch):
    from ascii_vision_gui.main_window import MainWindow

    dialogs = []
    for kind in ("critical", "warning", "information"):
        monkeypatch.setattr(QMessageBox, kind, staticmethod(lambda *a, _k=kind, **k: dialogs.append((_k, a[1:3]))))
    win = MainWindow()
    win.check_workload = lambda *a, **k: "continue"
    win.dialogs = dialogs
    yield win
    win.close()


@pytest.fixture
def image_path(tmp_path):
    y, x = np.mgrid[0:120, 0:160]
    arr = np.stack([x * 1.5, y * 2, (x + y)], axis=-1).clip(0, 255).astype(np.uint8)
    path = tmp_path / "gradient.png"
    Image.fromarray(arr).save(path)
    return str(path)


def _wait_for_conversion(window, timeout=30):
    # Pump events by hand: QTest.qWait can starve the worker thread of the GIL.
    deadline = time.time() + timeout
    while time.time() < deadline:
        QApplication.processEvents()
        if window.worker is None and window.thread is None:
            return True
        time.sleep(0.01)
    return False


@pytest.mark.parametrize(
    "preset, charset, metric",
    [
        ("Fast", "Shades", "Brightness"),
        ("Balanced", "ASCII", "MSE"),
        ("High Quality", "ASCII", "SSIM"),
        ("Maximum Quality", "Braille", "SSIM"),
    ],
)
def test_presets_apply_their_charset_and_metric(window, preset, charset, metric):
    # Start from something else so a no-op would be noticed.
    window.preset_combo.setCurrentText("Custom")
    window.charset_combo.setCurrentText("Blocks")
    window.metric_combo.setCurrentText("MSE" if metric != "MSE" else "SSIM")
    window.preset_combo.setCurrentText(preset)
    assert window.charset_combo.currentText() == charset
    assert window.metric_combo.currentText() == metric


@pytest.mark.parametrize("preset", ["Fast", "Balanced", "High Quality", "Maximum Quality"])
def test_every_preset_converts_without_error(window, image_path, preset):
    window.load_image(image_path)
    window.preset_combo.setCurrentText(preset)
    window.generate_btn.click()
    assert _wait_for_conversion(window), "conversion did not finish"
    assert window.dialogs == []
    assert window.ascii_text.strip()


def test_white_background_conversion_succeeds_in_color(window, image_path):
    window.load_image(image_path)
    window.color_mode_cb.setChecked(True)
    window.bg_color_combo.setCurrentText("White")
    window.generate_btn.click()
    assert _wait_for_conversion(window)
    assert window.dialogs == []


def test_exif_rotated_photo_loads_upright(window, tmp_path):
    img = Image.new("RGB", (60, 40), "red")
    exif = img.getexif()
    exif[0x0112] = 6
    path = tmp_path / "rotated.jpg"
    img.save(path, exif=exif)
    window.load_image(str(path))
    assert (window.original_pixmap.width(), window.original_pixmap.height()) == (40, 60)


def test_unreadable_image_reports_an_error(window, tmp_path):
    bad = tmp_path / "broken.png"
    bad.write_bytes(b"\x89PNG\r\n\x1a\n" + b"not really a png")
    window.load_image(str(bad))
    assert window.original_pixmap is None
    assert window.dialogs and window.dialogs[0][0] == "warning"


def test_rapid_webcam_toggling_does_not_crash(window):
    for _ in range(15):
        window.webcam_btn.click()
        QApplication.processEvents()
        if window.webcam_btn.isChecked():
            window.webcam_btn.click()
    QApplication.processEvents()
    assert window.webcam_worker is None and window.webcam_thread is None


def test_profile_with_custom_charset_round_trips_into_the_ui(window):
    config = {"preset": "Balanced", "metric": "MSE", "charset": ".:-=+*#%@", "color_mode": False,
              "background_color": "Black"}
    window._apply_config_to_ui(config)
    assert window.charset_combo.currentText() == "Custom"
    assert window.custom_charset_input.toPlainText() == ".:-=+*#%@"
