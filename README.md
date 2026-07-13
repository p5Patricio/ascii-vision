# ASCII Vision

ASCII Vision is a professional Python-based desktop application designed to convert images into high-quality ASCII art using modern computer vision techniques, edge matching, histogram optimization, dithering, and perceptual similarity metrics (like SSIM).

## Features (Planned)
- Elegant modern GUI built with PySide6 (Qt) inspired by VS Code, GitHub Desktop, and Figma.
- High-fidelity visual output with advanced image processing pipelines.
- Multiple conversion algorithms across evolutionary phases:
  - Phase 1: Classic Brightness Mapping
  - Phase 2: Histogram Matching
  - Phase 3: Dithering (Floyd-Steinberg, Atkinson, Bayer)
  - Phase 4: Character Font Render & Pattern Comparison
  - Phase 5: Mean Squared Error (MSE) Optimization
  - Phase 6: Perceptual Optimization (SSIM)
  - Phase 7: ASCII, Extended Unicode, Block/Shade, and Braille sets comparison.
- Export options: TXT, HTML, SVG, PNG, Clipboard.
- High performance powered by NumPy, Pillow, OpenCV, vectorized processing, character cache, and multi-threading.

## Tech Stack
- Python 3.13+
- PySide6 (Qt)
- OpenCV
- Pillow
- NumPy

## License
MIT License
