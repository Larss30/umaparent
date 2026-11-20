import io

import cv2
import numpy as np
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 40_000_000     # Pillow refuses much bigger images (decompression bombs)


class ImageError(ValueError):
    """The upload is not a usable screenshot."""


def decode(data: bytes) -> np.ndarray:
    """Decode an upload into a BGR array, with size checks."""
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception as e:
        raise ImageError("That file is not a readable image.") from e
    im = ImageOps.exif_transpose(im).convert("RGB")
    if im.width < 400 or im.height < 600:
        raise ImageError("That screenshot is too small to read.")
    return np.asarray(im)[:, :, ::-1].copy()


def to_hsv(bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
