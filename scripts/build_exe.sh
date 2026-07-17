#!/usr/bin/env bash
set -euo pipefail

GREEN="\e[32m"
ENDCOLOR="\e[0m"

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

# PyInstaller cannot cross-compile -- run this on each target OS to produce that
# platform's binary. The single-file executable lands in dist/
# (dont-serve-together.exe on Windows, dont-serve-together on macOS/Linux).
#
# Flag notes:
# - --collect-submodules: Textual and its add-ons load widgets and drivers
#   lazily, which static analysis cannot see -- collect every submodule.
# - --copy-metadata: textual_fspicker reads its own version from package
#   metadata at import time (a crash if missing), and the Welcome screen shows
#   this project's version the same way.
# - --console: the TUI needs a terminal. On Windows this makes the executable
#   launch with (or attach to) a console; on macOS it skips the .app bundle so
#   the binary runs in the terminal that starts it; on Linux it has no effect.
# - --icon: embedded on Windows only; other platforms ignore it (regenerate
#   with scripts/png_to_ico.py when assets/logo.png changes).
# - --specpath: PyInstaller always generates a spec file; keep it out of the
#   repo by writing it into the gitignored build/ directory.
printf "${GREEN}==>${ENDCOLOR} Building standalone executable with PyInstaller\n"
uv run pyinstaller dont_serve_together/__main__.py \
    --name dont-serve-together \
    --onefile \
    --console \
    --noupx \
    --icon "$REPO_ROOT/assets/logo.ico" \
    --collect-submodules textual \
    --collect-submodules textual_diff_view \
    --collect-submodules textual_fspicker \
    --copy-metadata dont-serve-together \
    --copy-metadata textual \
    --copy-metadata textual-diff-view \
    --copy-metadata textual-fspicker \
    --specpath build \
    --noconfirm
