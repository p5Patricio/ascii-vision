import os
from typing import Generator, Union
import numpy as np
from PIL import Image

class FrameProvider:
    """
    Abstract base class for retrieving frames iteratively.
    """
    def get_frames(self) -> Generator[np.ndarray, None, None]:
        """
        Yields frames sequentially.
        """
        raise NotImplementedError("Subclasses must implement get_frames()")

    @property
    def total_frames(self) -> int:
        """
        Returns the total number of frames.
        """
        raise NotImplementedError("Subclasses must implement total_frames")


class StaticImageFrameProvider(FrameProvider):
    """
    FrameProvider implementation for loading a single static image using Pillow.
    Yields exactly one frame and terminates.
    """
    def __init__(self, image_source: Union[str, Image.Image]):
        """
        Initializes the provider with a file path or a PIL Image instance.
        """
        if not isinstance(image_source, (str, Image.Image)):
            raise TypeError("image_source must be a file path (str) or PIL.Image.Image instance")
        self.image_source = image_source
        self._frame = None

    def _load_frame(self) -> np.ndarray:
        if self._frame is not None:
            return self._frame

        if isinstance(self.image_source, str):
            if not os.path.exists(self.image_source):
                raise FileNotFoundError(f"Image path not found: {self.image_source}")
            with Image.open(self.image_source) as img:
                # Convert to RGB to ensure a consistent 3D NumPy array shape
                img_rgb = img.convert("RGB")
                self._frame = np.array(img_rgb)
        elif isinstance(self.image_source, Image.Image):
            img_rgb = self.image_source.convert("RGB")
            self._frame = np.array(img_rgb)
        else:
            raise TypeError("image_source must be a file path (str) or PIL.Image.Image instance")

        return self._frame

    def get_frames(self) -> Generator[np.ndarray, None, None]:
        """
        Yields exactly 1 frame of the loaded image and terminates.
        """
        yield self._load_frame()

    @property
    def total_frames(self) -> int:
        """
        Returns 1 for a static image.
        """
        return 1
