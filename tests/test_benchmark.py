import time
import numpy as np
import pytest
from ascii_vision.glyph_cache import GlyphCache
from ascii_vision.engine import ConversionEngine
from ascii_vision.metrics import compute_mse, compute_ssim

TEST_FONT_PATH = "assets/fonts/JetBrainsMono-Regular.ttf"

def test_benchmark_mse_vs_ssim(capsys=None):
    """
    Executes and reports comparison execution times for MSE vs SSIM on a small dummy image,
    writing statistics to stdout.
    """
    # Create a dummy image block (10x10) and dummy glyph cache (100 glyphs of 10x10)
    np.random.seed(42)
    block = np.random.rand(10, 10).astype(np.float32)
    glyphs = np.random.rand(100, 10, 10).astype(np.float32)
    
    # Run MSE benchmark
    iterations = 1000
    start_mse = time.perf_counter()
    for _ in range(iterations):
        _ = compute_mse(block, glyphs)
    end_mse = time.perf_counter()
    mse_total_time = end_mse - start_mse
    mse_avg_time = mse_total_time / iterations
    
    # Run SSIM benchmark
    start_ssim = time.perf_counter()
    for _ in range(iterations):
        _ = compute_ssim(block, glyphs, dynamic_range=1.0)
    end_ssim = time.perf_counter()
    ssim_total_time = end_ssim - start_ssim
    ssim_avg_time = ssim_total_time / iterations
    
    # Output statistics
    report = (
        "\n" + "="*60 + "\n"
        "           ASCII VISION BENCHMARK REPORT (MSE vs SSIM)      \n"
        "="*60 + "\n"
        f"Iterations: {iterations}\n"
        f"Glyphs Cache Count: {glyphs.shape[0]} ({glyphs.shape[1]}x{glyphs.shape[2]} px)\n"
        "-"*60 + "\n"
        f"MSE  - Total Time: {mse_total_time:.5f}s | Avg Time: {mse_avg_time * 1e6:.2f} µs\n"
        f"SSIM - Total Time: {ssim_total_time:.5f}s | Avg Time: {ssim_avg_time * 1e6:.2f} µs\n"
        f"Ratio (SSIM / MSE): {ssim_total_time / mse_total_time:.2f}x slower\n"
        "="*60 + "\n"
    )
    
    # Print so pytest -s or python runs display it
    print(report)

if __name__ == "__main__":
    test_benchmark_mse_vs_ssim()
