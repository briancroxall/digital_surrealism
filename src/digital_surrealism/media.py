"""Read basic facts about a video file with ffprobe."""

import json
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


@dataclass
class VideoInfo:
    width: int  # stored width in pixels
    height: int  # stored height in pixels
    sar: Fraction  # sample aspect ratio: how wide each stored pixel is shown
    duration: float  # seconds

    @property
    def display_width(self) -> float:
        """Width once non-square (anamorphic) pixels are made square."""
        return self.width * self.sar


def probe(path: Path) -> VideoInfo:
    """Return size, pixel shape, and duration of the first video stream."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,sample_aspect_ratio:format=duration",
            "-of", "json",
            str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    if not data.get("streams"):
        raise ValueError(f"No video stream found in {path}")
    stream = data["streams"][0]

    # A missing or "0:1" SAR means square pixels.
    sar_text = stream.get("sample_aspect_ratio", "1:1")
    num, den = (int(n) for n in sar_text.split(":"))
    sar = Fraction(num, den) if num and den else Fraction(1)

    return VideoInfo(
        width=int(stream["width"]),
        height=int(stream["height"]),
        sar=sar,
        duration=float(data["format"]["duration"]),
    )
