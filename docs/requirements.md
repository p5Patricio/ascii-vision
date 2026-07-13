# Project Requirements: ASCII Vision

This document details the functional and non-functional requirements for the first release of ASCII Vision.

---

## Functional Requirements

### 1. Image Loading & Format Support
- The application **MUST** support the following input formats: PNG, JPG, JPEG, BMP, WEBP, and TIFF.
- For animated GIFs, the application **MUST** load and process only the first frame.
- Drag & Drop interface **MUST** accept files dropped anywhere on the left load panel.

### 2. Live Preview & Comparison View
- The application **MUST** feature a live low-resolution preview that updates dynamically as sliders change.
- A full-resolution conversion **MUST** only run when the user explicitly triggers "Generate ASCII".
- The comparison view **MUST** support a Split-View with a draggable slider showing the original image and the generated ASCII output side-by-side.

### 3. Output Monospace Editor
- The bottom panel **MUST** contain a monospace text editor to display the final ASCII text.
- The editor **MUST** implement:
  - Copy to Clipboard & Select All.
  - Text Search (Find).
  - Word Wrap toggle.
  - Font Size adjustment & Font family selector.
  - Character counter and output dimensions (cols x rows).

### 4. Configuration & Profiles
- All settings **MUST** be exportable to and loadable from portable JSON configuration files.
- If a custom font loaded from a config file is missing on the current system, the engine **MUST** fallback to the bundled JetBrains Mono font and display a non-blocking UI alert.

### 5. Quality Presets
- The application **MUST** offer five predefined quality presets:
  - **Fast**: Low-resolution, simple brightness mapping, small glyph set.
  - **Balanced (Default)**: Medium-resolution, Floyd-Steinberg dithering, standard ASCII.
  - **High Quality**: High-resolution, MSE pattern matching, extended ASCII.
  - **Maximum Quality**: Highest resolution, SSIM perceptual matching, full Unicode/Braille set.
  - **Custom**: Exposes all sliders and checkboxes for manual fine-tuning.

---

## Non-Functional Requirements

### 1. Performance & Responsiveness
- High-fidelity conversions **MUST NOT** block the GUI main thread. All processing must run asynchronously in worker threads.
- For a balanced 1080p conversion, the total conversion time **SHOULD NOT** exceed 2 seconds on standard modern CPU hardware.
- The application **MUST** pre-render and cache character glyph blocks to avoid rendering text on the fly during image comparison loops.

### 2. Platform & Tooling
- The application **MUST** target Python 3.13+.
- The GUI **MUST** be built using PySide6 (Qt6) for cross-platform desktop UI consistency.
- Standard libraries like OpenCV, NumPy, and Pillow **MUST** be used for image loading, matrix operations, and resizing.

---

## Execution Guards & Safety
- Before starting computationally intensive SSIM/MSE matching on high-resolution targets, the engine **MUST** estimate the workload (comparing output resolution, active glyph set, and metric).
- If the estimated execution time exceeds 5 seconds, the application **MUST** prompt the user to "Continue", "Optimize Automatically" (which downscales resolution/glyph set), or "Cancel".
