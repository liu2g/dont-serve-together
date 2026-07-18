# Contributing to Don't Serve Together

Thank you for your interest in the project!
Bug reports, feature requests, and pull requests are all welcome.

## Reporting bugs

Open an issue on the [issue tracker](https://github.com/liu2g/dont-serve-together/issues).
A useful report includes:

- What you did, what you expected, and what happened instead.
- Whether you ran the prebuilt `dont-serve-together.exe` or from source, and on which operating system.
- If the problem involves a specific cluster, the relevant config files (`cluster.ini`, `server.ini`, `leveldataoverride.lua`, `modoverrides.lua`) or a minimal cluster folder that reproduces it.
  Never attach `cluster_token.txt`; it is a secret tied to your Klei account.

## Requesting features

Open an issue describing the hosting scenario you are trying to accomplish, not only the mechanism you have in mind.
The tool is built around concrete server-setup workflows, so a worked example like the one in the README makes the strongest case for a feature.

## Setting up a development environment

The project is written in Python 3.14 and managed with [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/liu2g/dont-serve-together.git
cd dont-serve-together
uv sync                        # install dependencies
uv run dont-serve-together     # run the app from source
```

The [developer documentation](docs/developer-docs.md) has the code map and the exact file-handling rules.

One safety rule:
code and tests must never read from or write to a real game data directory (`Documents/Klei/DoNotStarveTogether`).
Use the sample clusters under `tests/cluster_examples/` instead; they exist so that development never risks a real server.

## Checks

Run the whole suite before opening a pull request:

```bash
./scripts/check.sh            # format, lint, type-check, and tests
```

The flags `--format`, `--lint`, and `--test` run individual stages.

## Pull requests

- For anything larger than a small fix, open an issue first so the approach can be discussed before you invest time in it.
- Keep each pull request focused on one change.
- Add or update tests under `tests/` when behavior changes.
- Match the existing code style, which ruff and pyright enforce:
  `pathlib` over `os.path`, type hints everywhere, Google-style docstrings, and Pydantic models for structured data.

## AI-assisted contributions

You are welcome to use LLMs, AI tools and services as assistance when working on this project.
These ground rules come with that:

- **Do not contribute your AI configuration files.**
  Keep your own local copies of instruction files (such as `CLAUDE.md`), skills, and other assistant configuration rather than committing them to the repo.
  To leave note about important information, use the developer human-facing `docs/` folder instead.
  The `.gitignore` already excludes the maintainer's own instruction file, which is why you may see it mentioned but not find it in a fresh clone.
- **Be honest about AI assistance.**
  Say so in the pull request or commit message when content was produced with AI help, and, better still, explain how it was used
  (for example: "the first draft of this parser came from a model; I rewrote the error handling and verified it against the sample clusters").
- **You are responsible for every line you commit.**
  Responsibility never shifts to the model, service, or tool that helped produce the change.
  Review, understand, and test whatever an assistant writes before it goes into a pull request,
  exactly as if you had typed it yourself.
- **Only report what you have actually observed.**
  The same responsibility applies to issues and comments as to code:
  file a bug report only for behavior you have seen yourself,
  and check a model-suggested diagnosis against reality before repeating it.
  Unverified AI-generated reports cost a maintainer more time than they save.
- **Answer reviews yourself.**
  A reviewer commenting on your pull request is talking to you, not to your assistant.
  Be ready to explain what your change does and why;
  if you cannot, the change is not ready to submit.
- **Contribute only what you have the right to license.**
  Contributions are accepted under the [MIT License](LICENSE), and that promise is yours to make.
  Models sometimes reproduce existing code nearly verbatim,
  so if output looks like a lifted chunk of someone else's project rather than code written for this one, do not submit it as-is.

## Code of conduct

Everyone participating in the project is expected to follow the [code of conduct](CODE_OF_CONDUCT.md).

## License

By contributing, you agree that your contributions are licensed under the project's [MIT License](LICENSE).
