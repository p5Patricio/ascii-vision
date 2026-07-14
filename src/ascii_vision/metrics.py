import numpy as np

def brightness_mapping(block: np.ndarray, num_chars: int) -> int:
    """
    Maps the average intensity of a source block directly to an index in a density-sorted list of characters.
    
    Parameters:
        block: 2D NumPy array representing the source image block.
        num_chars: Number of characters available in the sorted list.
        
    Returns:
        An integer index in the range [0, num_chars - 1].
    """
    if block.size == 0:
        return 0
    
    mean_val = np.mean(block)
    # Check if intensity is in range [0, 255] or [0.0, 1.0]
    if mean_val > 1.0:
        mean_val /= 255.0
        
    idx = int(round(mean_val * (num_chars - 1)))
    return max(0, min(num_chars - 1, idx))


def brightness_mapping_vectorized(blocks: np.ndarray, num_chars: int) -> np.ndarray:
    """
    Vectorized version of brightness mapping.
    
    Parameters:
        blocks: NumPy array of shape (cols, height, width) or (rows, cols, height, width).
        num_chars: Number of characters available in the sorted list.
        
    Returns:
        NumPy array of indices matching the shape of blocks up to the height/width dimensions.
    """
    if blocks.size == 0:
        return np.array([], dtype=np.int32)
    
    # Calculate mean over the last two dimensions (height, width)
    means = np.mean(blocks, axis=(-2, -1))
    
    # Normalize if values are in [0, 255]
    # We check the maximum value to decide
    max_val = np.max(means)
    if max_val > 1.0:
        means = means / 255.0
        
    indices = np.round(means * (num_chars - 1)).astype(np.int32)
    return np.clip(indices, 0, num_chars - 1)


def compute_mse(block: np.ndarray, glyphs: np.ndarray) -> np.ndarray:
    """
    Computes Mean Squared Error (MSE) of a single source block against cached glyphs.
    
    Parameters:
        block: 2D NumPy array of shape (height, width).
        glyphs: 3D NumPy array of shape (N, height, width).
        
    Returns:
        1D NumPy array of shape (N,) containing MSE values.
    """
    if block.ndim != 2:
        raise ValueError("block must be a 2D array of shape (height, width)")
    if glyphs.ndim != 3:
        raise ValueError("glyphs must be a 3D array of shape (N, height, width)")
    if block.shape != glyphs.shape[1:]:
        raise ValueError(f"Block shape {block.shape} does not match glyph shape {glyphs.shape[1:]}")
        
    # Vectorized subtraction, squaring, and mean along (height, width) axes
    return np.mean((glyphs - block) ** 2, axis=(1, 2))


def compute_ssim(block: np.ndarray, glyphs: np.ndarray, dynamic_range: float = 1.0) -> np.ndarray:
    """
    Computes Structural Similarity Index (SSIM) of a single source block against cached glyphs.
    
    Parameters:
        block: 2D NumPy array of shape (height, width).
        glyphs: 3D NumPy array of shape (N, height, width).
        dynamic_range: 1.0 if arrays are normalized to [0.0, 1.0], or 255.0 if in [0, 255].
        
    Returns:
        1D NumPy array of shape (N,) containing SSIM values in the range [-1.0, 1.0].
    """
    if block.ndim != 2:
        raise ValueError("block must be a 2D array of shape (height, width)")
    if glyphs.ndim != 3:
        raise ValueError("glyphs must be a 3D array of shape (N, height, width)")
    if block.shape != glyphs.shape[1:]:
        raise ValueError(f"Block shape {block.shape} does not match glyph shape {glyphs.shape[1:]}")

    # Stabilization constants
    k1, k2 = 0.01, 0.03
    c1 = (k1 * dynamic_range) ** 2
    c2 = (k2 * dynamic_range) ** 2

    mu_x = np.mean(block)
    mu_y = np.mean(glyphs, axis=(1, 2))  # shape (N,)

    sigma_x_sq = np.var(block)
    sigma_y_sq = np.var(glyphs, axis=(1, 2))  # shape (N,)

    # Covariance: E[(X - mu_X)(Y - mu_Y)]
    mu_y_expanded = mu_y[:, np.newaxis, np.newaxis]
    covariance = np.mean((block - mu_x) * (glyphs - mu_y_expanded), axis=(1, 2))

    numerator = (2 * mu_x * mu_y + c1) * (2 * covariance + c2)
    denominator = (mu_x**2 + mu_y**2 + c1) * (sigma_x_sq + sigma_y_sq + c2)

    # Prevent division by zero just in case
    denominator = np.where(denominator == 0.0, 1e-10, denominator)

    return numerator / denominator
