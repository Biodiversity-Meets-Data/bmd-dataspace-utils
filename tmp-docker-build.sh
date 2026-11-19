#!/usr/bin/env bash

# This is how we must temporarily build the docker image until Meise
# has fixed a couple of bugs that prevent the cubing engine to run
# standalone, without IDE, inside a docker image. Delete when fixed.
docker build \
  --build-context bmc=/home/ayco/git-repos/bmd-github/BmC \
  -t ghcr.io/biodiversity-meets-data/bmd-dataspace-utils:local .