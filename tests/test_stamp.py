"""Tests for tools/stamp_version.py, which prepares web/ for GitHub Pages."""

import re
import shutil
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"
WEB = TOOLS.parent / "web"
sys.path.insert(0, str(TOOLS))
from stamp_version import stamp  # noqa: E402


def test_every_script_reference_is_stamped(tmp_path):
    count = stamp(WEB, tmp_path / "site", "abc1234")
    # index.html: summing.js and worker.js; worker.js: png.js and summing.js.
    assert count == 4
    for path in (tmp_path / "site").glob("*"):
        text = path.read_text(encoding="utf-8")
        for name in re.findall(r"""["']\./([\w-]+\.js[^"']*)["']""", text):
            assert name.endswith("?v=abc1234"), f"{path.name}: {name}"


def test_only_script_references_change(tmp_path):
    stamp(WEB, tmp_path / "site", "abc1234")
    for original in WEB.glob("*"):
        stamped = (tmp_path / "site" / original.name).read_text(encoding="utf-8")
        assert stamped.replace("?v=abc1234", "") == original.read_text(encoding="utf-8")


def test_unstamped_reference_stops_it(tmp_path):
    source = tmp_path / "web"
    shutil.copytree(WEB, source)
    worker = source / "worker.js"
    worker.write_text(worker.read_text().replace('"./png.js"', '"png.js"'))
    with pytest.raises(SystemExit, match="Unstamped"):
        stamp(source, tmp_path / "site", "abc1234")


def test_reference_to_a_missing_script_stops_it(tmp_path):
    source = tmp_path / "web"
    shutil.copytree(WEB, source)
    worker = source / "worker.js"
    worker.write_text(worker.read_text().replace('"./png.js"', '"./missing.js"'))
    with pytest.raises(SystemExit, match="missing.js"):
        stamp(source, tmp_path / "site", "abc1234")
