#!/usr/bin/env sh

set -e

# Move up to the root of the repository
cd "$(dirname "$0")/.."

# Directory into which to write the cube. Required by "cube" service in docker-compose.yml.
export CUBE_OUTPUT_DIR="./output" # git-ignored
mkdir -p "${CUBE_OUTPUT_DIR}"

# Unless we have a SKIP_BUILD variable in our environment, rebuild the image.
[ -n "$SKIP_BUILD" ] || docker compose build

# FULL path to the recipe file.
RECIPE="$(pwd)/tests/smoke_test.yaml"

docker compose run --rm --user "$(id -u):$(id -g)" -v "${RECIPE}:/recipe.yaml:ro" cube
