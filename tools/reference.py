"""Reference version of the Image maker's calculations, in Python.

Used to check the browser's output. Same arithmetic as web/summing.js:
average the frames, then stretch each colour channel so its darkest value
becomes 0 and its brightest 255, rounding halves up.
"""

from pathlib import Path

import numpy as np
from PIL import Image


def frame_paths(folder: Path) -> list[Path]:
    """PNG frames in the order the web page uses (frame_2 before frame_10)."""
    import re

    def key(path: Path):
        return [int(part) if part.isdigit() else part.lower()
                for part in re.split(r"(\d+)", path.name)]

    return sorted((p for p in folder.glob("*.png") if not p.name.startswith(".")), key=key)


def read(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)


def summed_image(paths: list[Path]) -> tuple[np.ndarray, list[tuple[float, float]]]:
    """Return the summed image (uint8 RGB) and each channel's (darkest, brightest)."""
    total = None
    for path in paths:
        frame = read(path)
        total = frame if total is None else total + frame
    mean = total / len(paths)
    out = np.empty_like(mean)
    ranges = []
    for channel in range(3):
        values = mean[..., channel]
        low, high = values.min(), values.max()
        ranges.append((low, high))
        stretched = (values - low) / (high - low) * 255 if high > low else values
        out[..., channel] = np.floor(stretched + 0.5)
    return out.astype(np.uint8), ranges
