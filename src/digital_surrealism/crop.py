"""Find the black bars (letterboxing/pillarboxing) around a film's picture.

ffmpeg's cropdetect filter looks at a few frames and reports the smallest
rectangle that contains everything brighter than near-black. One sample can
be fooled (a dark scene, a fade to black, credits on black), so we sample the
film at many points and keep the answer that comes up most often.
"""

import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .media import VideoInfo

# Pixels darker than this (on a 0-255 scale) count as black bar. ffmpeg's default.
BLACK_LIMIT = 24
# Sample between 5% and 95% of the runtime to skip opening/closing credits.
SAMPLE_START = 0.05
SAMPLE_END = 0.95
SAMPLE_COUNT = 30
FRAMES_PER_SAMPLE = 15

CROP_PATTERN = re.compile(r"crop=(-?\d+):(-?\d+):(-?\d+):(-?\d+)")


@dataclass(frozen=True)
class Crop:
    w: int
    h: int
    x: int
    y: int

    def __str__(self) -> str:
        return f"{self.w}:{self.h}:{self.x}:{self.y}"

    @classmethod
    def parse(cls, text: str) -> "Crop":
        w, h, x, y = (int(n) for n in text.split(":"))
        return cls(w, h, x, y)


@dataclass
class CropResult:
    crop: Crop
    agreeing: int  # samples that found exactly this crop
    usable: int  # samples that gave a plausible answer
    total: int  # samples taken

    @property
    def confident(self) -> bool:
        """True when at least half the usable samples agree."""
        return self.usable > 0 and self.agreeing * 2 >= self.usable


def sample_times(duration: float, count: int = SAMPLE_COUNT) -> list[float]:
    """Evenly spaced timestamps between SAMPLE_START and SAMPLE_END of the film."""
    start, end = duration * SAMPLE_START, duration * SAMPLE_END
    step = (end - start) / (count - 1)
    return [start + i * step for i in range(count)]


def detect_at(path: Path, seconds: float) -> Crop | None:
    """Run cropdetect on a few frames starting at `seconds`."""
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostdin",
            "-ss", f"{seconds:.3f}", "-i", str(path),
            "-map", "0:v:0", "-frames:v", str(FRAMES_PER_SAMPLE),
            "-vf", f"cropdetect=limit={BLACK_LIMIT}:round=2:reset=0",
            "-f", "null", "-",
        ],
        capture_output=True, text=True,
    )
    matches = CROP_PATTERN.findall(result.stderr)
    if not matches:
        return None
    # cropdetect's last report covers all frames it saw in this sample.
    return Crop(*(int(n) for n in matches[-1]))


def is_plausible(crop: Crop, info: VideoInfo) -> bool:
    """Reject answers from all-black frames (negative or tiny sizes)."""
    return (
        crop.x >= 0 and crop.y >= 0
        and crop.w >= info.width / 4 and crop.h >= info.height / 4
        and crop.x + crop.w <= info.width and crop.y + crop.h <= info.height
    )


def detect_crop(path: Path, info: VideoInfo) -> CropResult:
    """Sample the film and return the most common plausible crop."""
    times = sample_times(info.duration)
    found = [detect_at(path, t) for t in times]
    usable = [c for c in found if c is not None and is_plausible(c, info)]
    if not usable:
        # Nothing usable (e.g., a very dark film): keep the whole frame.
        full = Crop(info.width, info.height, 0, 0)
        return CropResult(full, agreeing=0, usable=0, total=len(times))

    counts = Counter(usable)
    # Most common crop; on a tie, prefer the larger area (crops off less picture).
    crop, agreeing = max(counts.items(), key=lambda item: (item[1], item[0].w * item[0].h))
    return CropResult(crop, agreeing=agreeing, usable=len(usable), total=len(times))


def render_previews(
    path: Path, info: VideoInfo, crop: Crop, out_dir: Path, count: int = 6
) -> list[tuple[Path, Path]]:
    """Save preview pairs, pixels made square.

    For each moment: the full frame with the crop drawn as a red box
    (preview_N.png), and the picture as it will be cropped
    (preview_N_cropped.png). The second shows the crop even where a red box
    would vanish against red scenery.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    full_width = round(info.display_width)
    crop_width = round(crop.w * info.sar)
    outputs = []
    for i, seconds in enumerate(sample_times(info.duration, count), start=1):
        boxed = out_dir / f"preview_{i}.png"
        cropped = out_dir / f"preview_{i}_cropped.png"
        subprocess.run(
            [
                "ffmpeg", "-v", "error", "-nostdin", "-y",
                "-ss", f"{seconds:.3f}", "-i", str(path),
                "-filter_complex", (
                    "[0:v:0]split[a][b];"
                    f"[a]drawbox=x={crop.x}:y={crop.y}:w={crop.w}:h={crop.h}"
                    f":color=red:t=3,scale={full_width}:{info.height},setsar=1[boxed];"
                    f"[b]crop={crop},scale={crop_width}:{crop.h},setsar=1[cropped]"
                ),
                "-map", "[boxed]", "-frames:v", "1", str(boxed),
                "-map", "[cropped]", "-frames:v", "1", str(cropped),
            ],
            check=True,
        )
        outputs.append((boxed, cropped))
    return outputs
