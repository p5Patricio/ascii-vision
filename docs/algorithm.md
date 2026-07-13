# Conversion Algorithms: ASCII Vision

This document details the mathematical algorithms and image processing techniques implemented in ASCII Vision.

---

## 1. Brightness Mapping (Phase 1)

Matches each image block to a character based strictly on average grayscale intensity.

- **Formula**: 
  $$\text{Grayscale} = 0.299R + 0.587G + 0.114B$$
  $$\text{Index} = \lfloor \text{Average Grayscale} \times \frac{N_{\text{chars}} - 1}{255} \rfloor$$
- **Pros**: Computationally very fast (\(O(1)\) per block).
- **Cons**: Poor detail retention; ignores edge contours, texture, and shapes.
- **Complexity**: \(O(W \times H)\) where \(W, H\) are the resized dimensions.

---

## 2. Dithering (Phase 3)

Distributes quantization errors to neighboring pixels to simulate continuous tones in low-palette outputs.

### Floyd-Steinberg Dithering
Pushes error to adjacent pixels using fixed weights:
```
       *   7/16
3/16  5/16 1/16
```
- **Pros**: Excellent representation of shading and gradients.
- **Cons**: Can introduce graininess or "patterns" in high-contrast blocks.
- **Complexity**: \(O(W \times H)\).

### Atkinson Dithering
Distributes only a fraction (3/4) of the error, leaving softer contrast:
```
       *   1/8   1/8
 1/8  1/8  1/8
      1/8
```

---

## 3. Pattern Matching via Mean Squared Error (MSE) (Phase 4)

Compares the pixel matrix of an image block directly against pre-rendered glyph bitmaps.

- **Formula**:
  $$\text{MSE}(B, G) = \frac{1}{w \times h} \sum_{x=0}^{w-1} \sum_{y=0}^{h-1} (B(x,y) - G(x,y))^2$$
  where \(B\) is the normalized image block and \(G\) is the pre-rendered glyph matrix.
- **Pros**: Captures structural shapes and character outlines.
- **Cons**: Sensitive to uniform brightness shifts (e.g. a dark block and a light block with the same pattern will register high error).
- **Complexity**: \(O(N_{\text{blocks}} \times N_{\text{glyphs}} \times w \times h)\).

---

## 4. Perceptual Optimization (SSIM) (Phase 5)

Evaluates similarity based on three human visual system components: luminance, contrast, and structure.

- **Formula**:
  $$\text{SSIM}(x, y) = \frac{(2\mu_x\mu_y + C_1)(2\sigma_{xy} + C_2)}{(\mu_x^2 + \mu_y^2 + C_1)(\sigma_x^2 + \sigma_y^2 + C_2)}$$
  where \(\mu\) represents mean intensity, \(\sigma\) represents variance/covariance, and \(C_1, C_2\) are stabilization constants.
- **Pros**: Outstanding visual fidelity; aligns outlines and detects fine structural shapes.
- **Cons**: High computational cost.
- **Complexity**: \(O(N_{\text{blocks}} \times N_{\text{glyphs}} \times w \times h)\) with floating-point operations.

---

## 5. Braille Mapping (Phase 6)

Braille characters are represented in Unicode block `U+2800` to `U+28FF` (256 characters) corresponding to an 8-dot grid layout (\(2 \times 4\)):

```
Dot 1 (1)  Dot 4 (8)
Dot 2 (2)  Dot 5 (16)
Dot 3 (4)  Dot 6 (32)
Dot 7 (64) Dot 8 (128)
```
- **Algorithm**:
  1. Threshold the \(2 \times 4\) sub-block to a binary matrix.
  2. Compute the offset index by summing the values of active dots.
  3. The Unicode character is `chr(0x2800 + offset)`.
- **Pros**: Extremely high detail; can represent fine line art and edges.
- **Cons**: Lacks contrast shading; strictly binary (black/white).
- **Complexity**: \(O(W \times H)\) since it is a direct pixel-to-bit shift.
