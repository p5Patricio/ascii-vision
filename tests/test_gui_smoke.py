"""GUI smoke tests — instantiate MainWindow and exercise controls headlessly."""

import os
import sys

import pytest
from PySide6.QtCore import Qt


@pytest.fixture
def main_window():
    sys.path.insert(0, "src")
    try:
        from PySide6.QtWidgets import QApplication
        from ascii_vision_gui.main_window import MainWindow

        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        yield window
        window.close()
    finally:
        sys.path.remove("src")


def test_main_window_instantiates(main_window):
    assert main_window is not None
    assert main_window.windowTitle() == "ASCII Vision"


def test_save_buttons_exist(main_window):
    buttons = [
        main_window.save_txt_btn,
        main_window.save_html_btn,
        main_window.save_svg_btn,
        main_window.save_png_btn,
    ]
    for btn in buttons:
        assert btn is not None
        assert btn.text().startswith("Save ")


def test_webcam_button_exists(main_window):
    assert main_window.webcam_btn is not None
    assert "Webcam" in main_window.webcam_btn.text()


def test_save_buttons_click_without_result(main_window, monkeypatch):
    """Clicking save before conversion shows a warning without blocking."""
    from PySide6.QtWidgets import QMessageBox
    from unittest.mock import patch

    with patch.object(QMessageBox, "warning", return_value=QMessageBox.Ok):
        main_window.save_html_btn.click()
    assert main_window.save_html_btn is not None


def test_save_html_creates_file(main_window, tmp_path, monkeypatch):
    """Save HTML writes a file when a conversion result is present."""
    import numpy as np
    from PySide6.QtWidgets import QFileDialog
    from unittest.mock import patch

    main_window.char_matrix = np.array([["A", "B"], ["C", "D"]])
    out_path = str(tmp_path / "out.html")

    with patch.object(QFileDialog, "getSaveFileName", return_value=(out_path, "")):
        main_window.save_html_btn.click()

    assert os.path.exists(out_path)
    with open(out_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "<html>" in content or "<!DOCTYPE html>" in content


# ── pytest-qt GUI interaction tests ──────────────────────────────────────────

@pytest.fixture
def gui_window(qtbot):
    """Provide a MainWindow managed by qtbot (no manual QApplication)."""
    sys.path.insert(0, "src")
    try:
        from ascii_vision_gui.main_window import MainWindow
        window = MainWindow()
        window.show()
        qtbot.addWidget(window)
        # Process pending events so the window and scroll area are fully mapped
        qtbot.wait(50)
        yield window
    finally:
        sys.path.remove("src")


def test_streaming_controls_exist(gui_window):
    """FPS spinner and adaptive quality checkbox exist with defaults."""
    spinner = gui_window.fps_spinner
    assert spinner.minimum() == 1
    assert spinner.maximum() == 60
    assert spinner.value() == 15

    cb = gui_window.adaptive_cb
    assert cb.text() == "Adaptive Quality"
    assert cb.isChecked() is False


def test_fps_spinner_can_change(qtbot, gui_window):
    """FPS spinner value can be changed via keyboard."""
    spinner = gui_window.fps_spinner
    assert spinner.value() == 15

    # Arrow key increment
    spinner.setFocus()
    qtbot.keyClick(spinner, Qt.Key_Up)
    assert spinner.value() == 16


def test_adaptive_checkbox_toggle(qtbot, gui_window):
    """Adaptive quality checkbox can be toggled programmatically."""
    cb = gui_window.adaptive_cb
    assert cb.isChecked() is False
    cb.toggle()
    qtbot.wait(50)
    assert cb.isChecked() is True
    cb.toggle()
    qtbot.wait(50)
    assert cb.isChecked() is False


def test_profile_combo_populated(gui_window):
    """Profile combo box is populated with at least 'Default'."""
    combo = gui_window.profile_combo
    assert combo.count() >= 1
    assert combo.currentText() == "Default"


def test_profile_selection_switches(gui_window):
    """Profile combo can be programmatically switched without error."""
    combo = gui_window.profile_combo
    # Switch to Default explicitly — should not raise
    combo.setCurrentText("Default")
    assert combo.currentText() == "Default"


def test_webcam_button_toggle(qtbot, gui_window):
    """Webcam button toggles text synchronously on click."""
    btn = gui_window.webcam_btn
    assert "Start" in btn.text()

    # Click to start — text changes synchronously to "Stop Webcam"
    qtbot.mouseClick(btn, Qt.LeftButton)
    assert "Stop" in btn.text(), "Button text should change to Stop synchronously"

    # Clean up any background thread started by the toggle
    gui_window.stop_webcam()
    assert "Start" in gui_window.webcam_btn.text()


def test_cancel_conversion_flow(qtbot, gui_window):
    """Generate button switches to cancel when a worker is active."""
    from unittest.mock import Mock

    btn = gui_window.generate_btn
    assert "Generate" in btn.text()

    # Simulate active conversion by setting a mock worker
    mock_worker = Mock()
    gui_window.worker = mock_worker

    # Click the button — should trigger cancel path
    qtbot.mouseClick(btn, Qt.LeftButton)
    assert "Cancel" in btn.text(), "Button should show Cancel during conversion"
    assert mock_worker.cancel.called, "worker.cancel() should be called"


def test_gui_imports_and_signals(qtbot, gui_window):
    """Basic structural checks on streaming controls."""
    assert hasattr(gui_window, "fps_spinner")
    assert hasattr(gui_window, "adaptive_cb")

    # Verify the toggle_webcam method accepts streaming params through WebcamWorker
    from ascii_vision_gui.worker import WebcamWorker
    import inspect
    sig = inspect.signature(WebcamWorker.__init__)
    assert "target_fps" in sig.parameters
    assert "adaptive" in sig.parameters
