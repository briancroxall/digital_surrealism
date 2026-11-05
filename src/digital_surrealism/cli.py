"""Command-line interface for the frame extractor."""

import argparse
import sys
from pathlib import Path

from .crop import Crop, detect_crop, render_previews
from .extract import expected_frames, extract_frames, output_size
from .media import probe


def describe(path: Path, full_res: bool, crop_text: str | None):
    """Probe the film, find (or accept) the crop, and print a summary."""
    info = probe(path)
    print(f"Video: {info.width} x {info.height} stored, pixel shape {info.sar}, "
          f"{info.duration / 60:.1f} minutes")
    if crop_text:
        crop = Crop.parse(crop_text)
        print(f"Crop (given): {crop}")
    else:
        print("Looking for black bars...")
        result = detect_crop(path, info)
        crop = result.crop
        print(f"Crop (detected): {crop}  "
              f"[{result.agreeing} of {result.usable} usable samples agree; "
              f"{result.total - result.usable} samples were too dark to use]")
        if not result.confident:
            print("WARNING: samples disagree. Check the previews before extracting.")
    width, height = output_size(info, crop, full_res)
    print(f"Frames will be {width} x {height}, about {expected_frames(info)} of them")
    return info, crop


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="digital-surrealism")
    sub = parser.add_subparsers(dest="command", required=True)

    detect = sub.add_parser("detect", help="find the crop and save preview images")
    detect.add_argument("film", type=Path)
    detect.add_argument("--previews", type=Path, help="folder for preview images")
    detect.add_argument("--full-res", action="store_true")

    extract = sub.add_parser("extract", help="extract one frame every 2 seconds")
    extract.add_argument("film", type=Path)
    extract.add_argument("out_dir", type=Path)
    extract.add_argument("--crop", help="W:H:X:Y, skipping detection")
    extract.add_argument("--full-res", action="store_true",
                         help="don't scale down to DVD size")

    args = parser.parse_args(argv)

    if args.command == "detect":
        info, crop = describe(args.film, args.full_res, None)
        if args.previews:
            for out in render_previews(args.film, info, crop, args.previews):
                print(f"Preview: {out}")
    else:
        info, crop = describe(args.film, args.full_res, args.crop)

        def show(fraction: float) -> None:
            print(f"\rExtracting: {fraction:6.1%}", end="", file=sys.stderr)

        count = extract_frames(args.film, info, crop, args.out_dir,
                               args.full_res, on_progress=show)
        print(f"\nSaved {count} frames to {args.out_dir}")
