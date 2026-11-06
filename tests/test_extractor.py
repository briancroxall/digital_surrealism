"""Tests for crop detection and frame extraction, using synthetic films
(see conftest.py)."""

import subprocess
from fractions import Fraction

import pytest

from digital_surrealism.crop import Crop, detect_crop, is_plausible
from digital_surrealism.extract import extract_frames, output_size
from digital_surrealism.media import VideoInfo, probe


def test_probe_reads_anamorphic_dvd(dvd_film):
    info = probe(dvd_film)
    assert (info.width, info.height, info.sar) == (720, 480, Fraction(32, 27))
    assert info.duration == pytest.approx(40, abs=0.1)


def test_detect_ignores_dark_scene(dvd_film):
    result = detect_crop(dvd_film, probe(dvd_film))
    assert result.crop == Crop(720, 360, 0, 60)
    assert result.usable < result.total  # the dark samples were thrown out
    assert result.confident


def test_all_black_answer_is_rejected():
    info = VideoInfo(720, 480, Fraction(1), 60)
    assert not is_plausible(Crop(-718, -478, 720, 480), info)
    assert is_plausible(Crop(720, 360, 0, 60), info)


def test_output_sizes():
    dvd = VideoInfo(720, 480, Fraction(32, 27), 60)
    bluray = VideoInfo(1920, 1080, Fraction(1), 60)
    assert output_size(dvd, Crop(720, 360, 0, 60)) == (853, 360)
    # DVD never scales up, even when asked for full resolution
    assert output_size(dvd, Crop(720, 360, 0, 60), full_res=True) == (853, 360)
    assert output_size(bluray, Crop(1920, 804, 0, 138)) == (853, 357)
    assert output_size(bluray, Crop(1920, 804, 0, 138), full_res=True) == (1920, 804)


def test_extract_frames(dvd_film, tmp_path):
    info = probe(dvd_film)
    count = extract_frames(dvd_film, info, Crop(720, 360, 0, 60), tmp_path)
    assert count == 20  # 40 seconds, one frame every 2 seconds
    first = tmp_path / "frame_0001.png"
    size = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
                           "-of", "csv=p=0", str(first)],
                          capture_output=True, text=True, check=True).stdout.strip()
    assert size == "853,360"


def test_extract_refuses_folder_with_frames(dvd_film, tmp_path):
    (tmp_path / "frame_0001.png").touch()
    with pytest.raises(FileExistsError):
        extract_frames(dvd_film, probe(dvd_film), Crop(720, 360, 0, 60), tmp_path)
