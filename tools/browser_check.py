"""Check the Image maker in a real browser against the Python reference.

    uv run tools/browser_check.py FRAMES_FOLDER
    uv run tools/browser_check.py FRAMES_FOLDER --browser manual

Serves the repository and the frames on http://127.0.0.1:8765, runs
web/worker.js on the frames in a browser, saves the browser's four images
(summed image and three barcodes), and compares each pixel by pixel with
tools/reference.py.

By default it uses headless Chrome. With --browser manual it prints a URL to
open yourself (for Safari or Firefox) and waits.
"""

import argparse
import json
import subprocess
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from reference import barcodes, frame_paths, summed_image  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
PORT = 8765
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def make_handler(frames: list[Path], out_dir: Path, finished: threading.Event):
    by_name = {path.name: path for path in frames}

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == "/frames/":
                body = json.dumps([path.name for path in frames]).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
            elif self.path.startswith("/frames/"):
                path = by_name.get(unquote(self.path[len("/frames/"):]))
                if path is None:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                self.wfile.write(path.read_bytes())
            else:
                if self.path.startswith("/fresh/"):  # /fresh/<number>/web/... -> /web/...
                    self.path = "/" + self.path.split("/", 3)[3]
                super().do_GET()

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            name = self.path.strip("/")
            (out_dir / name).write_bytes(body)
            self.send_response(200)
            self.end_headers()
            if name in ("info", "error"):
                finished.set()

        def end_headers(self):
            # Always send the current page code, never a browser's cached copy.
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def guess_type(self, path):
            if str(path).endswith(".js"):
                return "text/javascript"
            return super().guess_type(path)

    return partial(Handler, directory=str(REPO))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("frames", type=Path)
    parser.add_argument("--browser", choices=["chrome", "manual"], default="chrome")
    parser.add_argument("--out", type=Path, help="folder for the browser's output")
    args = parser.parse_args()

    frames = frame_paths(args.frames)
    out_dir = args.out or Path(tempfile.mkdtemp(prefix="image-maker-check-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    finished = threading.Event()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), make_handler(frames, out_dir, finished))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{PORT}/tools/browser_check.html"

    print(f"{len(frames)} frames from {args.frames}")
    browser = None
    if args.browser == "chrome":
        browser = subprocess.Popen(
            [CHROME, "--headless=new", f"--user-data-dir={out_dir / 'chrome-profile'}", url],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    else:
        print(f"Open this in the browser to test, and leave it open until this finishes:\n  {url}")
    try:
        finished.wait()
    finally:
        if browser:
            browser.terminate()
            browser.wait()
        server.shutdown()

    if (out_dir / "error").exists():
        sys.exit(f"The browser reported an error: {(out_dir / 'error').read_text()}")

    info = json.loads((out_dir / "info").read_text())
    reference_summed, ranges = summed_image(frames)
    references = {"summed": reference_summed, **barcodes(frames)}
    print(f"Browser: {info['userAgent']}")
    print(f"Browser time (reading + making images, after loading files): {info['seconds']:.1f} s")
    print(f"Frames used: {info['count']}")
    print(f"Frames with a colour label removed: {info.get('labelled', 'not reported (old page code?)')}")
    for name, got, want in zip("RGB", info["ranges"], ranges):
        print(f"  {name} range before stretching: browser {got['low']:.3f}-{got['high']:.3f}, "
              f"Python {want[0]:.3f}-{want[1]:.3f}")
    for kind, reference in references.items():
        got = np.asarray(Image.open(out_dir / f"{kind}.png").convert("RGB"), dtype=int)
        if got.shape != reference.shape:
            print(f"{kind:>10}: SIZE DIFFERS, browser {got.shape[1]} x {got.shape[0]}, "
                  f"Python {reference.shape[1]} x {reference.shape[0]}")
            continue
        diff = np.abs(got - reference.astype(int))
        print(f"{kind:>10}: {got.shape[1]} x {got.shape[0]}, values that differ: "
              f"{np.count_nonzero(diff)} of {diff.size}, largest difference {diff.max()}")
    print(f"Browser's images: {out_dir}")


if __name__ == "__main__":
    main()
