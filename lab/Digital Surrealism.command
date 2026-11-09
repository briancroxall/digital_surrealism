#!/bin/bash
# Double-click this file to open the Digital Surrealism frame extractor.
# It runs `digital-surrealism app` from the repo this file lives in.
# See lab/INSTALL.md for setting up a Mac.

# Programs started from Finder don't get the usual command-line PATH, so add
# the places Homebrew and the uv installer put things.
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"

# Each Mac account gets its own copy of Python and Flask, kept out of the repo
# folder so the repo can be shared read-only (for example, in /Users/Shared).
export UV_PROJECT_ENVIRONMENT="$HOME/Library/Caches/digital-surrealism/venv"

repo="$(cd "$(dirname "$0")/.." && pwd)"

stop() {
    echo
    echo "$1"
    echo "Ask your instructor for help. (Setup instructions: lab/INSTALL.md"
    echo "in the digital_surrealism folder.)"
    echo
    read -r -p "Press Return to close this window."
    exit 1
}

[ -f "$repo/pyproject.toml" ] || stop "This launcher has to stay in the lab folder inside the
digital_surrealism folder. To put it on the Desktop, make an alias
(Option-Command-drag) instead of a copy."
command -v ffmpeg >/dev/null || stop "ffmpeg isn't installed on this Mac."
command -v uv >/dev/null || stop "uv isn't installed on this Mac."

if [ ! -d "$UV_PROJECT_ENVIRONMENT" ]; then
    echo "First time on this Mac account: setting up. This takes a minute or so"
    echo "and needs an internet connection."
    echo
fi

uv run --project "$repo" --frozen --no-dev digital-surrealism app \
    || stop "The extractor stopped with an error (see above)."
