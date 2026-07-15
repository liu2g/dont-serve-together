# Don't Serve Together

A desktop GUI for managing **Don't Starve Together** dedicated-server clusters:
their `cluster.ini` / `server.ini` settings, mods, and player lists.

Built with [Pydantic](https://docs.pydantic.dev/) for typed, validated config models.

## Requirements

- Python **3.14+**
- [uv](https://docs.astral.sh/uv/) for dependency and environment management

## Getting started

```bash
uv sync                       # create the environment and install the project
uv run dont_serve_together    # run the app (or: uv run python -m dont_serve_together)
```

> Status: scaffolding only — the application is not implemented yet.

## Project layout

```
dont_serve_together/
├─ __init__.py          # package metadata
└─ __main__.py          # entry point (main); dont_serve_together / python -m target
```

See [CLAUDE.md](CLAUDE.md) for a primer on the DST server file format and the
project's coding conventions.

## Development

```bash
uv run ruff check .           # lint (enforces the conventions in CLAUDE.md)
uv run ruff format .          # format
uv run pyright                # type-check
uv run pytest                 # run tests (once added under tests/)
```
