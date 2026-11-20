import os

import cv2
import numpy as np
import pytesseract

os.environ.setdefault("OMP_THREAD_LIMIT", "1")   # we run several Tesseract processes in parallel


def _prep(crop: np.ndarray, colored: bool, scale: float, thr) -> np.ndarray:
    big = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    if colored:                                  # white text on a blue, pink or green pill
        hsv = cv2.cvtColor(big, cv2.COLOR_BGR2HSV)
        s_max, v_min = thr or (80, 200)          # low saturation + bright = white text
        mask = (hsv[:, :, 1] < s_max) & (hsv[:, :, 2] > v_min)
    else:                                        # dark brown text on a grey pill
        mask = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY) < (thr or 150)
    img = np.where(mask, 0, 255).astype(np.uint8)
    img = cv2.copyMakeBorder(img, 14, 14, 14, 14, cv2.BORDER_CONSTANT, value=255)
    return cv2.GaussianBlur(img, (3, 3), 0)


def read_line(crop: np.ndarray, colored: bool, psm: int = 7, scale: float = 3.0, thr=None) -> tuple[str, float]:
    """OCR one line of text. Returns (text, mean confidence 0-100)."""
    d = pytesseract.image_to_data(_prep(crop, colored, scale, thr), config=f"--psm {psm}",
                                  output_type=pytesseract.Output.DICT)
    words = [(t, float(c)) for t, c in zip(d["text"], d["conf"]) if t.strip() and float(c) >= 0]
    if not words:
        return "", 0.0
    return " ".join(w for w, _ in words).strip(), sum(c for _, c in words) / len(words)
