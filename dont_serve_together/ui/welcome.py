"""The Welcome screen: program name, version, and cluster folder selection."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Static
from textual_fspicker import SelectDirectory

from dont_serve_together.cluster import ClusterLoadError, load_cluster
from dont_serve_together.ui import pickers
from dont_serve_together.ui.cluster_view import ClusterViewScreen

ASCII_ART = r"""
   ____               o                                 ______                _               
  (|   \              /        ()                      (_) |                 | |              
   |    | __   _  _    _|_     /\  _   ,_         _        | __   __,  _ _|_ | |     _   ,_   
  _|    |/  \_/ |/ |    |     /  \|/  /  |  |  |_|/      _ |/  \_/  | |/  |  |/ \   |/  /  |  
 (/\___/ \__/   |  |_/  |_/  /(__/|__/   |_/ \/  |__/   (_/ \__/ \_/|/|__/|_/|   |_/|__/   |_/
                                                                   /|                         
                                                                   \|                         
"""
# Generated with https://patorjk.com/software/taag using the "Script" font

def _app_version() -> str:
    try:
        return version("dont-serve-together")
    except PackageNotFoundError:
        return "unknown"


class WelcomeScreen(Screen[None]):
    """First screen at launch: pick a cluster folder to manage."""

    DEFAULT_CSS = """
    WelcomeScreen {
        align: center middle;
    }
    WelcomeScreen #welcome-box {
        width: auto;
        height: auto;
    }
    WelcomeScreen #app-name {
        width: auto;
        text-style: bold;
    }
    WelcomeScreen #app-version {
        width: 1fr;
        text-align: center;
        color: $text-muted;
    }
    WelcomeScreen Button {
        margin-top: 1;
    }
    WelcomeScreen #welcome-error {
        width: 1fr;
        margin-top: 1;
        text-align: center;
        color: $text-error;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the program name, version, Browse button, and error line."""
        with Vertical(id="welcome-box"):
            with Center():
                yield Static(Text(ASCII_ART.strip("\n")), id="app-name")
            yield Static(f"version {_app_version()}", id="app-version")
            with Center():
                yield Button("Browse cluster folder", id="browse", variant="primary")
            yield Static("", id="welcome-error")
        yield Footer()

    @on(Button.Pressed, "#browse")
    def _browse(self) -> None:
        self.app.push_screen(
            SelectDirectory(location=pickers.start_location(), title="Select a cluster folder"),
            callback=self._folder_picked,
        )

    def _folder_picked(self, picked: Path | None) -> None:
        if picked is None:
            return
        error = self.query_one("#welcome-error", Static)
        try:
            cluster = load_cluster(picked)
        except ClusterLoadError as exc:
            error.update(Text(f"Not a valid cluster: {exc}"))
            return
        error.update("")
        pickers.remember_pick(picked)
        self.app.push_screen(ClusterViewScreen(cluster), callback=self._cluster_closed)

    def _cluster_closed(self, error: str | None) -> None:
        if error is not None:
            self.query_one("#welcome-error", Static).update(Text(error))
