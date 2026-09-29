#!/bin/sh
# Fetches Bub-n-Bros (the Python 3 fork, MIT) for examples/bubbros.py.
#
#   scripts/bubbros-fetch.sh
#
# It lives next to the repo's worktrees, at ../bubbros, pinned by commit and
# never edited: examples/bubbros.py runs its game server unchanged. The game is
# MIT; its art is Sebastian Wegner's, which Bub-n-Bros redistributes with his
# permission. It is fetched from the Bub-n-Bros repository and never committed
# or redistributed here.
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
