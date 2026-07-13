# GUI Specification: ASCII Vision

ASCII Vision features a dark-themed visual workbench inspired by VS Code, Figma, and GitHub Desktop. It is built using **PySide6 (Qt6)**.

---

## 1. Visual Layout Grid

```
+--------------------------------------------------------------------------------+
|  File  |  Edit  |  Settings  |  Help                                           |
+--------------------------------------------------------------------------------+
|                    |                                       |                   |
|                    |             Center Panel              |    Right Panel    |
|                    |        (Original / Preview)           |   (Live Preview)  |
|                    |  +---------------------------------+  |                   |
|                    |  |                                 |  |                   |
|     Left Panel     |  |                                 |  |  +-------------+  |
|  - Drag & Drop Zone|  |     Original Image View         |  |  |   ASCII     |  |
|  - File Selector   |  |                                 |  |  |   Result    |  |
|                    |  |       [Split Slider]            |  |  |   Preview   |  |
|                    |  |                                 |  |  +-------------+  |
|                    |  +---------------------------------+  |                   |
+--------------------+---------------------------------------+-------------------+
|                                                                                |
|                                  Bottom Panel                                  |
|   +------------------------------------------------------------------------+   |
|   | Monospace Output Editor (TXT Scroll / Word Wrap / Search / Font Sizes) |   |
|   +------------------------------------------------------------------------+   |
|   [Status Bar: Char count | Dimensions cols x rows | Elapsed Time]             |
+--------------------------------------------------------------------------------+
```

---

## 2. Panel Details

### Left Panel (File Input & Presets)
- **Drag & Drop Target**: A visual zone with dashed borders. Supported formats (PNG, JPG, BMP, WEBP, TIFF, GIF) are displayed.
- **Preset Selector**: Combo box featuring `Fast`, `Balanced (Default)`, `High Quality`, `Maximum Quality`, and `Custom`.
- **Primary Action Button**: "Generate ASCII" — executes the full-resolution conversion in a background worker thread.

### Center & Right Panels (Previsualization & Comparison)
- **Split-Screen Mode**: Renders the original image and the converted ASCII side-by-side.
- **Draggable Comparison Slider**: A vertical line that can be dragged left/right across the center preview to wipe between the original pixel image and the generated text art.
- **Synchronized Zoom**: Zooming or panning on the original image automatically pans and zooms the preview matching cell coordinate.

### Bottom Panel (ASCII Monospace Workspace)
- **Text Editor**: A read-only monospace field showing the full-resolution text block.
- **Toolbar Actions**:
  - Word Wrap checkbox.
  - Font Size slider.
  - Font Family dropdown (dynamically loads installed system monospace fonts; falls back to JetBrains Mono).
  - "Copy to Clipboard" and "Search/Find" inputs.

---

## 3. Advanced Parameters (Visible in "Custom" Preset)

| Group | Parameter | Control Type | Range / Options | Description |
|-------|-----------|--------------|-----------------|-------------|
| **Sizing** | Resolution Scale | Slider | 10% - 200% | Target cell sizing scale. |
| **Sizing** | Aspect Ratio | Checkbox + Slider | Auto / 0.1 - 2.0 | Automate cell aspect calculation or override manually. |
| **Filters** | Contrast | Slider | -100 to +100 | Pre-processing contrast. |
| **Filters** | Brightness | Slider | -100 to +100 | Pre-processing brightness adjustment. |
| **Filters** | Sharpen | Slider | 0 to 10 | Edge-sharpening matrix weights. |
| **Filters** | Dithering | Combo Box | None / Floyd-Steinberg / Atkinson / Bayer | Adds gradient textures. |
| **Engine** | Metrics | Combo Box | Brightness / MSE / SSIM | Mathematical comparison model. |
| **Engine** | Char Set | Combo Box | ASCII / Unicode Shades / Braille / Custom | Bins of character maps. |

---

## 4. Background Progress Tracking
When a long conversion begins, a non-blocking dialog overlay displays:
- **Progress Bar** and percentage indicators.
- **Status Text**: E.g., *"Running SSIM on Block 420/2000..."*.
- **Timer Details**: Elapsed time and Estimated Time Arrival (ETA).
- **Cancel Button**: Clicking "Cancel" raises a cancellation flag to immediately terminate the worker thread processing loops.
