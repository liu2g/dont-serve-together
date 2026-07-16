"""The File Diff screen: preview and apply a level overwrite or mod merge."""

from __future__ import annotations

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


class FileDiffScreen(Screen[Cluster | None]):
    """Diff preview for one operation; dismisses with the reloaded cluster on Apply.

    With a ``shard``, the screen overwrites that shard's
    ``leveldataoverride.lua``; without one, it merges a picked mod list into
    the cluster-wide ``modoverrides.lua``.
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

    def __init__(self, cluster: Cluster, shard: Shard | None = None) -> None:
        """Initialize the screen for one operation.

        Args:
            cluster: The loaded cluster being managed.
            shard: The shard whose level settings are overwritten, or ``None``
                for the cluster-wide mod-list merge.
        """
        super().__init__()
        self._cluster = cluster
        self._shard = shard
        if shard is not None:
            self._original_path = shard.level_data.path
            self._original_text = shard.level_data.raw_text
        else:
            self._original_path = cluster.shards[0].mod_overrides.path
            self._original_text = cluster.shards[0].mod_overrides.raw_text
        self._new_text: str | None = None

    @property
    def _title_text(self) -> str:
        if self._shard is not None:
            return f"Overwriting level settings for shard: {self._shard.name}"
        return "Appending mod list for cluster"

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
            if self._shard is not None:
                new_text = prepare_level_overwrite(picked)
            else:
                new_text = prepare_mod_merge(self._original_text, picked)
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
            if self._shard is not None:
                write_config_text(self._shard.level_data.path, self._new_text)
            else:
                for shard in self._cluster.shards:
                    write_config_text(shard.mod_overrides.path, self._new_text)
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
