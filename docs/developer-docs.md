# Developer Documentation

This document explains how the program works to a developer new to the codebase: the development workflows (checks and executable builds), the UI flow, the behaviors behind each screen, and the handling of the game's `dedicated_server_mods_setup.lua`.
For what the project *is* and the workflow it automates, start with the [README](../README.md);
for how to contribute, see the [contributing guide](../CONTRIBUTING.md).
The on-disk formats of the cluster files the tool reads and writes are specified in [cluster-formats.md](cluster-formats.md).

## Development checks

`scripts/check.sh` is a convenience wrapper around the format, lint, and test commands.
Run it before committing:

```bash
./scripts/check.sh            # run everything: format, lint, and tests
./scripts/check.sh --format   # ruff format and import sorting only
./scripts/check.sh --lint     # ruff check and pyright only
./scripts/check.sh --test     # pytest only
```

With no flags it runs all three stages; the flags select individual stages, and `--all` is the explicit form of the default.

## Building the standalone executable

`scripts/build_exe.sh` builds a single-file executable with PyInstaller into `dist/` (`dont-serve-together.exe` on Windows, `dont-serve-together` on macOS/Linux):

```bash
./scripts/build_exe.sh
```

- All PyInstaller options live in the script, with a comment explaining each non-obvious flag; no spec file is checked in (PyInstaller writes the generated spec into the gitignored `build/` directory).
- The script runs on every platform, but PyInstaller cannot cross-compile: run the build on each target OS to produce that platform's binary.
- Two resources are embedded on Windows only; the other platforms ignore the corresponding options:
  - The icon, `assets/logo.ico`.
    Regenerate it with `scripts/png_to_ico.py` when `assets/logo.png` changes.
  - The version resource (what Explorer shows under Properties → Details: name, version, description, author, copyright).
    The build script generates it fresh on every build by running `scripts/gen_version_file.py`, which reads `pyproject.toml` (plus the `Copyright ...` line of `LICENSE`) and writes `build/file_version_info.txt` for PyInstaller's `--version-file` option.
    `pyproject.toml` therefore stays the single source of truth; nothing here needs a manual update for a release.
    One representational limit: Windows stores the file version as four integers, so a pre-release suffix (the `rc1` in `0.2.0rc1`) is dropped from the numeric version and appears only in the string fields.

## Code map

The UI is built with the Textual library.

| Module | Role |
| --- | --- |
| `dont_serve_together/ui/app.py` | Textual application shell; hosts the "Set Game Directory" palette command |
| `dont_serve_together/ui/welcome.py` | Welcome screen: version, cluster folder selection |
| `dont_serve_together/ui/cluster_view.py` | Cluster View screen: info box, warnings, action menu, shard selection |
| `dont_serve_together/ui/file_diff.py` | File Diff screen: preview and apply the two pipeline operations |
| `dont_serve_together/ui/pickers.py` | Session-global start location shared by the cluster file pickers |
| `dont_serve_together/cluster/model.py` | Pydantic models for a loaded cluster |
| `dont_serve_together/cluster/loader.py` | Loads and validates a cluster directory into the model |
| `dont_serve_together/cluster/luadata.py` | Parser and serializer for Klei's Lua data-literal files |
| `dont_serve_together/cluster/inidata.py` | Tolerant, read-only INI reader |
| `dont_serve_together/cluster/operations.py` | The two pipeline operations: level overwrite and mod merge |
| `dont_serve_together/mods_setup.py` | Checking and populating `dedicated_server_mods_setup.lua` |

## Global UI conventions

