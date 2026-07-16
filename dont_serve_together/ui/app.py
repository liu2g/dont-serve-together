"""The Textual application shell."""

from __future__ import annotations

from typing import ClassVar

from textual.app import App
from textual.binding import Binding, BindingType

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
