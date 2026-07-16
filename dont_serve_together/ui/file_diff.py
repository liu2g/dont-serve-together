"""The File Diff screen: preview and apply a level overwrite or mod merge."""

from __future__ import annotations

from enum import Enum, auto
from pathlib import Path
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Static
from textual_diff_view import DiffView
from textual_fspicker import FileOpen, Filters

from dont_serve_together.cluster import (
    Cluster,
    ClusterLoadError,
    PickedFileError,
    Shard,
    load_cluster,
    prepare_level_overwrite,
    prepare_mod_merge,
    write_config_text,
)
from dont_serve_together.ui import pickers


class DiffMode(Enum):
    """A kind of change the File Diff screen can preview and apply."""

    OVERWRITE_LEVEL = auto()
    """Replace one shard's ``leveldataoverride.lua`` with a picked file."""

    APPEND_MODS = auto()
    """Merge a picked mod list into the cluster-wide ``modoverrides.lua``."""


class FileDiffScreen(Screen[Cluster | None]):
    """Diff preview for one mode; dismisses with the reloaded cluster on Apply.

    Everything mode-specific (title, source file, write targets, preview
    builder) is resolved by matching on the :class:`DiffMode` -- adding a new
    mode means adding an enum member and extending those matches.
    """

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    FileDiffScreen #diff-title {
        width: 1fr;
        padding: 0 1;
        text-style: bold;
        background: $panel;
    }
    FileDiffScreen #pick-row {
        height: auto;
        padding: 0 1;
        margin-top: 1;
    }
    FileDiffScreen #picked-path {
        width: 1fr;
        height: 3;
        padding: 0 1;
        border: round $primary;
        color: $text-muted;
    }
    FileDiffScreen #pick-row Button {
        margin-left: 1;
    }
    FileDiffScreen #pick-error {
        width: 1fr;
        padding: 0 1;
        color: $text-error;
    }
    FileDiffScreen #diff-scroll {
        margin: 0 1;
    }
    FileDiffScreen #actions {
        height: auto;
        padding: 0 1 1 1;
        align-horizontal: center;
    }
    FileDiffScreen #actions Button {
        margin: 0 2;
    }
    """

    def __init__(self, cluster: Cluster, mode: DiffMode, shard: Shard | None = None) -> None:
        """Initialize the screen for one mode.

        Args:
            cluster: The loaded cluster being managed.
            mode: The kind of change to preview and apply.
            shard: The shard the mode targets; required by
                ``OVERWRITE_LEVEL``, forbidden for cluster-wide modes.

        Raises:
            ValueError: If ``shard`` does not match what ``mode`` needs.
        """
        super().__init__()
        self._cluster = cluster
        self._mode = mode
        match mode:
            case DiffMode.OVERWRITE_LEVEL:
                if shard is None:
                    raise ValueError("OVERWRITE_LEVEL requires a shard")
                self._title_text = f"Overwriting level settings for shard: {shard.name}"
                source = shard.level_data
                self._write_paths = [source.path]
            case DiffMode.APPEND_MODS:
                if shard is not None:
                    raise ValueError("APPEND_MODS applies cluster-wide and does not take a shard")
                self._title_text = "Appending mod list for cluster"
                source = cluster.shards[0].mod_overrides
                self._write_paths = [each.mod_overrides.path for each in cluster.shards]
        self._original_path = source.path
        self._original_text = source.raw_text
        self._new_text: str | None = None

    def _build_preview(self, picked: Path) -> str:
        """Build the right-panel text for a picked file.

        Args:
            picked: The user-picked file.

        Returns:
            The text that Apply would write.

        Raises:
            PickedFileError: If the picked file is not valid for the mode.
        """
        match self._mode:
            case DiffMode.OVERWRITE_LEVEL:
                return prepare_level_overwrite(picked)
            case DiffMode.APPEND_MODS:
                return prepare_mod_merge(self._original_text, picked)

    @property
    def _target_name(self) -> str:
        return self._original_path.name

    def compose(self) -> ComposeResult:
        """Compose the title, picker row, diff view, and action buttons."""
        yield Static(Text(self._title_text), id="diff-title")
        with Horizontal(id="pick-row"):
            yield Static("(no file selected)", id="picked-path")
            yield Button(f"Browse {self._target_name}…", id="browse")
        yield Static("", id="pick-error")
        yield VerticalScroll(id="diff-scroll")
        with Horizontal(id="actions"):
            yield Button("Apply Changes", id="apply", variant="primary", disabled=True)
            yield Button("Cancel", id="cancel")
        yield Footer()

    async def on_mount(self) -> None:
        """Show the initial diff: both sides are the original file content."""
        await self._show_diff(self._original_path, self._original_text)

    async def _show_diff(self, modified_path: Path, modified_text: str) -> None:
        view = DiffView(
            self._original_path.as_posix(),
            modified_path.as_posix(),
            self._original_text,
            modified_text,
            split=True,
        )
        await view.prepare()
        container = self.query_one("#diff-scroll", VerticalScroll)
        await container.remove_children()
        await container.mount(view)

    @on(Button.Pressed, "#browse")
    def _browse(self) -> None:
        target = self._target_name
        self.app.push_screen(
            FileOpen(
                location=pickers.start_location(),
                title=f"Select a {target} file",
                filters=Filters(
                    (target, lambda path: path.name.lower() == target),
                    ("All files", lambda path: True),
                ),
            ),
            callback=self._file_picked,
        )

    async def _file_picked(self, picked: Path | None) -> None:
        if picked is None:
            return
        error = self.query_one("#pick-error", Static)
        try:
            new_text = self._build_preview(picked)
        except PickedFileError as exc:
            error.update(Text(str(exc)))
            return
        error.update("")
        pickers.remember_pick(picked)
        self._new_text = new_text
        self.query_one("#picked-path", Static).update(Text(picked.as_posix()))
        self.query_one("#apply", Button).disabled = False
        await self._show_diff(picked, new_text)

    @on(Button.Pressed, "#apply")
    def _apply(self) -> None:
        if self._new_text is None:
            return
        error = self.query_one("#pick-error", Static)
        try:
            for path in self._write_paths:
                write_config_text(path, self._new_text)
            reloaded = load_cluster(self._cluster.path)
        except (OSError, ClusterLoadError) as exc:
            error.update(Text(f"Apply failed: {exc}"))
            return
        self.dismiss(reloaded)

    @on(Button.Pressed, "#cancel")
    def _cancel(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        """Discard the preview and go back to the Cluster View screen."""
        self.dismiss(None)
