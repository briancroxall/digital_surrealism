"""Web interface for the frame extractor.

Runs a small Flask server on this Mac only (127.0.0.1) and opens it in the
browser. The page walks a student through: choose film -> check crop ->
choose size -> choose where to save -> extract.

The page asks the server for its status about once a second. Slow work
(finding the black bars, extracting frames) runs in a background thread, so
the page stays responsive. One student per Mac at a time: the server keeps a
single Session.
"""

import shutil
import socket
import subprocess
import tempfile
import threading
import time
import webbrowser
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

from .crop import Crop, CropResult, detect_crop, is_plausible, render_previews
from .extract import (
    DVD_HEIGHT,
    ExtractionStopped,
    expected_frames,
    extract_frames,
    output_size,
)
from .media import VideoInfo, probe

PORT = 5150  # avoids 5000, which macOS uses for AirPlay
NUDGE_PIXELS = 2
# Rough PNG size, from a real DVD: 3,442 frames at 853 x 360 took 1.2 GB.
BYTES_PER_PIXEL = 1.15
# Set once the Image maker is published (step 4).
IMAGE_MAKER_URL = None


# --- Finder dialogs (macOS) -------------------------------------------------

def ask_for_file() -> Path | None:
    """Open a Finder window to choose the film. None if the student cancels."""
    return _ask("choose file with prompt \"Choose the film (the MKV file from MakeMKV):\""
                " default location (path to movies folder)")


def ask_for_folder() -> Path | None:
    """Open a Finder window to choose where frames go. None if cancelled."""
    return _ask("choose folder with prompt \"Choose where to save the frames:\""
                " default location (path to desktop folder)")


