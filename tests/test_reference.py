"""Tests for the Python reference version of the summed image (tools/reference.py).

The browser's version (web/summing.js) is checked against this reference with
tools/browser_check.py.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from reference import frame_paths, summed_image  # noqa: E402


def write_frames(folder, frames):
    for i, frame in enumerate(frames, start=1):
        Image.fromarray(np.array(frame, dtype=np.uint8)).save(folder / f"frame_{i:04d}.png")


def test_hand_computed_example(tmp_path):
    # Red averages are 20, 40, 60, 101 -> stretched over 20..101 (a range of 81):
    #   (40-20)/81*255 = 62.96 -> 63,  (60-20)/81*255 = 125.9 -> 126.
    # Green averages are 0, 0, 0, 30 -> 0 and 255. Blue is 9 everywhere: a flat
    # channel can't be stretched, so it stays 9.
    write_frames(tmp_path, [
        [[(10, 0, 9), (30, 0, 9)], [(50, 0, 9), (100, 30, 9)]],
        [[(20, 0, 9), (40, 0, 9)], [(60, 0, 9), (101, 30, 9)]],
        [[(30, 0, 9), (50, 0, 9)], [(70, 0, 9), (102, 30, 9)]],
    ])
    image, ranges = summed_image(frame_paths(tmp_path))
    assert image.tolist() == [[[0, 0, 9], [63, 0, 9]], [[126, 0, 9], [255, 255, 9]]]
    assert ranges == [(20, 101), (0, 30), (9, 9)]


def test_halves_round_up(tmp_path):
    # Red averages 0, 1, 2 over a range of 0..2 stretch to 0, 127.5, 255.
    # 127.5 rounds up to 128, as in the browser (Math.floor(x + 0.5)).
    write_frames(tmp_path, [[[(0, 0, 0), (1, 0, 0), (2, 0, 0)]]])
    image, _ = summed_image(frame_paths(tmp_path))
    assert image[0, 1, 0] == 128


def test_frames_sorted_by_number(tmp_path):
    for name in ["frame_10.png", "frame_2.png", "frame_1.png", ".hidden.png"]:
        Image.new("RGB", (1, 1)).save(tmp_path / name)
    assert [p.name for p in frame_paths(tmp_path)] == ["frame_1.png", "frame_2.png", "frame_10.png"]