- File paths are always displayed with forward slashes (`/`), even on Windows.
- All *cluster* file pickers start browsing at a location stored as a session-global variable (`ui/pickers.py`):
  - Its initial value is the game data directory: `~/Documents/Klei/DoNotStarveTogether/` on Windows/macOS, `~/.klei/DoNotStarveTogether/` on Linux.
    If that location does not exist, it falls back to the user's home directory.
  - After every successful pick, the global updates to the picked file's directory, so subsequent pickers resume there.
    The value is not persisted across program runs.
  - The "Set Game Directory" picker is the exception -- see [Setting the game directory](#setting-the-game-directory).
- Byte-level comparison happens in exactly one place: the cross-shard `modoverrides.lua` identity check during cluster validation.
  Those files must be byte-identical to be seen as "one file" across the entire cluster.
  Everything else is judged at parse/model level, never by bytes.

## Welcome screen

The first screen at launch.
It shows the program name, the version (read from package metadata, not hardcoded), and a "Browse cluster folder" button.
There is no text box; selection happens exclusively through the picker.
Every Browse button in the program is labeled with what it picks.

When a cluster folder is selected, the program loads and validates it (`cluster/loader.py`).
If invalid, an inline error message describing the problem is shown, and the user can browse again.
If valid, the program continues to the Cluster View screen.

A valid cluster folder must have:

- a `cluster.ini` file
- at least one shard folder (a subdirectory containing `server.ini`)
- `server.ini`, `leveldataoverride.lua`, and `modoverrides.lua` files in every shard folder
- all `modoverrides.lua` files byte-identical across shards -- a mismatch is a hard error whose message names the differing shards
- all above files following their respective formats and parsing successfully

## Cluster View screen

Cluster info appears in a rounded box titled "Cluster Info":

- cluster name (`[NETWORK] cluster_name` from `cluster.ini`, falling back to the folder name if absent) and folder path
- how many shards are in the cluster, their names, and which one is the master shard
- how many mods are enabled in the cluster (entries with `enabled = true`)
- warnings -- display-only, never blocking:
  - no `cluster_token.txt`: the cluster cannot be hosted as a dedicated server without it
  - the cluster has been played (a `save` folder in any shard): changing cluster settings may break the save files
  - no master shard, or more than one: the cluster cannot run as-is (the tool never touches `server.ini`, so it only reports this)
  - the mods-setup warnings described in [The mods-setup check](#the-mods-setup-check)

After the cluster info comes a menu:

- Overwrite level settings → submenu to select a shard among the shards in the cluster → File Diff screen
- Append mod list → File Diff screen
- Populate missing mods to `dedicated_server_mods_setup.lua` -- only shown when the mods-setup check found missing mods
- Reload cluster -- reloads from disk and shows a locale-aware "Last loaded" time
- Open another cluster → back to the Welcome screen
- Quit

The footer shows key bindings: Escape = back, Ctrl+Q = quit.

## File Diff screen

At the very top, a title reads "Overwriting level settings for shard: [shard name]" or "Appending mod list for cluster" depending on the menu selection (the two modes of `DiffMode` in `ui/file_diff.py`).

The screen shows a diff view of the selected file (`leveldataoverride.lua` for a shard, or `modoverrides.lua`).
Above the diff view sit a read-only text box (displaying the user-picked file path) and a Browse button next to it, labeled with the target file name ("Browse leveldataoverride.lua" / "Browse modoverrides.lua").
Below the diff view sit an "Apply Changes" button and a "Cancel" button.
At start, both sides of the diff view show the original file content, and "Apply Changes" is disabled; it becomes enabled once a valid file has been picked.

The Browse button filters for the corresponding file name.
The picked file is parsed and validated (`cluster/operations.py`):

- level settings: must parse as a single `return { ... }` table with string `id` and `location` fields
- mod list: must parse with every top-level entry being a string key mapped to a table

There is no deeper schema check -- in particular, no world-type match check: overwriting a forest shard with a cave file is allowed without warning.

If the picked file is invalid, an inline error is shown and the right panel stays unchanged.
Clicking Browse again replaces the right panel content with the new pick.

The right panel is always produced by the serialize-from-model pipeline: picked file → parse into the model → serialize back to text.
"Apply Changes" writes exactly the string shown in the right panel.

- Overwrite level settings (`prepare_level_overwrite`): the right panel is the serialized picked file; nothing from the original file is carried over.
- Append mod list (`prepare_mod_merge`): the right panel is the original modeled mod list merged with the picked one, then serialized:
  - entries whose keys already exist are replaced in place by the incoming entry (incoming wins; in-place replacement keeps the diff view aligned)
  - entries with new keys are appended at the end, in the picked file's order
  - the merge operates on the full parsed table (`LuaTable`), so unknown fields inside an entry survive even though the `ModEntry` model narrows entries to `enabled` + `configuration_options`

The user cannot edit either panel, but can scroll through them.

When the user clicks "Apply Changes", the program writes the file(s) -- for the mod list, the same serialized string to every shard's `modoverrides.lua`, which keeps them byte-identical by construction -- then reloads the cluster from disk and returns to a refreshed Cluster View screen.
On a write failure, an error is shown and the diff screen stays.
"Cancel" (or Escape) discards any changes and goes back to the Cluster View screen.

## Lua serialization

The parser and serializer live in `cluster/luadata.py`.
Serialized output follows Klei's table-serializer style: 2-space indent, bare keys where the key is a Lua identifier and `["..."]=` quoting otherwise, a trailing space before closing braces, empty tables as `{  }`, LF-only line endings, no trailing newline.
Keys are emitted in model insertion order -- parse order for round-trips, original-then-appended for merges; the serializer never re-sorts.

The acceptance bar (covered in `tests/test_luadata.py`): parsing any Klei-written Lua file from the sample clusters and re-serializing it reproduces the file byte-for-byte.

Known, accepted loss of serialize-from-model: `--` comments in a source file are dropped.

## dedicated_server_mods_setup.lua

The program does not actually download or install mods itself.
Instead, it reads and appends to a particular Lua file, which the game server process runs on boot to determine which mods to download and install.
All of this lives in `mods_setup.py`; the file belongs to the game install, not to a cluster, so nothing here touches the cluster model.

### File location

`<game directory>/mods/dedicated_server_mods_setup.lua`

The default location of the game directory is:

- Windows: `C:/Program Files (x86)/Steam/steamapps/common/Don't Starve Together`
- Linux: `~/.steam/steam/steamapps/common/Don't Starve Together`
- Mac: `~/Library/Application Support/Steam/steamapps/common/Don't Starve Together`

### Setting the game directory

The user can have the game installed elsewhere.
A "Set Game Directory" command in the Textual command palette (available on every screen) invokes a folder picker to select the game directory.

- The picker starts browsing at `C:/` on Windows and the home directory on Linux/macOS.
  It does not read or update the session's shared "last picked" location used by the cluster file pickers.
- The picked folder is accepted silently -- no validation, no notification.
  The cluster-load warning (below) is the only feedback loop.
- The selected directory is stored in memory for the session and is not persisted to disk (for now).

### File content

The stock file (Windows install):

```lua
--There are two functions that will install mods, ServerModSetup and ServerModCollectionSetup. Put the calls to the functions in this file and they will be executed on boot.

--ServerModSetup takes a string of a specific mod's Workshop id. It will download and install the mod to your mod directory on boot.
	--The Workshop id can be found at the end of the url to the mod's Workshop page.
	--Example: http://steamcommunity.com/sharedfiles/filedetails/?id=350811795
	--ServerModSetup("350811795")

--ServerModCollectionSetup takes a string of a specific mod's Workshop id. It will download all the mods in the collection and install them to the mod directory on boot.
	--The Workshop id can be found at the end of the url to the collection's Workshop page.
	--Example: http://steamcommunity.com/sharedfiles/filedetails/?id=379114180
	--ServerModCollectionSetup("379114180")

ServerModSetup("1467214795")
ServerModSetup("3435352667")
```

Observed facts about the stock file: ASCII/UTF-8 text, CRLF line endings, **no trailing newline** after the last line.

### Reading the file

Mod ids are extracted with a comment-aware text scan (`parse_installed_mod_ids`).
The file is arbitrary user-editable Lua (the game runs it as a script), so any reading short of a Lua interpreter is an approximation by design:

- `--[[ ... ]]` block comments are stripped, then `--` line comments -- the stock file's commented-out examples must not count as installed.
- `ServerModSetup("<digits>")` calls are matched, allowing single or double quotes and internal whitespace.
- `ServerModCollectionSetup` calls are ignored entirely: a collection's contents cannot be known without the Steam network.
  If a user's collection actually covers a cluster mod, the warning is a false positive, and populating appends an explicit line that is redundant but harmless.

### Which cluster mods are checked

- Only entries with `enabled = true` in the cluster's `modoverrides.lua` (byte-identical across shards, so any shard's copy is the cluster mod list).
- Only keys matching `workshop-<digits>`; the numeric part is compared against the ids in the file.
  Other keys (e.g. local mods) are skipped silently -- `ServerModSetup` cannot download them anyway.

### Rules of writing to the file

- The file is ALWAYS written in "append" mode, never in "overwrite" mode.
- Nothing is ever appended to a file that was not just successfully read (a missing or unreadable file produces a warning only -- see below).
- The file is re-read immediately before appending, so a stale load-time snapshot cannot cause duplicate appends; only ids still missing are written.
- The appended block:
  - bare `ServerModSetup("<id>")` lines, one per missing mod, in `modoverrides.lua` entry order -- no header comment;
  - preceded by one line break if the file does not already end with one;
  - line breaks match the file's existing style (CRLF if any CRLF is present, LF otherwise);
  - no trailing newline after the last line, matching the stock file's convention.

### The mods-setup check

The check (`check_mods_setup`) runs every time a cluster is loaded or reloaded (opening a cluster, the "Reload cluster" action, and the automatic reload after an apply), as a separate step alongside `load_cluster()` -- the cluster model stays cluster-only.

- The `dedicated_server_mods_setup.lua` file is read and the installed mod ids parsed out.
- The ids are checked against the cluster's mod list, counting the mods that are in the cluster but not in the file.
- If the count is greater than zero:
  - a warning indicates that there are N enabled mods not in `dedicated_server_mods_setup.lua`;
  - a menu option "Populate missing mods to dedicated_server_mods_setup.lua" appears.
  - Otherwise, neither the warning nor the menu option is shown.
- If the file does not exist, a warning is shown instead:
  > Could not find dedicated_server_mods_setup.lua.
  > Use "Set Game Directory" to select the game directory that contains the file, and reload the cluster.
- If the file exists but cannot be read (permission denied, undecodable bytes), a distinct warning is shown:
  > Could not read dedicated_server_mods_setup.lua: \<reason\>

  The populate option is never offered in this state.

### Populate missing mods

- Selecting the menu option appends immediately (`append_missing_mods`) -- no diff preview.
- On success: a notification ("Appended N mods to dedicated_server_mods_setup.lua"), then the exact "Reload cluster" code path runs, which re-runs the check and clears the warning and the menu option.
- On failure (e.g. permission denied): an error notification; the view is unchanged.

### Testing

- A static fixture `tests/game_dir_example/mods/dedicated_server_mods_setup.lua` holds the stock content shown above (CRLF, no trailing newline), mirroring `tests/cluster_examples/`.
- Tests that append first copy the fixture into a pytest `tmp_path`; tests never read from or write to a real game install.
