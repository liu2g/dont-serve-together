# Don't Serve Together

<img src="/assets/logo.ico" align="right" width="185px"/>

A companion tool for people who host [Don't Starve Together](https://www.klei.com/games/dont-starve-together) dedicated servers.
It opens a server cluster folder and takes over the fiddly parts of setting one up:
carrying world settings from one cluster to another, combining mod lists, and keeping the server's mod-download list in sync.
Every change is shown as a side-by-side preview before anything is written, so you never have to hand-edit a config file.

> [!NOTE]
> This project is not made to be the replacement/alterantive to the [Vox Launcher](https://github.com/diogo-webber/vox-launcher).
> Despite the name, the project serves a different purpose as of today's scope, and it is not a launcher.

## What it does

Point the tool at a cluster folder and it shows what is inside:
the cluster name, its shards (the levels of the world, such as the overworld and the caves), which shard is the master, and how many mods are enabled.
It also warns about common problems, such as a missing `cluster_token.txt` or a cluster without a master shard.

From there, the menu offers three actions:

- **Overwrite level settings**:
  replace one shard's world settings (`leveldataoverride.lua`) with a file taken from another cluster.
  Useful for carrying world-generation settings you configured in the in-game menu over to your dedicated cluster.
- **Append mod list**:
  merge another cluster's mod list (`modoverrides.lua`) into this one.
  Mods you already have are updated with the incoming settings, new mods are added at the end, and every shard ends up with the same mod list.
- **Populate missing mods**:
  if the cluster enables mods that your server install is not set up to download, add them to the game's `dedicated_server_mods_setup.lua` in one step.
  This option appears only when such mods are found.

The first two actions show a before/after comparison of the affected file, and nothing is written until you press "Apply Changes".

## Installation

### Windows Prebuilt

Prebuilt executable `dont-serve-together.exe` is available to download from the [releases page](https://github.com/liu2g/dont-serve-together/releases).
There is nothing to install: save it anywhere and run it.

<details>

<summary>Windows may warn that the app is unrecognized the first time you run it.</summary>

This project is 100% open-source.
Everything is archived in this repository, even including the exe building process.

If you downloaded it from the releases page above, it is safe to run, so you can choose "More info" and then "Run anyway".

If you are still not sure, you can build the exe yourself from source; see the section below for instructions.

</details>

### Building From Source (Compatible to Windows, macOS, and Linux)

This project is a Python app implemented with modern toolchain and cross-platform compatibility in mind.
As a result, it can be installed using any pip-compatible tools.
Here we provide examples using [UV](https://docs.astral.sh/uv/getting-started/installation/) and [pipx](https://pipx.pypa.io/stable/how-to/install-pipx.html).

To install using UV, run the following command in a terminal:

```
uv tool install git+https://github.com/liu2g/dont-serve-together
```

To install using pipx, run the following command in a terminal:

```
pipx install git+https://github.com/liu2g/dont-serve-together
```

## Getting started

Here is the scenario the tool was built around, as a worked example.

The game's own server-creation screen can only make a two-shard cluster: `Master` (the overworld) and `Caves`.
Suppose you want to host a four-shard cluster that adds `Island` and `Volcano` shards, enabled by the Island Adventure mod (IA, also called Shipwrecked).
Such a cluster can only be assembled by editing server files, and that assembly is what this tool automates.

You start with two ingredients:

- **A template**: a four-shard cluster provided by the IA mod author.
  Its shard wiring (`cluster.ini`, `server.ini`) is correct, but the level settings are the defaults and the only mods are the IA mods.
- **A preset**: a throwaway two-shard cluster you create in the game's UI, apply your custom world settings and mods to, and exit immediately.
  It carries your customizations but knows nothing about IA.

The assembly:

1. Copy the template's folder into the game's cluster folder (`Documents\Klei\DoNotStarveTogether`) with the file explorer, under whatever name you like.
   This part you do by hand; everything after it happens in the tool.
2. Run `dont-serve-together.exe`.
   A text-style interface opens in a terminal window; both mouse and keyboard work.
3. Press "Browse cluster folder" and pick the copy you just made.
   The picker already starts in the game's cluster folder.
4. Choose "Overwrite level settings", select the `Master` shard, and browse to the preset's `Master/leveldataoverride.lua`.
   Check the before/after preview and press "Apply Changes".
   Repeat for `Caves`.
   The `Island` and `Volcano` shards keep the template's level settings.
5. Choose "Append mod list" and browse to the preset's `modoverrides.lua`.
   The preview shows the template's IA mods with your preset's mods appended after them; if the same mod appears on both sides, your preset's settings win.
   Apply, and the merged list is written to all four shards at once.
6. If "Populate missing mods" now appears in the menu, run it so the dedicated server downloads the newly added mods on boot.

Everything else stays exactly as the template had it: `cluster.ini`, the port and network wiring in `server.ini`, and any admin files.
The new cluster is ready to serve.

`Escape` goes back one screen and `Ctrl+Q` quits; the bar at the bottom of the screen lists these.

If your game is not installed in the default Steam location, open the command palette with `Ctrl+P` and run "Set Game Directory" so the tool can find `dedicated_server_mods_setup.lua`.

## Good to know

- The tool writes only `leveldataoverride.lua`, `modoverrides.lua`, and (append-only) `dedicated_server_mods_setup.lua`.
  It never touches save data, backups, logs, or the network and port settings in `server.ini`.
- Warnings are advice, not blockers: the tool will not stop you from applying a change to a world that has already been played.
  Settings changes can conflict with an existing save, so make a copy of the cluster folder first; a plain folder copy is a complete backup.

## For developers

How the program works inside, the exact file-handling rules, and instructions for running from source live in the [developer documentation](docs/developer-docs.md).

## Contributing

Bug reports, feature requests, and pull requests are all welcome.
If the tool misbehaves or a hosting workflow you need is missing, open an issue on the [issue tracker](https://github.com/liu2g/dont-serve-together/issues).
The [contributing guide](CONTRIBUTING.md) explains what makes a bug report useful and how to set up a development environment.

## License

[MIT](LICENSE).
This is a fan-made tool, not affiliated with or endorsed by Klei Entertainment.
