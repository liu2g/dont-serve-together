# CLAUDE.md

## What this project is

A **customtkinter** desktop GUI for managing **Don't Starve Together** dedicated-server
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
