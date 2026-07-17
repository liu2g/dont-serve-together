#!/usr/bin/env bash
set -euo pipefail

RED="\e[31m"
GREEN="\e[32m"
BLUE="\e[34m"
ENDCOLOR="\e[0m"

DO_FORMAT=false
DO_LINT=false
DO_TEST=false

usage() {
    printf "Usage: %s [--format] [--lint] [--test] [--all]\n" "$(basename "$0")"
    printf "  --format: Run code formatter\n"
    printf "  --lint: Run static code analysis\n"
    printf "  --test: Run unit tests\n"
    printf "  --all: Run all of the above (default if no flag given)\n"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --format) DO_FORMAT=true ;;
        --lint) DO_LINT=true ;;
        --test) DO_TEST=true ;;
        --all) DO_FORMAT=true; DO_LINT=true; DO_TEST=true ;;
        -h|--help) usage; exit 0 ;;
        *) printf "${RED}Unknown option: %s${ENDCOLOR}\n" "$1"; usage; exit 1 ;;
    esac
    shift
done

if ! $DO_FORMAT && ! $DO_LINT && ! $DO_TEST; then
    DO_FORMAT=true
    DO_LINT=true
    DO_TEST=true
fi

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

if $DO_FORMAT; then
    printf "${GREEN}==>${ENDCOLOR} Running code formatter\n"
    printf "${BLUE} ->${ENDCOLOR} Running ruff\n"
    uv run ruff format && uv run ruff check --fix --select I
fi

if $DO_LINT; then
    printf "${GREEN}==>${ENDCOLOR} Running static code analysis\n"
    printf "${BLUE} ->${ENDCOLOR} Running ruff\n"
    uv run ruff check
    printf "${BLUE} ->${ENDCOLOR} Running pyright\n"
    uv run pyright
fi

if $DO_TEST; then
    printf "${GREEN}==>${ENDCOLOR} Running unit tests\n"
    uv run pytest tests
fi
