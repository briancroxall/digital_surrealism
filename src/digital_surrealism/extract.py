"""Extract one frame every two seconds, cropped and with square pixels.

Order of operations in the single ffmpeg pass:
  1. deinterlace frames flagged as interlaced (common on DVDs; a no-op otherwise)
  2. keep one frame every 2 seconds (fps=0.5)
  3. crop off the black bars, in the video's stored pixels
  4. scale to square pixels and, for "DVD size", so the full frame
     would be 480 pixels tall
"""

import subprocess
from collections.abc import Callable
from pathlib import Path

from .crop import Crop
from .media import VideoInfo

FRAMES_PER_SECOND = 0.5
DVD_HEIGHT = 480


def output_size(info: VideoInfo, crop: Crop, full_res: bool = False) -> tuple[int, int]:
    """Pixel size of each saved frame.

    DVD size scales the whole frame so it would be 480 pixels tall, then
    crops, so a widescreen film comes out shorter than 480. Sources that are
    already 480 tall or less are never scaled up.
    """
    scale = 1.0 if full_res else min(1.0, DVD_HEIGHT / info.height)
    width = round(crop.w * info.sar * scale)
    height = round(crop.h * scale)
    return width, height


def filter_chain(info: VideoInfo, crop: Crop, full_res: bool = False) -> str:
    width, height = output_size(info, crop, full_res)
    return ",".join([
        "bwdif=mode=send_frame:deint=interlaced",
        f"fps={FRAMES_PER_SECOND}",
        f"crop={crop}",
        f"scale={width}:{height}:flags=lanczos",
        "setsar=1",
    ])


def expected_frames(info: VideoInfo) -> int:
    return round(info.duration * FRAMES_PER_SECOND)


def extract_frames(
    path: Path,
    info: VideoInfo,
    crop: Crop,
    out_dir: Path,
    full_res: bool = False,
    on_progress: Callable[[float], None] | None = None,
) -> int:
    """Write frame_0001.png, frame_0002.png, ... to out_dir. Returns the count."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if any(out_dir.glob("frame_*.png")):
        raise FileExistsError(
            f"{out_dir} already has frame images. Choose an empty folder so "
            "frames from different films don't get mixed together."
        )

    process = subprocess.Popen(
        [
            "ffmpeg", "-v", "error", "-nostdin",
            "-i", str(path),
            "-map", "0:v:0",
            "-vf", filter_chain(info, crop, full_res),
            "-progress", "pipe:1", "-nostats",
            str(out_dir / "frame_%04d.png"),
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    # ffmpeg writes "out_time_us=<microseconds>" lines as it works.
    for line in process.stdout:
        if on_progress and line.startswith("out_time_us="):
            value = line.split("=", 1)[1].strip()
            if value.isdigit():
                on_progress(min(1.0, int(value) / 1e6 / info.duration))
    errors = process.stderr.read()
    if process.wait() != 0:
        raise RuntimeError(f"ffmpeg failed:\n{errors}")
    if on_progress:
        on_progress(1.0)
    return len(list(out_dir.glob("frame_*.png")))
