#!/usr/bin/env bash

# USAGE: create_cube.sh </full/path/to/some_recipe.yml>
# Recipes _inside_ this repository can be specified through a relative path.

BASE_DIR="$(dirname "${0}")"
BASE_DIR="$(realpath "$BASE_DIR")"

RECIPE="${1:-}"
if [[ -z "${RECIPE}" ]]; then
  echo "USAGE: $0 </full/path/to/some_recipe.yml>"
  exit 1
fi

if [[ ! -f "${RECIPE}" ]]; then
  if [[ -f "${BASE_DIR}/${RECIPE}" ]]; then
    RECIPE="${BASE_DIR}/${RECIPE}"
  else
    echo "No such file: $RECIPE"
    exit 1
  fi
fi

RECIPE="$(realpath "$RECIPE")"

if [[ ! -f "${BASE_DIR}/.env" ]]; then
  echo "Missing .env file. Copy env.template to .env first"
  exit 1
fi

docker compose run --rm --user "$(id -u):$(id -g)" -v "$RECIPE:/recipe.yaml:ro" cube
