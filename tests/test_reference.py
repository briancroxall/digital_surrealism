"""Tests for the Python reference version of the Image maker (tools/reference.py).

The browser's version (web/summing.js) is checked against this reference with
tools/browser_check.py.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from reference import barcodes, frame_paths, summed_image  # noqa: E402


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


K, W = (0, 0, 0), (99, 99, 99)       # black; grey in the LEFT middle column
C, R = (200, 100, 50), (5, 6, 7)     # marked centre column; marked centre row
BARCODE_FRAMES = [
    [[(255, 0, 0)] * 4] * 3,         # solid red
    [[(0, 255, 0)] * 4] * 3,         # solid green
    [[(0, 0, 255)] * 4] * 3,         # solid blue
    [[(10, 20, 30)] * 4] * 3,        # solid grey
    [[K, W, C, K],                   # 4 wide: the centre column is the 3rd
     [R, R, R, R],                   # (right-hand middle), not the grey 2nd.
     [K, W, C, K]],                  # 3 tall: the centre row is the 2nd.
]


def as_lists(rows):
    """Colours written as tuples above, in the list form numpy gives back."""
    return np.array(rows).tolist()


def test_barcodes_hand_computed(tmp_path):
    write_frames(tmp_path, BARCODE_FRAMES)
    codes = barcodes(frame_paths(tmp_path))
    solids = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (10, 20, 30)]

    # Horizontal: 5 frames wide x 3 tall; frame 5's column is C, R, C.
    assert codes["horizontal"].tolist() == as_lists([
        solids + [C], solids + [R], solids + [C]])

    # Vertical: 4 wide x 5 frames tall; frame 5's row is all R.
    assert codes["vertical"].tolist() == as_lists([[s] * 4 for s in solids] + [[R] * 4])

    # Average colour of frame 5, over its 12 pixels:
    #   red   (2*99 + 2*200 + 4*5) / 12 = 618/12 = 51.5   -> 52 (halves round up)
    #   green (2*99 + 2*100 + 4*6) / 12 = 422/12 = 35.17  -> 35
    #   blue  (2*99 + 2*50  + 4*7) / 12 = 326/12 = 27.17  -> 27
    stripe = solids + [(52, 35, 27)]
    assert codes["average"].tolist() == as_lists([stripe, stripe, stripe])
