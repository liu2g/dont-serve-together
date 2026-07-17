# DST cluster file formats

This document describes the on-disk layout and file formats of a Don't Starve Together dedicated-server cluster,
as this tool understands and reproduces them.
The facts here are not from official Klei documentation;
they were observed in real cluster files, preserved as the [sample clusters](#the-sample-clusters) under `tests/cluster_examples/`,
and any parser or serializer change must stay consistent with them.

## Clusters and shards

A DST server consists of **clusters** and **shards**.
A shard is a map or level.
A cluster ties one or more shards together.

From the server's perspective, a shard runs as an individual process,
connected by configured ports to the other shards in the cluster.
From the player's perspective, a cluster is a single game server instance,
and the shards are the different levels of the world reached by traveling between them.

## Cluster layout

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
│   ├── save/                   # runtime, played clusters only
│   ├── backup/                 # runtime
│   ├── server_log.txt          # runtime
│   └── server_chat_log.txt     # runtime
└── <ShardB>/
    └── ...
```

- Folder names are arbitrary labels, for the cluster and for its shards alike.
  In `Cluster_3`, the folder named `Master` holds a Shipwrecked world and `Caves` holds a Volcano world;
  in `Cluster_IslandStart`, the master shard is `Island`, not the folder named `Master`.
  What a shard *is* comes only from its files.
- The optional root files appear only in some clusters:
  the template-derived `Cluster_IslandStart` sample has them, while the game-UI-created samples have none.
- The runtime entries (`save/`, `backup/`, logs) appear only in clusters that have been played,
  and are Klei-specific formats (for example, `save/shardindex` starts with a `KLEI     1` header).
  They are **outside the scope of this tool**: it never reads, writes, or manages them.

## cluster.ini

- Sections observed: `[GAMEPLAY]`, `[NETWORK]`, `[MISC]`, `[SHARD]`;
  the IA template adds `[STEAM]` and extra keys.
  Section and key sets vary per cluster, so there is no fixed schema to validate against.
  Game-generated files carry a `cluster_cloud_id`; the template does not.
- Parsing must tolerate trailing whitespace (the template's `[SHARD]` block has trailing tabs)
  and empty values (`cluster_password = `).

## server.ini

- Sections: `[NETWORK]` (`server_port`), `[SHARD]`, `[ACCOUNT]` (`encode_user_path`),
  and usually `[STEAM]` (`master_server_port`, `authentication_port`).
  Section order varies between files.
- In `[SHARD]`, the master shard has only `is_master = true`;
  non-master shards have `is_master = false`, `name`, and `id`.
  Game-generated slave ids are large random numbers;
  the template's are small hand-picked ones (`2`, `3`, `4`).
- Each shard has a distinct `server_port` (and distinct `[STEAM]` ports) within its cluster.

## Lua data files

`leveldataoverride.lua` and `modoverrides.lua` are each a single `return { ... }` expression
in the style of Klei's table serializer:

- 2-space indentation.
- Keys sorted lexicographically.
- String keys that need quoting written as `["..."]=`,
  including non-ASCII keys such as `["世界设置"]` and the empty-string key `[""]`.
- A trailing space before closing braces, and empty tables written as `{  }`.
- Values are strings, booleans, numbers, and nested tables/lists.

### leveldataoverride.lua

- Top-level `id` / `location` identify the world type:
  `SURVIVAL_TOGETHER`/`forest`, `DST_CAVE`/`cave`,
  `SURVIVAL_SHIPWRECKED_CLASSIC`/`shipwrecked`, `SURVIVAL_VOLCANO_CLASSIC`/`volcanoworld`.
- Alongside those: `name`, `desc`, `version=4`,
  and a large `overrides={...}` table whose key set differs per world type.
- Optional top-level fields vary per file:
  `custom_settings_*` / `custom_worldgen_*` appear only in game-UI-created files.

### modoverrides.lua

- Shape: `return { ["workshop-<id>"] = { configuration_options = {...}, enabled = true }, ... }`.
  `configuration_options` may be empty.
- Within one cluster the file is byte-identical across all shards
  (verified by hash in all three sample clusters).
- Entry order is semantically irrelevant.
  `Cluster_IslandStart`'s merged file is a literal concatenation (the two IA mods first, then the preset's entries byte-for-byte),
  while the game re-sorts keys lexicographically whenever it rewrites the file.

## Encodings and line endings

- All text files: UTF-8, no BOM.
- INI files: CRLF line endings, with a trailing newline.
- Lua files: LF-only line endings, **no** trailing newline.
- `adminlist.txt` / `blocklist.txt`: CRLF between lines, no trailing newline.
  Entries are Klei user ids (`KU_...`);
  `blocklist.txt` also shows a 17-digit SteamID64 line, so both formats occur.
- `cluster_token.txt`: a single line, no newline at all.

## The sample clusters

The samples under `tests/cluster_examples/` are real cluster files, and every claim above can be checked against them:

- `Cluster_2`: a "preset", the fresh two-shard cluster the in-game UI creates.
- `Cluster_IslandStart`: a finalized four-shard cluster,
  the result of merging a `Cluster_2`-like preset into the Island Adventure template.
  Its `Master`/`Caves` `leveldataoverride.lua` are byte-identical to `Cluster_2`'s,
  and its `modoverrides.lua` (identical across all four shards) is the IA mods plus `Cluster_2`'s mods.
- `Cluster_3`: a cluster that has actually been played (saves, logs, sessions);
  useful for verifying that the tool leaves runtime data alone.
