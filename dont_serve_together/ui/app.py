"""The Textual application shell."""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path
from typing import ClassVar

from textual.app import App, SystemCommand
from textual.binding import Binding, BindingType
from textual.screen import Screen
from textual_fspicker import SelectDirectory

from dont_serve_together import mods_setup
from dont_serve_together.ui.welcome import WelcomeScreen


class DontServeTogetherApp(App[None]):
    """GUI manager for Don't Starve Together dedicated-server clusters."""

    TITLE = "Don't Serve Together"
    BINDINGS: ClassVar[list[BindingType]] = [Binding("ctrl+q", "quit", "Quit", priority=True)]

    # Flatten the default raised-button bevel (whose lightened top edge reads
    # as a white bar on primary buttons) and keep focus indication as bold
    # text instead of reverse video.
    CSS = """
    Button.-primary {
        border-top: tall $primary;
        border-bottom: tall $primary;
    }
    Button:focus {
        text-style: bold;
    }
    """

    def get_default_screen(self) -> WelcomeScreen:
        """Return the Welcome screen as the base of the screen stack."""
        return WelcomeScreen()

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        """Add "Set Game Directory" to the command palette on every screen."""
        yield from super().get_system_commands(screen)
        yield SystemCommand(
            "Set Game Directory",
            f"Select the game install directory holding mods/{mods_setup.MODS_SETUP_NAME}",
            self._set_game_directory,
        )

    def _set_game_directory(self) -> None:
        """Open a folder picker for the game directory.

        Deliberately independent of the shared picker start location: browsing
        starts at the drive/home root, and the pick is not remembered for the
        cluster file pickers.
        """
        start = Path("C:/") if sys.platform == "win32" else Path.home()
        self.push_screen(
            SelectDirectory(location=start, title="Select the game directory"),
            callback=self._game_directory_picked,
        )

    def _game_directory_picked(self, picked: Path | None) -> None:
        """Store the picked game directory for the session, accepted silently."""
        if picked is not None:
            mods_setup.set_game_directory(picked)
