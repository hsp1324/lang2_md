#!/bin/sh
set -eu
xdg-open "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/index.html"