def _ask(choose: str) -> Path | None:
    # "activate" brings the dialog in front of the browser.
    result = subprocess.run(
        ["osascript", "-e", "activate", "-e", f"POSIX path of ({choose})"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:  # cancelled
        return None
    return Path(result.stdout.strip())


# --- Describing things in plain language -------------------------------------

def describe_film(path: Path, info: VideoInfo) -> dict:
    if info.height >= 720:
        kind = "HD (Blu-ray size)"
    elif info.height in (480, 576):
        kind = "DVD"
    else:
        kind = "video"
    shape = info.display_width / info.height
    if abs(shape - 16 / 9) < 0.05:
        shape_text = "widescreen (16:9)"
    elif abs(shape - 4 / 3) < 0.05:
        shape_text = "standard (4:3)"
    else:
        shape_text = f"{shape:.2f}:1"
    return {
        "name": path.name,
        "path": str(path),
        "kind": kind,
        "stored": f"{info.width} × {info.height}",
        "shape": shape_text,
        "minutes": round(info.duration / 60, 1),
    }


def margins(crop: Crop, info: VideoInfo) -> dict:
    """How many stored pixels are cut from each edge."""
    return {
        "top": crop.y,
        "bottom": info.height - crop.y - crop.h,
        "left": crop.x,
        "right": info.width - crop.x - crop.w,
    }


def nudged(crop: Crop, edge: str, pixels: int) -> Crop:
    """Move one edge of the crop. Positive pixels cut more off that edge."""
    x, y, w, h = crop.x, crop.y, crop.w, crop.h
    if edge == "top":
        y, h = y + pixels, h - pixels
    elif edge == "bottom":
        h -= pixels
    elif edge == "left":
        x, w = x + pixels, w - pixels
    elif edge == "right":
        w -= pixels
    else:
        raise ValueError(f"Unknown edge: {edge}")
    return Crop(w, h, x, y)


# --- The student's session ---------------------------------------------------

class Session:
    """Everything about the current film, from choosing it to extraction.

    Stages: "start" -> "detecting" -> "review" -> "extracting" -> "done".
    Errors return to an earlier stage with a message in `error`.
    """

    def __init__(self, preview_root: Path):
        self.preview_root = preview_root
        self.lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        self.stage = "start"
        self.error = None
        self.film: Path | None = None
        self.info: VideoInfo | None = None
        self.detection: CropResult | None = None
        self.crop: Crop | None = None
        self.previews_version = 0
        self.full_res = False
        self.out_dir: Path | None = None
        self.progress = 0.0
        self.started_at = None
        self.stop_requested = threading.Event()
        self.frame_count = None

    # Choosing the film and finding the bars

    def choose_film(self, film: Path) -> None:
        """Start over with a new film. A file that isn't a video changes nothing."""
        try:
            info = probe(film)
        except (subprocess.CalledProcessError, ValueError, KeyError):
            self.error = f"Couldn't read {film.name} as a video. Choose the MKV file from MakeMKV."
            return
        self.reset()
        self.film, self.info = film, info
        self.stage = "detecting"

    def run_detection(self) -> None:
        try:
            self.detection = detect_crop(self.film, self.info)
            self.set_crop(self.detection.crop)
            self.stage = "review"
        except Exception as error:  # show any failure on the page
            self.error = f"Something went wrong looking for the black bars: {error}"
            self.stage = "start"

    def set_crop(self, crop: Crop) -> None:
        """Use this crop and redraw the previews into a fresh folder."""
        self.previews_version += 1
        folder = self.preview_root / str(self.previews_version)
        render_previews(self.film, self.info, crop, folder)
        shutil.rmtree(self.preview_root / str(self.previews_version - 1), ignore_errors=True)
        self.crop = crop

    def nudge(self, edge: str, pixels: int) -> None:
        new = nudged(self.crop, edge, pixels)
        if not is_plausible(new, self.info):
            self.error = "The crop can't move any further that way."
            return
        self.error = None
        self.set_crop(new)

    # Size and where to save

    def frame_size(self) -> tuple[int, int]:
        return output_size(self.info, self.crop, self.full_res)

    def estimated_bytes(self) -> int:
        width, height = self.frame_size()
        return round(width * height * BYTES_PER_PIXEL * expected_frames(self.info))

    def choose_folder(self, parent: Path) -> None:
        out_dir = parent / f"{self.film.stem}_frames"
        if any(out_dir.glob("frame_*.png")):
            self.error = (f"{out_dir} already has frames in it. Choose a different "
                          "place, or delete that folder first.")
            self.out_dir = None
            return
        self.error = None
        self.out_dir = out_dir

    def space_warning(self) -> str | None:
        if self.out_dir is None:
            return None
        existing = self.out_dir if self.out_dir.exists() else self.out_dir.parent
        free = shutil.disk_usage(existing).free
        if free < self.estimated_bytes() * 1.2:
            return (f"This disk may not have enough room: about {gb(free)} free, and "
                    f"the frames need roughly {gb(self.estimated_bytes())}.")
        return None

    # Extracting

    def run_extraction(self) -> None:
        self.stage = "extracting"
        self.started_at = time.monotonic()
        try:
            self.frame_count = extract_frames(
                self.film, self.info, self.crop, self.out_dir, self.full_res,
                on_progress=self.set_progress,
                should_stop=self.stop_requested.is_set,
            )
            self.stage = "done"
        except FileExistsError as error:  # not our frames: leave them alone
            self.error = str(error)
            self.out_dir = None
            self.stage = "review"
        except ExtractionStopped:
            self.delete_partial_frames()
            self.error = "Extraction stopped. The partial frames were deleted."
            self.stage = "review"
        except Exception as error:  # e.g., the disk filled up
            self.delete_partial_frames()
            self.error = (f"Extraction failed, so the partial frames were deleted. "
                          f"The error was: {error}")
            self.stage = "review"
        self.stop_requested.clear()

    def set_progress(self, fraction: float) -> None:
        self.progress = fraction

    def delete_partial_frames(self) -> None:
        """Delete only our frame files, then the folder if nothing else is in it."""
        for frame in self.out_dir.glob("frame_*.png"):
            frame.unlink()
        try:
            self.out_dir.rmdir()
        except OSError:  # missing, or holds the student's other files
            pass

    def frames_saved(self) -> int:
        if self.out_dir is None or not self.out_dir.exists():
            return 0
        return sum(1 for _ in self.out_dir.glob("frame_*.png"))

    def seconds_left(self) -> int | None:
        if self.stage != "extracting" or self.progress < 0.02:
            return None
        elapsed = time.monotonic() - self.started_at
        return round(elapsed / self.progress * (1 - self.progress))

    # Everything the page needs, as JSON

    def status(self) -> dict:
        status = {"stage": self.stage, "error": self.error,
                  "image_maker_url": IMAGE_MAKER_URL}
        if self.info is None:
            return status
        status["film"] = describe_film(self.film, self.info)
        if self.crop is not None:
            width, height = self.frame_size()
            status.update({
                "crop": str(self.crop),
                "margins": margins(self.crop, self.info),
                "detection": {
                    "crop": str(self.detection.crop),
                    "agreeing": self.detection.agreeing,
                    "usable": self.detection.usable,
                    "total": self.detection.total,
                    "confident": self.detection.confident,
                },
                "previews": [
                    {"boxed": f"/previews/{self.previews_version}/preview_{i}.png",
                     "cropped": f"/previews/{self.previews_version}/preview_{i}_cropped.png"}
                    for i in range(1, 7)
                ],
                "can_full_res": self.info.height > DVD_HEIGHT,
                "full_res": self.full_res,
                "frame_size": f"{width} × {height}",
                "frame_count": expected_frames(self.info),
                "estimate": gb(self.estimated_bytes()),
                "out_dir": str(self.out_dir) if self.out_dir else None,
                "space_warning": self.space_warning(),
            })
        if self.stage == "extracting":
            status["progress"] = {
                "fraction": self.progress,
                "frames_saved": self.frames_saved(),
                "seconds_left": self.seconds_left(),
            }
        if self.stage == "done":
            status["result"] = {"count": self.frame_count, "out_dir": str(self.out_dir)}
        return status


def gb(n_bytes: float) -> str:
    if n_bytes < 1e9:
        return f"{n_bytes / 1e6:.0f} MB"
    return f"{n_bytes / 1e9:.1f} GB"


# --- The web server ----------------------------------------------------------

def create_app(preview_root: Path | None = None) -> Flask:
    app = Flask(__name__)
    preview_root = preview_root or Path(tempfile.mkdtemp(prefix="digital-surrealism-"))
    session = Session(preview_root)
    app.config["SESSION"] = session

    def in_background(work) -> None:
        threading.Thread(target=work, daemon=True).start()

    def busy() -> bool:
        return session.stage in ("detecting", "extracting")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/status")
    def status():
        with session.lock:
            return jsonify(session.status())

    @app.post("/api/choose-film")
    def choose_film():
        if busy():
            abort(409)
        film = ask_for_file()
        with session.lock:
            if film is not None:
                session.choose_film(film)
                if session.stage == "detecting":
                    in_background(session.run_detection)
            return jsonify(session.status())

    @app.post("/api/nudge")
    def nudge():
        data = request.get_json()
        with session.lock:
            if session.stage != "review":
                abort(409)
            session.nudge(data["edge"], int(data["pixels"]))
            return jsonify(session.status())

    @app.post("/api/reset-crop")
    def reset_crop():
        with session.lock:
            if session.stage != "review":
                abort(409)
            session.error = None
            session.set_crop(session.detection.crop)
            return jsonify(session.status())

    @app.post("/api/size")
    def size():
        with session.lock:
            if session.stage != "review":
                abort(409)
            session.full_res = bool(request.get_json()["full_res"]) and session.info.height > DVD_HEIGHT
            return jsonify(session.status())

    @app.post("/api/choose-folder")
    def choose_folder():
        if session.stage != "review":
            abort(409)
        parent = ask_for_folder()
        with session.lock:
            if parent is not None:
                session.choose_folder(parent)
            return jsonify(session.status())

    @app.post("/api/extract")
    def extract():
        with session.lock:
            if session.stage != "review" or session.out_dir is None:
                abort(409)
            session.error = None
            session.stage = "extracting"
            session.progress = 0.0
            in_background(session.run_extraction)
            return jsonify(session.status())

    @app.post("/api/cancel")
    def cancel():
        if session.stage == "extracting":
            session.stop_requested.set()
        return jsonify({"ok": True})

    @app.post("/api/show-in-finder")
    def show_in_finder():
        if session.out_dir and session.out_dir.exists():
            subprocess.run(["open", str(session.out_dir)])
        return jsonify({"ok": True})

    @app.post("/api/start-over")
    def start_over():
        with session.lock:
            if busy():
                abort(409)
            session.reset()
            return jsonify(session.status())

    @app.get("/previews/<int:version>/<name>")
    def preview(version: int, name: str):
        return send_from_directory(preview_root / str(version), name, max_age=0)

    return app


def serve() -> None:
    """Start the server and open the page in the browser."""
    url = f"http://127.0.0.1:{PORT}"
    with socket.socket() as probe_socket:
        already_running = probe_socket.connect_ex(("127.0.0.1", PORT)) == 0
    if already_running:
        print(f"The extractor is already running. Opening {url}")
        webbrowser.open(url)
        return
    print(f"Digital Surrealism frame extractor: {url}")
    print("Leave this window open while you work. Press Control-C to quit.")
    threading.Timer(1.0, webbrowser.open, [url]).start()
    create_app().run(host="127.0.0.1", port=PORT, threaded=True)
