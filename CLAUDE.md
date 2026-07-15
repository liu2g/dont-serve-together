# CLAUDE.md

## What this project is

A **PySide6 (Qt 6)** desktop GUI for managing **Don't Starve Together (DST)** dedicated-server
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

## Primary use case: assembling a 4-shard cluster

The game's own server-creation UI only supports two shards: **Master** (the
overworld, "the Constant") and **Caves**. The user hosts a 4-shard cluster that
adds **Island** and **Volcano** shards, enabled by the **Island Adventure** mod
(IA, also called Shipwrecked). Such a cluster can only be assembled at file
level, which this tool automates.

Inputs:

- **Template**: a 4-shard cluster provided by the IA mod author. Correct shard
  wiring (`cluster.ini`, `server.ini`), but default level settings and no mods
  besides the IA mods.
- **Preset**: a throwaway 2-shard (Master + Caves) cluster the user creates in
  the game UI, applies their custom level settings and mods to, and exits
  immediately. It carries the user's customizations but knows nothing about IA.

Pipeline (what the tool automates):

1. Copy the template to a WIP area.
2. Overwrite the WIP `Master/leveldataoverride.lua` and
   `Caves/leveldataoverride.lua` with the preset's, as whole-file copies.
   Island and Volcano keep the template's level settings.
3. Merge mods: take the template's `modoverrides.lua` (IA mods) and append the
   preset's mod entries. This is the one operation that requires entry-level
   editing inside a file. The same merged file is written to **all four**
   shards. If the same mod appears on both sides, the GUI warns and lets the
   user decide per mod.
4. Everything else is left as the template has it — `cluster.ini` (nothing
   carries over from the preset), `server.ini`, network/port settings, and
   admin files (`adminlist.txt`, `blocklist.txt`, `cluster_token.txt`).
5. The WIP cluster is now finalized and ready to serve.

Template, preset, and output locations are **user-configurable paths** — do not
hard-code the Klei data-directory layout.

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
