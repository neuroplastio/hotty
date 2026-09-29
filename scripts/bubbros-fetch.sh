#!/bin/sh
# Fetches Bub-n-Bros (the Python 3 fork, MIT) for examples/bubbros.py.
#
#   scripts/bubbros-fetch.sh
#
# It lives next to the repo's worktrees, at ../bubbros, pinned by commit and
# never edited: examples/bubbros.py runs its game server unchanged. Its art is
# Sebastian Wegner's, used with the project's permission; it is replaced before
# anything built on it is published.
set -eu
HERE="$(cd "$(dirname "$0")/.." && pwd)"
DIR="${BUBBROS_DIR:-$(dirname "$HERE")/bubbros}"
REV=c30200ca172ef0cf4e537f59699ddde9a290292b
if [ -d "$DIR/.git" ]; then
  echo "bubbros at $DIR: $(git -C "$DIR" log --oneline -1)"
  exit 0
fi
git clone -q https://github.com/fpiesche/bub-n-bros "$DIR"
git -C "$DIR" checkout -q "$REV"
echo "bubbros ready at $DIR"
