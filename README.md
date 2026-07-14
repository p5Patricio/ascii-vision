# ASCII Vision

ASCII Vision is a professional Python-based desktop application designed to convert images into high-quality ASCII, Unicode, and Braille art. It leverages modern computer vision techniques, vectorized image processing, pre-rendered glyph caching, and structural similarity optimization (like SSIM) to deliver high-fidelity outputs.

## Project Structure
- `src/ascii_vision/`: The headless core conversion library.
  - `frame_provider.py`: Abstraction for static images and frame streams.
  - `glyph_cache.py`: Pre-renders character glyphs into bitmap matrices and calculates dynamic aspect ratio.
  - `metrics.py`: Mathematical comparison algorithms (Brightness, MSE, SSIM).
  - `engine.py`: Image pre-processing filters, scaling, and vectorized matching logic.
  - `exporter.py`: Exporters for TXT, HTML, SVG, PNG, and Clipboard.
  - `config.py`: JSON settings manager with font lookup fallbacks.
- `src/ascii_vision_gui/`: The PySide6 desktop application interface.
  - `worker.py`: Background thread worker utilizing Qt signals/slots for non-blocking UI rendering.
  - `app.py`: Modern dark-themed GUI workbench with a draggable comparison slider.
- `tests/`: Automated unit, integration, and benchmark tests.
- `docs/`: Concept, specifications, and architecture documentation.

---

## Installation & Setup

1. **Prerequisites**: Python 3.13+ (or 3.14)
2. **Setup virtual environment**:
   ```bash
   python -m venv .venv
   ```
3. **Activate virtual environment**:
   - Windows PowerShell:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - Linux/macOS:
     ```bash
     source .venv/bin/activate
     ```
4. **Install in editable mode with dependencies**:
   ```bash
   pip install -e .
   ```

---

## Usage

### 1. Launching the GUI
To start the desktop application:
```bash
python -m ascii_vision_gui.app
```
**Features**:
- Drag and drop images directly into the window.
- Select quality presets or adjust advanced settings (brightness, contrast, metrics).
- Drag the vertical comparison slider in the center panel to wipe between the original image and the ASCII preview.
- View, copy, search, or customize the font of the final ASCII text in the bottom editor.

### 2. Running Tests & Benchmarks
- Run the test suite:
  ```bash
  pytest
  ```
- Run the benchmarks to see MSE vs SSIM timing:
  ```bash
  pytest tests/test_benchmark.py -s
  ```

---

## License
MIT License.
