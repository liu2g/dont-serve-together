"""The Cluster View screen: cluster info, warnings, and the action menu."""

from __future__ import annotations

from typing import ClassVar

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Footer, OptionList, Static
from textual.widgets.option_list import Option

from dont_serve_together.cluster import Cluster, Shard
from dont_serve_together.ui.file_diff import DiffMode, FileDiffScreen


def _warnings(cluster: Cluster) -> list[str]:
    """Collect the display-only warnings for the Cluster Info box."""
    warnings: list[str] = []
    if cluster.cluster_token is None:
        warnings.append("No cluster_token.txt -- the cluster cannot be hosted as a dedicated server without it.")
    if any((shard.path / "save").is_dir() for shard in cluster.shards):
        warnings.append("This cluster has been played -- changing cluster settings may break the save files.")
    masters = [shard.name for shard in cluster.shards if shard.is_master]
    if not masters:
        warnings.append("No shard declares is_master = true -- the cluster cannot run as-is.")
    elif len(masters) > 1:
        warnings.append(f"Multiple master shards ({', '.join(masters)}) -- the cluster cannot run as-is.")
    return warnings


def _shard_label(shard: Shard) -> str:
    """Return a shard's menu/info label: folder name, world location, master role."""
    location = shard.level_data.location or "unknown world"
    role = ", master" if shard.is_master else ""
    return f"{shard.name} ({location}{role})"


class ClusterViewScreen(Screen[None]):
    """Cluster info in a rounded box, then the action menu."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "back", "Back")]

    DEFAULT_CSS = """
    ClusterViewScreen {
        align: center top;
    }
    ClusterViewScreen #cluster-info {
        width: 90%;
        margin: 1 0;
        padding: 0 1;
        border: round $primary;
        border-title-color: $text;
    }
    ClusterViewScreen #menu {
        width: 90%;
        height: auto;
    }
    """

    def __init__(self, cluster: Cluster) -> None:
        """Initialize the screen for a loaded cluster.

        Args:
            cluster: The cluster snapshot to display.
        """
        super().__init__()
        self._cluster = cluster

    def compose(self) -> ComposeResult:
        """Compose the Cluster Info box and the action menu."""
        info = Static(self._info_text(), id="cluster-info")
        info.border_title = "Cluster Info"
        yield info
        yield OptionList(
            Option("Overwrite level settings", id="level"),
            Option("Append mod list", id="mods"),
            Option("Open another cluster", id="open"),
            Option("Quit", id="quit"),
            id="menu",
        )
        yield Footer()

    def _info_text(self) -> Text:
        cluster = self._cluster
        name = cluster.cluster_ini.cluster_name or cluster.name
        enabled_mods = sum(entry.enabled for entry in cluster.shards[0].mod_overrides.entries)
        shard_labels = ", ".join(_shard_label(shard) for shard in cluster.shards)

        text = Text()
        text.append(name, style="bold")
        text.append(f"\n{cluster.path.as_posix()}", style="dim")
        text.append(f"\nShards ({len(cluster.shards)}): {shard_labels}")
        text.append(f"\nEnabled mods: {enabled_mods}")
        for warning in _warnings(cluster):
            text.append(f"\n⚠ {warning}", style="yellow")
        return text

    @on(OptionList.OptionSelected, "#menu")
    def _menu_selected(self, event: OptionList.OptionSelected) -> None:
        match event.option_id:
            case "level":
                self.app.push_screen(ShardSelectScreen(self._cluster), callback=self._shard_chosen)
            case "mods":
                self.app.push_screen(
                    FileDiffScreen(self._cluster, DiffMode.APPEND_MODS), callback=self._diff_closed
                )
            case "open":
                self.app.pop_screen()
            case "quit":
                self.app.exit()

    def _shard_chosen(self, shard: Shard | None) -> None:
        if shard is not None:
            self.app.push_screen(
                FileDiffScreen(self._cluster, DiffMode.OVERWRITE_LEVEL, shard=shard),
                callback=self._diff_closed,
            )

    def _diff_closed(self, cluster: Cluster | None) -> None:
        if cluster is not None:
            self._cluster = cluster
            self.refresh(recompose=True)

    def action_back(self) -> None:
        """Go back to the Welcome screen."""
        self.app.pop_screen()


class ShardSelectScreen(ModalScreen[Shard | None]):
    """Submenu to pick the shard whose level settings will be overwritten."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    ShardSelectScreen {
        align: center middle;
    }
    ShardSelectScreen #shard-box {
        width: 60;
        height: auto;
        padding: 0 1;
        border: round $primary;
        border-title-color: $text;
    }
    ShardSelectScreen OptionList {
        height: auto;
    }
    """

    def __init__(self, cluster: Cluster) -> None:
        """Initialize the shard submenu.

        Args:
            cluster: The cluster whose shards are offered.
        """
        super().__init__()
        self._cluster = cluster

    def compose(self) -> ComposeResult:
        """Compose the shard list."""
        box = Vertical(
            OptionList(
                *[Option(Text(_shard_label(shard)), id=shard.name) for shard in self._cluster.shards],
                id="shard-menu",
            ),
            id="shard-box",
        )
        box.border_title = "Select shard"
        yield box

    @on(OptionList.OptionSelected, "#shard-menu")
    def _shard_selected(self, event: OptionList.OptionSelected) -> None:
        shard = self._cluster.shard(event.option_id or "")
        self.dismiss(shard)

    def action_cancel(self) -> None:
        """Close the submenu without picking a shard."""
        self.dismiss(None)
