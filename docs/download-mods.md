This document explains how mods are downloaded and installed for the game.

The program does not actually download or install mods itself.
Instead, it reads and writes to a particular Lua file, which is used by the game server process to determine which mods to load.

## This file location

`<game directory>/mods/dedicated_server_mods_setup.lua`

The default location of the game directory is:
- Windows: `C:/Program Files (x86)/Steam/steamapps/common/Don't Starve Together`
- Linux: `~/.steam/steam/steamapps/common/Don't Starve Together`
- Mac: `~/Library/Application Support/Steam/steamapps/common/Don't Starve Together`

However, the user can have a different location for the game directory.
For this, a "Set Game Directory" command in the Textual command palette (available on every screen) invokes a folder picker to select the game directory.

- The picker starts browsing at `C:/` on Windows and the home directory on Linux/macOS. It does not read or update the session's shared "last picked" location used by the cluster file pickers.
- The picked folder is accepted silently — no validation, no notification. The cluster-load warning (below) is the only feedback loop.
- The selected directory is stored in memory for the session, and is not persisted to disk (for now).

## This file content

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

Observed facts about the stock file (Windows install): ASCII/UTF-8 text, CRLF
line endings, **no trailing newline** after the last line.

## Reading the file

Mod ids are extracted with a comment-aware text scan. The file is arbitrary
user-editable Lua (the game runs it as a script), so any reading short of a
Lua interpreter is an approximation by design:

- Strip `--[[ ... ]]` block comments, then `--` line comments — the stock
  file's commented-out examples must not count as installed.
- Match `ServerModSetup("<digits>")` calls, allowing single or double quotes
  and internal whitespace.
- `ServerModCollectionSetup` calls are ignored entirely: a collection's
  contents cannot be known without the Steam network. If a user's collection
  actually covers a cluster mod, the warning is a false positive, and
  populating appends an explicit line that is redundant but harmless.

## Which cluster mods are checked

- Only entries with `enabled = true` in the cluster's `modoverrides.lua`
  (byte-identical across shards, so any shard's copy is the cluster mod list).
- Only keys matching `workshop-<digits>`; the numeric part is compared against
  the ids in the file. Other keys (e.g. local mods) are skipped silently —
  `ServerModSetup` cannot download them anyway.

## Rules of writing to the file

- ALWAYS write to the file in "append" mode, never in "overwrite" mode.
- Never append to a file that was not just successfully read (a missing or
  unreadable file produces a warning only — see below).
- The file is re-read immediately before appending, so a stale load-time
  snapshot cannot cause duplicate appends; only ids still missing are written.
- The appended block:
    - bare `ServerModSetup("<id>")` lines, one per missing mod, in
      `modoverrides.lua` entry order — no header comment;
    - preceded by one line break if the file does not already end with one;
    - line breaks match the file's existing style (CRLF if any CRLF is
      present, LF otherwise);
    - no trailing newline after the last line, matching the stock file's
      convention.

## Interaction with the program

The check runs every time a cluster is loaded or reloaded (opening a cluster,
the "Reload cluster" action, and the automatic reload after an apply), as a
separate step alongside `load_cluster()` — the cluster model stays
cluster-only.

- Read the `dedicated_server_mods_setup.lua` file and parse out the mod ids
- Check the mod ids against the mod list associated with the cluster, count the number of mods that are in the cluster but not in the `dedicated_server_mods_setup.lua` file
- If the count is greater than zero:
    - Add a warning indicating that there are N mods in the cluster not in the dedicated_server_mods_setup.lua file
    - Add an option in the menu to "Populate missing mods to dedicated_server_mods_setup.lua"
    - Otherwise, do not show the warning or the option in the menu
- If the `dedicated_server_mods_setup.lua` file does not exist:
    - Add a warning
      > Could not find dedicated_server_mods_setup.lua. Use "Set Game Directory" to select the game directory that contains the file, and reload the cluster.
- If the file exists but cannot be read (permission denied, undecodable
  bytes):
    - Add a distinct warning
      > Could not read dedicated_server_mods_setup.lua: <reason>
    - Never offer the populate option in this state.

### Populate missing mods

- Selecting the menu option appends immediately — no diff preview.
- On success: a notification ("Appended N mods to
  dedicated_server_mods_setup.lua"), then the exact "Reload cluster" code path
  runs, which re-runs the check and clears the warning and the menu option.
- On failure (e.g. permission denied): an error notification; the view is
  unchanged.

## Testing

- A static fixture `tests/game_dir_example/mods/dedicated_server_mods_setup.lua`
  holds the stock content shown above (CRLF, no trailing newline), mirroring
  `tests/cluster_examples/`.
- Tests that append first copy the fixture into a pytest `tmp_path`; tests
  never read from or write to a real game install.
