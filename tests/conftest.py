"""Synthetic test films shared by the tests.

Each test film is a ffmpeg test pattern padded with black bars, so we know
exactly where the picture is.
"""

import subprocess

import pytest


def make_film(path, picture, frame, offset, sar="1", seconds=40, dark=None):
    """Write a test film: `picture` (WxH) padded to `frame` (WxH) at `offset` (x:y)."""
    filters = []
    if dark:  # paint the picture black between these seconds
        filters.append(f"drawbox=enable='between(t,{dark[0]},{dark[1]})'"
                       ":x=0:y=0:w=iw:h=ih:color=black:t=fill")
    filters.append(f"pad={frame.replace('x', ':')}:{offset}:black,setsar={sar}")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", f"testsrc2=size={picture}:rate=24:duration={seconds}",
         "-vf", ",".join(filters), "-c:v", "mpeg2video", "-q:v", "3", str(path)],
        check=True,
    )
    return path


@pytest.fixture(scope="module")
def dvd_film(tmp_path_factory):
    """Anamorphic 16:9 DVD with a 2:1 picture and a dark scene in the middle."""
    path = tmp_path_factory.mktemp("films") / "dvd.mkv"
    return make_film(path, "720x360", "720x480", "0:60", sar="32/27", dark=(15, 22))
