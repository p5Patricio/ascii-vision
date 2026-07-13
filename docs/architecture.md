# Project Architecture: ASCII Vision

ASCII Vision follows a clean, modular, and decoupled architecture. The core conversion engine behaves as a headless library (`ascii_vision`), and the user interface (`ascii_vision_gui`) acts as a graphical shell that consumes the core services.

---

## 1. High-Level Modular Design

```
+-----------------------------------------------------------------+
|                        ascii_vision_gui                         |
|  - MainView (PySide6)                                           |
|  - WorkerThread (QThread)                                       |
+-----------------------------------------------------------------+
                               │
            Uses signals / slots to trigger tasks
                               │
                               ▼
+-----------------------------------------------------------------+
|                          ascii_vision                           |
|                                                                 |
|   +-------------------+    +-------------------+                |
|   |   FrameProvider   |    |    GlyphCache     |                |
|   | - StaticImage     |    | - JetBrains Mono  |                |
|   | - GIF (v2)        |    | - Dynamic Metrics |                |
|   +-------------------+    +-------------------+                |
|             │                        │                          |
|             ▼                        ▼                          |
|   +--------------------------------------------+                |
|   |              ConversionEngine              |                |
|   | - Preprocessing (contrast, sharpen, etc.)  |                |
|   | - Block Division                           |                |
|   | - Match Metrics (Brightness, MSE, SSIM)    |                |
|   +--------------------------------------------+                |
|                          │                                      |
|                          ▼                                      |
|   +--------------------------------------------+                |
|   |               ExportManager                |                |
|   | - TXT, HTML, SVG, PNG, Clipboard           |                |
|   +--------------------------------------------+                |
+-----------------------------------------------------------------+
```

---

## 2. Core Components

| Component | Responsibility | Technical Details |
|-----------|----------------|-------------------|
| **FrameProvider** | Abstraction of the frame source. | Yields image frames (NumPy arrays) one-by-one. Handles static files, and is architected to support future GIF/Video streams. |
| **GlyphCache** | Pre-renders character glyphs into bitmap matrices. | Uses Pillow to render chars under JetBrains Mono (or a system font) at a given cell resolution, caching them as NumPy boolean matrices. |
| **ConversionEngine** | Orchestrates resizing, preprocessing, and block-character mapping. | Performs vertical/horizontal resizing, computes font cell aspect ratio, segments the image, and compares blocks. |
| **Metrics** | Defines mathematical algorithms for cell matching. | Implements Brightness matching, Mean Squared Error (MSE), and Structural Similarity (SSIM). |
| **ExportManager** | Formats ASCII results into structured output files. | Writes output matrices as TXT, styled HTML (inline CSS), vector SVG, or rendered PNG images. |
| **ConfigManager** | Handles JSON settings persistence. | Serializes UI controls and presets. Fallbacks to JetBrains Mono if a custom font is missing. |

---

## 3. Asynchronous Worker Model (GUI Responsiveness)

To prevent GUI freezing during heavy operations (like SSIM calculations), execution is offloaded to a background thread using Qt's `QThread` and worker pattern.

```
Main UI Thread                     Worker Thread (QThread)
==============                     =======================
   │                                         │
   ├─► Click "Generate ASCII" ───────────────┤
   │                                         ├─► Initialize FrameProvider
   │                                         ├─► Build GlyphCache
   │   ◄── Emit progress(15%, "Cache Built")─┤
   │                                         ├─► Resizing & Aspect Correction
   │                                         ├─► Block Matching loop (NumPy)
   │   ◄── Emit progress(65%, "SSIM Matching")┤
   │                                         ├─► Final ASCII assembly
   │   ◄── Emit result(AsciiMatrix) ─────────┤
   ├─► Display in Monospace Editor           │
```

## 4. Key Architectural Decisions

1. **Font Bounding-Box Ratio**: Rather than utilizing a hardcoded character ratio (e.g. `0.55`), the `ConversionEngine` measures the bounding box of a standard character (e.g. `'M'`) in the target font size, obtaining its width and height dynamically.
2. **Vectorized Comparison**: Loops over image blocks compare the block matrix directly to the pre-rendered glyph cache tensor using NumPy broadcasting, which shifts computation to optimized C-code.
