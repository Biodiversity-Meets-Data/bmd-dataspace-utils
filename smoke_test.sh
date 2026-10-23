#!/usr/bin/env sh

set -e

mkdir -p output
[ -n "$SKIP_BUILD" ] || docker compose build
docker compose run --rm --user "$(id -u):$(id -g)" cube /recipes/smoke_test.yaml

test -n "$(find output/smoke_test -name '*.nc' | head -n 1)"