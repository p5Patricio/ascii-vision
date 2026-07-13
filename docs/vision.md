# Project Vision: ASCII Vision

ASCII Vision is a professional Python-based desktop application designed to convert images into high-fidelity ASCII, Unicode, and Braille art. 

Unlike basic brightness-based ASCII converters, ASCII Vision functions as an **ASCII Rendering Laboratory**. It utilizes modern computer vision, vectorized pre-processing, and perceptual similarity metrics (like SSIM) to match structural features (edges, contours) and optimize visual output.

---

## Core Philosophy

1. **Visual Fidelity First**: The primary objective is producing the highest-quality ASCII representation possible.
2. **Zero-Configuration defaults**: A new user can drag an image and get an outstanding result in one click.
3. **Advanced Controls**: Power users can fine-tune every parameter (contrast, sharpness, dithering algorithms, similarity metrics).
4. **Cross-Platform Consistency**: Visual styling and output must be identical across Windows, macOS, and Linux.
5. **Decoupled Engine**: The core conversion engine is a headless package, entirely independent of the PySide6 GUI, enabling CLI usage and unit testing.

---

## Capabilities Checklist

- [x] Bundle JetBrains Mono font for cross-platform rendering consistency.
- [x] Dynamically measure glyph bounding boxes for automatic character aspect ratio correction.
- [x] Run conversion pipelines in background threads to keep the UI fully responsive.
- [x] Support multiple conversion metrics: Brightness mapping, Mean Squared Error (MSE), and Structural Similarity (SSIM).
- [x] Multi-format export: Plain text (.txt), styled HTML (.html), scalable vector graphics (.svg), rendered PNG (.png), and clipboard.
- [x] Interactive comparison mode with a draggable split-view slider and synchronized zoom.

---

## Future Laboratory Extensions
- Real-time video-to-ASCII streaming.
- GPU acceleration via CUDA and OpenCL.
- ANSI color parsing (RGB ASCII).
- VS Code plugin support.
