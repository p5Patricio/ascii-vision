# ASCII Vision

ASCII Vision is a professional Python-based desktop application designed to convert images into high-quality ASCII, Unicode, and Braille art. It leverages modern computer vision techniques, vectorized image processing, pre-rendered glyph caching, and structural similarity optimization (like SSIM) to deliver high-fidelity outputs.

## Project Structure
- `src/ascii_vision/`: The headless core conversion library.
  - `frame_provider.py`: Abstraction for static images and frame streams.
  - `glyph_cache.py`: Pre-renders character glyphs into bitmap matrices and calculates dynamic aspect ratio.
  - `metrics.py`: Mathematical comparison algorithms (Brightness, MSE, SSIM).
  - `engine.py`: Image pre-processing filters, scaling, vectorized matching, and RGB color quantization.
  - `exporter.py`: Exporters for HTML (optimized with RLE spans), SVG (optimized with RLE tspans), PNG, ANSI TXT, and Clipboard.
  - `config.py`: JSON settings manager with font lookup fallbacks, named profiles and color mode persistence.
  - `resources.py`: Locates the bundled fonts (works from a checkout, a `pip install` and a frozen build) and swaps in a fallback font when the chosen one cannot draw the character set (e.g. Braille).
  - `assets/fonts/`: Bundled JetBrains Mono (+ DejaVu Sans fallback) with their licences.
- `src/ascii_vision_gui/`: The PySide6 desktop application interface.
  - `worker.py`: Background thread worker utilizing Qt signals/slots for non-blocking UI rendering, supporting RGB color calculation.
  - `app.py`: Modern dark-themed GUI workbench with a draggable comparison slider and color controls.
- `tests/`: Automated unit, integration, and benchmark tests.
- `docs/`: Concept, specifications, and architecture documentation.

---

## Installation & Setup

1. **Prerequisites**: Python 3.13+
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

## Features & Usage

### 1. Launching the GUI
To start the desktop application:
```bash
ascii-vision-gui
# or
python -m ascii_vision_gui
```
**GUI Controls**:
- **Drag & Drop Zone**: Load images (PNG, JPG, BMP, WEBP, TIFF, GIF) by dragging them into the left panel.
- **Color Mode**: Check the "Color Mode" box to enable 24-bit RGB rendering.
- **Background Color**: Choose between Black, White, or Transparent backgrounds.
- **Quality Presets**: Choose Fast (Shades, Brightness), Balanced (ASCII, MSE), High Quality (ASCII, SSIM), Maximum Quality (Braille, SSIM), or Custom. Each preset sets its own character set and metric.
- **Split-Screen Slider**: Drag the vertical slider in the center panel to wipe between the original image and the ASCII preview.
- **Bottom Monospace Editor**: Displays the full-resolution ASCII. If Color Mode is enabled, it renders rich HTML colors.
- **Copy to Clipboard**: Copies plain text (monochrome) or ANSI-colored text (if Color Mode is enabled).

### 2. Command-Line Interface
Convert images and videos without launching the GUI:

```bash
# Single image to HTML
ascii-vision --input image.png --output out.html

# SVG output with explicit format override
ascii-vision --input image.png --output out.txt --format svg

# PNG output with color mode
ascii-vision --input image.png --output out.png --color --background Black

# Convert a video to ASCII MP4 (keeps the input's frame rate and audio; H.264 output)
ascii-vision --input video.mp4 --output ascii.mp4 --columns 80

# Save your favourite settings once, reuse them later (flags you type still win)
ascii-vision --save-profile poster --columns 140 --preset "High Quality" --color
ascii-vision --profile poster --input photo.jpg --output photo.png
ascii-vision --list-profiles

ascii-vision --version
```
Presets, metrics and backgrounds are case-insensitive (`--preset "maximum quality"`). Very large requests are refused with a clear message (limit: 400,000 characters per frame).

The CLI is also available as a module:
```bash
python -m ascii_vision --input image.png --output out.html
```

### 3. Optional Video Extras
For PyAV-backed video decoding (better format support), install the optional `video` extra:
```bash
pip install -e ".[video]"
```
This installs `av>=10.0.0`. Without it, OpenCV is used as a fallback.

### 4. Webcam Preview
In the GUI, click **Start Webcam** to preview live ASCII art from the default camera. The preview uses the Fast preset with a small column count for responsiveness. Click **Stop Webcam** or close the window to release the camera.

### 5. Building a Windows installer
The application is Python + Qt, so the installer is built with PyInstaller (bundles Python and every
dependency, users install nothing else) and Inno Setup (creates `ASCII-Vision-Setup-<version>.exe`):
```bash
pip install -e ".[video]" pyinstaller
pyinstaller packaging/ascii-vision.spec --noconfirm
iscc /DAppVersion=0.1.0 packaging\installer.iss      # Windows, Inno Setup 6
```
The `Windows installer` GitHub Actions workflow does all of this on a Windows runner (Actions tab ->
*Run workflow*, or push a `v*` tag to attach the files to a release). Unsigned installers show the
Windows SmartScreen warning; see `packaging/` and the workflow comments for signing options.

### 6. Running Tests & Benchmarks
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
