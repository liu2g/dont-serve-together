# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the standalone executable.

Build (per platform -- PyInstaller cannot cross-compile, so run this on each
target OS with the same command):

    uv run pyinstaller dont_serve_together.spec --noconfirm

The single-file executable lands in dist/ (dont-serve-together.exe on
Windows, dont-serve-together on macOS/Linux).
"""

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

# Textual and its add-ons load widgets and drivers lazily, which static
# analysis cannot see -- collect every submodule.
hiddenimports = [
    *collect_submodules("textual"),
    *collect_submodules("textual_diff_view"),
    *collect_submodules("textual_fspicker"),
]

# textual_fspicker reads its own version from package metadata at import time
# (a crash if missing), and the Welcome screen shows this project's version
# the same way.
datas = [
    *copy_metadata("dont-serve-together"),
    *copy_metadata("textual"),
    *copy_metadata("textual-diff-view"),
    *copy_metadata("textual-fspicker"),
]

a = Analysis(
    ["dont_serve_together/__main__.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="dont-serve-together",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # The TUI needs a terminal. On Windows this makes the executable launch
    # with (or attach to) a console; on macOS it skips the .app bundle so the
    # binary runs in the terminal that starts it; on Linux it has no effect.
    console=True,
)
