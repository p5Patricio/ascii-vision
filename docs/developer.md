# Developer Documentation: ASCII Vision Core

This document summarizes the core performance optimizations and architectural patterns implemented in ASCII Vision.

---

## 1. Vectorized Character Matching (NumPy)

To achieve high-quality ASCII conversion, the engine compares every block of the resized image against a pre-rendered cache of character glyph matrices. Doing this in standard Python loops would be extremely slow. We solve this by vectorizing the calculations using NumPy.

### Glyph Cache Tensor
The `GlyphCache` pre-renders all characters of a set into a 3D NumPy array of shape:
$$\text{Shape} = (N_{\text{glyphs}}, \text{height}, \text{width})$$

### Vectorized MSE (Mean Squared Error)
For an image block $B$ of size $(\text{height}, \text{width})$, we calculate the MSE against all cached glyphs simultaneously:
1. We expand $B$ to match the 3D glyph tensor using NumPy broadcasting.
2. We compute the element-wise differences, square them, and average over the spatial dimensions:
   ```python
   differences = glyph_cache_tensor - block[np.newaxis, :, :]
   mse_scores = np.mean(differences ** 2, axis=(1, 2))
   best_glyph_idx = np.argmin(mse_scores)
   ```
This pushes the entire loop over the character set into optimized, compiled C-code inside NumPy.

### Vectorized SSIM (Structural Similarity)
Similarly, the Structural Similarity Index is computed using vectorized statistical matrices (means, variances, and covariances) calculated across the 3D tensor, which allows matching complex edge outlines in real-time.

---

## 2. GUI Threading & Cancellation Model

To keep the PySide6 user interface responsive during heavy computations, the conversion engine runs inside a background `QThread` using a Worker pattern.

### Thread Communication
- **GUI to Worker**: Parameters (image source, columns, metrics) are packed into a JSON-compatible dictionary and passed to the `ConversionWorker` on instantiation or via signals.
- **Worker to GUI**: The worker emits signals for progress updates:
  - `progress(int, str)`: Broadcasts the percentage and current stage (e.g. "Caching Glyphs", "SSIM Mapping").
  - `eta(str, str)`: Broadcasts computed elapsed and remaining time.
  - `result(str, int, int)`: Delivers the final generated text matrix, column size, and row size.
  - `error(str)`: Delivers exception messages if loading or processing fails.

### Cancellation Flag
To allow immediate interruption of a running conversion (e.g. when clicking the "Cancel" button), the worker regularly checks a thread-safe volatile flag:
```python
if self.is_cancelled:
    # Terminate loop and emit partial/abort status
    break
```
This ensures the background thread exits cleanly without leaving orphaned processes.
