# CLAUDE.md

## What this project is

A program for managing **Don't Starve Together (DST)** dedicated-server
clusters (config, mods, player lists). Python 3.14, managed with **uv**.

Status: scaffolding only — not implemented yet.

## Commands

```bash
uv sync                                # install deps
uv run dont_serve_together             # run the app
uv run ruff check .                    # lint
uv run pyright                         # type-check
uv run pytest                          # tests
```

## Coding conventions

- Prefer `pathlib` over `os.path`.
- Use type hints everywhere.
- Google-style docstrings.
- Pydantic models for complex/repetitive data structures.
- pytest for unit tests, under `tests/`.

## Safety

- **Never read from or write to the user's actual DST data directory**
  (`~/Documents/Klei/DoNotStarveTogether/` on Windows/macOS,
  `~/.klei/DoNotStarveTogether/` on Linux) until the user says the project is
  ready to release. Use the sample clusters under `tests/` for development and
  testing instead.

## Terminology: Clusters and Shards

A DST server consists of **clusters** and **shards**.
A shard is a map or level.
A cluster ties one or more shards together.

From the server's perspective, a shard is run as an individual process, connected by configured ports to the other shards in the cluster.
From the player's perspective, a cluster is a single game server instance, and the shards are the different levels of the world that can be accessed by traveling between them.

## Scope

In scope now: the pipeline above — cluster scaffolding (template copy), level
config transfer, and mod list merging.

Deferred — do not design or build these until the user brings them up:

- Player list management (`adminlist.txt`, `blocklist.txt`, whitelist).
- Generating `dedicated_server_mods_setup.lua` (mod downloading for the
  dedicated-server install); planned as a small later feature.
- Choosing/re-assigning the master shard. `server.ini` comes straight from the
  template and is never touched. (Note: shard folder names don't imply the
  master role — in `Cluster_IslandStart`, Island is the master, not `Master`.)

## Design principle: whole files first

Configuration is managed at file level. Treat config files as opaque units to
copy or replace whole; do not parse them into granular entries unless an
operation truly requires it (the known exception is the `modoverrides.lua`
merge above).

## Sample clusters under tests/cluster_examples/

Test vectors moved from real data, mirroring the use case:

- `Cluster_2` — a "preset": fresh 2-shard cluster from the in-game UI.
- `Cluster_IslandStart` — a finalized 4-shard cluster: the result of merging a
  `Cluster_2`-like preset into the IA template. Its `Master`/`Caves`
  `leveldataoverride.lua` are byte-identical to `Cluster_2`'s, and its
  `modoverrides.lua` (identical across all four shards) is the IA mods plus
  `Cluster_2`'s mods.
- `Cluster_3` — a cluster that has actually been played (saves, logs,
  sessions); useful for verifying the tool leaves runtime data alone.

## Cluster file layout and contents

Facts observed in the sample clusters; no data-model design implied yet.

### Cluster layout

```
Cluster_X/                      # directory name is just a label
├── cluster.ini                 # cluster-wide settings
├── cluster_token.txt           # optional; required to host a dedicated server
├── adminlist.txt               # optional
├── blocklist.txt               # optional
├── <ShardA>/                   # one subdirectory per shard; name is a label
│   ├── server.ini              # shard wiring: master/slave role, ports
│   ├── leveldataoverride.lua   # world type + world-gen settings
│   ├── modoverrides.lua        # mod list + per-mod config
│   ├── save/                   # runtime, played clusters only — out of scope
│   ├── backup/                 # runtime — out of scope
│   ├── server_log.txt          # runtime — out of scope
│   └── server_chat_log.txt     # runtime — out of scope
└── <ShardB>/
    └── ...
```

- Folder names are arbitrary labels: in `Cluster_3`, the `Master` folder holds
  a Shipwrecked world and `Caves` a Volcano world. What a shard *is* comes
  only from its files.
- Only the template-derived `Cluster_IslandStart` has the optional root files;
  the game-UI clusters (`Cluster_2`, `Cluster_3`) have none.
- The runtime entries appear only in played clusters (`Cluster_3`), are
  Klei-specific formats (e.g. `save/shardindex` starts with a `KLEI     1`
  header), and are **outside the scope of this project** — the tool never
  reads, writes, or manages them.

### cluster.ini

- Sections `[GAMEPLAY]`, `[NETWORK]`, `[MISC]`, `[SHARD]`; the template adds
  `[STEAM]` and extra keys. Section and key sets vary per cluster — no fixed
  schema. Game-generated files carry a `cluster_cloud_id`; the template does
  not.
- Any parsing must tolerate trailing whitespace (the template's `[SHARD]`
  block has trailing tabs) and empty values (`cluster_password = `).

### server.ini

- Sections: `[NETWORK]` (`server_port`), `[SHARD]`, `[ACCOUNT]`
  (`encode_user_path`), and usually `[STEAM]` (`master_server_port`,
  `authentication_port`). Section order varies between files.
- The master shard has only `is_master = true`; non-master shards have
  `is_master = false`, `name`, and `id`. Game-generated slave ids are large
  random numbers; the template's are small hand-picked ones (`2`, `3`, `4`).
- Each shard has a distinct `server_port` (and distinct `[STEAM]` ports)
  within the cluster.

### Lua files (leveldataoverride.lua, modoverrides.lua)

- Both are a single `return { ... }` expression in Klei's table-serializer
  style: 2-space indent, keys sorted lexicographically, string keys that need
  quoting written as `["..."]=` (including non-ASCII keys like
  `["世界设置"]` and the empty-string key `[""]`), a trailing space before
  closing braces, empty tables as `{  }`. Values are strings, booleans,
  numbers, and nested tables/lists.

#### leveldataoverride.lua

- Top-level `id` / `location` identify the world type
  (`SURVIVAL_TOGETHER`/`forest`, `DST_CAVE`/`cave`,
  `SURVIVAL_SHIPWRECKED_CLASSIC`/`shipwrecked`,
  `SURVIVAL_VOLCANO_CLASSIC`/`volcanoworld`), plus `name`, `desc`,
  `version=4`, and a large `overrides={...}` table whose key set differs per
  world type. Optional top-level fields vary per file (e.g.
  `custom_settings_*` / `custom_worldgen_*` appear only in game-UI-created
  files).

#### modoverrides.lua

- Shape: `return { ["workshop-<id>"] = { configuration_options = {...},
  enabled = true }, ... }`. `configuration_options` may be empty.
- Within one cluster the file is byte-identical across all shards (verified by
  hash in all three samples).
- Entry order is semantically irrelevant: `Cluster_IslandStart`'s merged file
  is a literal concatenation (the two IA mods first, then the preset's entries
  byte-for-byte), while the game re-sorts keys lexicographically whenever it
  rewrites the file (`Cluster_2`, `Cluster_3`).

### Encodings and line endings

- All text files: UTF-8, no BOM.
- INI files: CRLF line endings, with a trailing newline.
- Lua files: LF-only line endings, **no** trailing newline.
- `adminlist.txt` / `blocklist.txt`: CRLF between lines, no trailing newline.
  Entries are Klei user ids (`KU_...`); `blocklist.txt` also shows a 17-digit
  SteamID64 line — both formats occur.
- `cluster_token.txt`: a single line, no newline at all.
