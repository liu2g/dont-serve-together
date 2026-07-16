# Program UI Preliminary Design

This document describes the preliminary design of the program's user interface using the Textual library.

## Global Design Principles

- Always use forward slashes (`/`) in file paths, even on Windows.
- All file pickers start browsing at a location stored as a session-global variable:
  - Its initial value is the game data directory: `~/Documents/Klei/DoNotStarveTogether/` on
    Windows/macOS, `~/.klei/DoNotStarveTogether/` on Linux. If that location does not exist, fall back
    to the user's home directory.
  - After every successful pick, the global updates to the picked file's directory, so subsequent pickers
    resume there. The value is not persisted across program runs.
- Byte-level comparison happens in exactly one place: the cross-shard `modoverrides.lua` identity check
  during cluster validation. Those files must be byte-identical to be seen as "one file" across the entire
  cluster. Everything else is judged at parse/model level, never by bytes.

## Welcome Screen

First screen to display at launch.
Show the program name, the version (read from package metadata, not hardcoded), and a "Browse cluster
folder" button. There is no text box; selection happens exclusively through the picker. Every Browse
button is labeled with what it picks.

When a cluster folder is selected, the program loads and validates it.
If invalid, an inline error message describing the problem is shown, and the user can browse again.
If valid, continue to the Cluster View Screen.

A valid cluster folder must have

- a `cluster.ini` file
- at least one shard folder (a subdirectory containing `server.ini`)
- `server.ini`, `leveldataoverride.lua`, and `modoverrides.lua` files in every shard folder
- all `modoverrides.lua` files byte-identical across shards — a mismatch is a hard error whose message
  names the differing shards
- all above files follow their respective formats and can be parsed successfully

## Cluster View Screen

Show info in a rounded box with a title "Cluster Info" and the following information:

- cluster name (`[NETWORK] cluster_name` from `cluster.ini`, falling back to the folder name if absent)
  and folder path
- how many shards in the cluster, what their names are, and which one is the master shard
- how many mods are enabled in the cluster (entries with `enabled = true`)
- warnings — display-only, never blocking:
  - no `cluster_token.txt`: the cluster cannot be hosted as a dedicated server without it
  - the cluster has been played (a `save` folder in any shard): changing cluster settings may break the
    save files
  - no master shard, or more than one: the cluster cannot run as-is (the tool never touches `server.ini`,
    so it only reports this)

After the cluster info, show a menu with the following options:

- Overwrite level settings -> submenu to select a shard among the shards in the cluster -> File Diff Screen
- Append mod list -> File Diff Screen
- Open another cluster -> back to the Welcome Screen
- Quit

The footer shows key bindings: Escape = back, Ctrl+Q = quit.

## File Diff Screen

At the very top of the screen, show a title "Overwriting level settings for shard: [shard name]" or
"Appending mod list for cluster" depending on the previous menu selection.

Show a diff view of the selected file (`leveldataoverride.lua` for a shard or `modoverrides.lua`).
At the top of the diff view, show a read-only text box (displaying the user-picked file path) and a
Browse button next to it, labeled with the target file name ("Browse leveldataoverride.lua" /
"Browse modoverrides.lua").
At the bottom of the diff view, show an "Apply Changes" button and a "Cancel" button.
At start, both left and right sides of the diff view show the original file content, and "Apply Changes"
is disabled; it becomes enabled once a valid file has been picked.

The "Browse" button filters for the corresponding file name, e.g. `leveldataoverride.lua` for level
settings, `modoverrides.lua` for mod list. The picked file is parsed and validated:

- level settings: must parse as a single `return { ... }` table with string `id` and `location` fields
- mod list: must parse with every top-level entry being a string key mapped to a table

There is no deeper schema check — in particular, no world-type match check: overwriting a forest shard
with a cave file is allowed without warning.

If the picked file is invalid, show an inline error and keep the right panel unchanged. Clicking "Browse"
again replaces the right panel content with the new pick.

The right panel is always produced by the serialize-from-model pipeline: picked file -> parse into the
model -> serialize back to text. "Apply Changes" writes exactly the string shown in the right panel.

- Overwrite level settings: the right panel is the serialized picked file; nothing from the original file
  is carried over.
- Append mod list: the right panel is the original modeled mod list merged with the picked one, then
  serialized:
  - entries whose keys already exist are replaced in place by the incoming entry (incoming wins; in-place
    replacement keeps the diff view aligned)
  - entries with new keys are appended at the end, in the picked file's order

The user cannot edit either the left or right panels, but can scroll through them.

When the user clicks "Apply Changes", the program writes the file(s) — for the mod list, the same
serialized string to every shard's `modoverrides.lua`, which keeps them byte-identical by construction —
then reloads the cluster from disk and returns to a refreshed Cluster View Screen. On a write failure,
show an error and stay on the diff screen.
When the user clicks "Cancel" (or presses Escape), the program discards any changes and goes back to the
Cluster View Screen.

## Lua Serialization

Serialized output follows Klei's table-serializer style: 2-space indent, bare keys where the key is a Lua
identifier and `["..."]=` quoting otherwise, a trailing space before closing braces, empty tables as
`{  }`, LF-only line endings, no trailing newline. Keys are emitted in model insertion order — parse order
for round-trips, original-then-appended for merges; the serializer never re-sorts.

Dev acceptance test: parsing any Klei-written Lua file from the sample clusters and re-serializing it must
reproduce the file byte-for-byte.

Known, accepted loss of serialize-from-model: `--` comments in a source file are dropped.

Implementation notes:

- The serializer does not exist yet and is a new work item in `luadata`.
- The mod merge must serialize entries from the full parsed table so unknown fields inside an entry are
  preserved (`ModEntry` currently narrows entries to `enabled` + `configuration_options`).
- The `source_text` span machinery in the parser is no longer needed by the merge once serialization
  lands.
