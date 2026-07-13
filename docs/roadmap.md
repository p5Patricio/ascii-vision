# Project Roadmap: ASCII Vision

This roadmap outlines the planned evolutionary phases for the algorithms, user interface, and performance optimizations of ASCII Vision.

---

## Algorithm Evolutionary Phases

```
┌────────────────────────────────┐
│   Phase 1: Brightness Mapping  │ <-- Fast conversion based on average pixel intensity
└───────────────┬────────────────┘
                ▼
┌────────────────────────────────┐
│  Phase 2: Histogram Matching   │ <-- Contrast adjustments and tone normalization
└───────────────┬────────────────┘
                ▼
┌────────────────────────────────┐
│       Phase 3: Dithering       │ <-- Error diffusion: Floyd-Steinberg, Atkinson, Bayer
└───────────────┬────────────────┘
                ▼
┌────────────────────────────────┐
│   Phase 4: Pattern Comparison  │ <-- Comparison against rendered character glyphs (MSE)
└───────────────┬────────────────┘
                ▼
┌────────────────────────────────┐
│  Phase 5: Perceptual Match (SSIM)  <-- Structural similarity matching (edges & contours)
└───────────────┬────────────────┘
                ▼
┌────────────────────────────────┐
│  Phase 6: Multi-Set Expansion  │ <-- ASCII, Unicode Shades, Block Elements, Braille
└───────────────┬────────────────┘
                ▼
┌────────────────────────────────┐
│     Phase 7: Future Labs       │ <-- Video streams, ANSI color, CUDA/OpenCL GPU
└────────────────────────────────┘
```

---

## Phase Breakdown

| Phase | Title | Description | Target Deliverables |
|-------|-------|-------------|---------------------|
| **Phase 1** | Brightness Mapping | Traditional grayscale-to-character conversion. | Average intensity mapping logic, default character set, basic TXT export. |
| **Phase 2** | Histogram Matching | Distribute image brightness levels to match character frequencies. | Local histogram equalization, contrast-stretching filters. |
| **Phase 3** | Dithering | Add texture detail using error diffusion. | Floyd-Steinberg, Atkinson, and Bayer dithering options. |
| **Phase 4** | Pattern Matching | Compare character glyph shapes directly. | Monospace glyph pre-rendering cache, Mean Squared Error (MSE) matrix math. |
| **Phase 5** | SSIM Match | Perceptual analysis focused on structures/edges. | Structural Similarity Index (SSIM) matching engine. |
| **Phase 6** | Multi-Set Expansion | Support broader character types. | Unicode block shading, Braille matching, and custom user-provided sets. |
| **Phase 7** | Future Labs | Performance and media extensions. | QThread video parser, ANSI color renderer, GPU-acceleration (CUDA). |

---

## Core Library vs. UI Roadmap

### Version 1.0 (Current Scope)
- Complete headless library `ascii_vision`.
- Implementation of Phases 1 to 6.
- PySide6 GUI supporting single static images, low-res preview, split draggable comparison slider, progress monitoring, and profile management.
- Multi-format exporter (TXT, HTML, SVG, PNG, Clipboard).

### Version 2.0 (Future Scope)
- Video/GIF processing (using the FrameProvider stream design).
- ANSI color output and colored HTML/SVG exports.
- GPU acceleration via PyOpenCL / CuPy.
- CLI binary and REST API wrapper.
