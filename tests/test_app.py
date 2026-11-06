"""Tests for the web interface, using a synthetic film (see conftest.py).

Finder dialogs can't be clicked in a test, so they are replaced with
functions that return a chosen path.
"""

import time

import pytest
from conftest import make_film

from digital_surrealism import app as app_module
from digital_surrealism.crop import Crop


@pytest.fixture
def client(tmp_path):
    flask_app = app_module.create_app(preview_root=tmp_path / "previews")
    return flask_app.test_client()


def choose(monkeypatch, film=None, folder=None):
    """Make the Finder dialogs 'return' these paths."""
    monkeypatch.setattr(app_module, "ask_for_file", lambda: film)
    monkeypatch.setattr(app_module, "ask_for_folder", lambda: folder)


def wait_for(client, stage, seconds=60):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        status = client.get("/api/status").get_json()
        if status["stage"] == stage:
            return status
        time.sleep(0.2)
    raise AssertionError(f"never reached {stage}: {status}")


def test_whole_flow(client, dvd_film, tmp_path, monkeypatch):
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    choose(monkeypatch, film=dvd_film, folder=desktop)

    client.post("/api/choose-film")
    status = wait_for(client, "review")
    assert status["film"]["kind"] == "DVD"
    assert status["film"]["shape"] == "widescreen (16:9)"
    assert status["crop"] == "720:360:0:60"
    assert status["margins"] == {"top": 60, "bottom": 60, "left": 0, "right": 0}
    assert status["frame_size"] == "853 × 360"
    assert not status["can_full_res"]  # a DVD has nothing larger to offer

    # Both images of each preview pair are served
    for pair in status["previews"]:
        assert client.get(pair["boxed"]).status_code == 200
        assert client.get(pair["cropped"]).status_code == 200

    status = client.post("/api/choose-folder").get_json()
    assert status["out_dir"] == str(desktop / "dvd_frames")

    client.post("/api/extract")
    status = wait_for(client, "done")
    assert status["result"]["count"] == 20
    assert len(list((desktop / "dvd_frames").glob("frame_*.png"))) == 20


def test_nudge_moves_one_edge_and_undo_restores(client, dvd_film, monkeypatch):
    choose(monkeypatch, film=dvd_film)
    client.post("/api/choose-film")
    wait_for(client, "review")

    status = client.post("/api/nudge", json={"edge": "top", "pixels": 2}).get_json()
    assert status["crop"] == "720:358:0:62"
    assert status["margins"]["top"] == 62 and status["margins"]["bottom"] == 60
    assert status["frame_size"] == "853 × 358"

    status = client.post("/api/reset-crop").get_json()
    assert status["crop"] == "720:360:0:60"


def test_nudge_cannot_leave_the_frame(client, dvd_film, monkeypatch):
    choose(monkeypatch, film=dvd_film)
    client.post("/api/choose-film")
    wait_for(client, "review")
    client.post("/api/nudge", json={"edge": "left", "pixels": -2})
    status = client.get("/api/status").get_json()
    assert status["crop"] == "720:360:0:60"
    assert "can't move" in status["error"]


def test_folder_with_frames_is_refused(client, dvd_film, tmp_path, monkeypatch):
    (tmp_path / "dvd_frames").mkdir()
    (tmp_path / "dvd_frames" / "frame_0001.png").touch()
    choose(monkeypatch, film=dvd_film, folder=tmp_path)
    client.post("/api/choose-film")
    wait_for(client, "review")
    status = client.post("/api/choose-folder").get_json()
    assert status["out_dir"] is None
    assert "already has frames" in status["error"]


def test_not_a_video_shows_a_message(client, tmp_path, monkeypatch):
    notes = tmp_path / "notes.txt"
    notes.write_text("not a film")
    choose(monkeypatch, film=notes)
    status = client.post("/api/choose-film").get_json()
    assert status["stage"] == "start"
    assert "Couldn't read" in status["error"]


def test_stopping_deletes_partial_frames_only(dvd_film, tmp_path):
    session = app_module.Session(tmp_path / "previews")
    session.choose_film(dvd_film)
    session.crop = Crop(720, 360, 0, 60)
    session.choose_folder(tmp_path)
    session.out_dir.mkdir()
    keep = session.out_dir / "notes.txt"  # a student's own file in the folder
    keep.write_text("mine")

    session.stop_requested.set()  # as if Cancel was confirmed
    session.run_extraction()

    assert session.stage == "review"
    assert "stopped" in session.error
    assert not list(session.out_dir.glob("frame_*.png"))
    assert keep.exists()


def test_stopping_removes_the_folder_it_made(dvd_film, tmp_path):
    session = app_module.Session(tmp_path / "previews")
    session.choose_film(dvd_film)
    session.crop = Crop(720, 360, 0, 60)
    session.choose_folder(tmp_path)
    session.stop_requested.set()
    session.run_extraction()
    assert not session.out_dir.exists()


def test_plain_descriptions():
    assert app_module.nudged(Crop(720, 360, 0, 60), "bottom", 2) == Crop(720, 358, 0, 60)
    assert app_module.nudged(Crop(720, 360, 0, 60), "right", -2) == Crop(722, 360, 0, 60)
    assert app_module.gb(1.2e9) == "1.2 GB"
    assert app_module.gb(250e6) == "250 MB"


def test_full_res_offered_for_bluray(tmp_path, monkeypatch):
    film = tmp_path / "bluray.mkv"
    make_film(film, "1920x800", "1920x1080", "0:140", seconds=10)
    flask_app = app_module.create_app(preview_root=tmp_path / "previews")
    client = flask_app.test_client()
    choose(monkeypatch, film=film)
    client.post("/api/choose-film")
    status = wait_for(client, "review")
    assert status["film"]["kind"] == "HD (Blu-ray size)"
    assert status["can_full_res"]
    assert status["frame_size"] == "853 × 356"
    status = client.post("/api/size", json={"full_res": True}).get_json()
    assert status["frame_size"] == "1920 × 800"


def test_going_back_to_choose_film_keeps_work_until_a_new_film(client, dvd_film, tmp_path, monkeypatch):
    choose(monkeypatch, film=dvd_film)
    client.post("/api/choose-film")
    wait_for(client, "review")
    client.post("/api/nudge", json={"edge": "top", "pixels": 2})

    # The student closes the Finder window without choosing
    choose(monkeypatch, film=None)
    status = client.post("/api/choose-film").get_json()
    assert status["stage"] == "review"
    assert status["crop"] == "720:358:0:62"

    # The student picks something that isn't a video
    notes = tmp_path / "notes.txt"
    notes.write_text("not a film")
    choose(monkeypatch, film=notes)
    status = client.post("/api/choose-film").get_json()
    assert status["stage"] == "review"
    assert status["crop"] == "720:358:0:62"
    assert "Couldn't read" in status["error"]
