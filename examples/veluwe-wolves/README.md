# Example: Veluwe predator-prey cube

A working example of a "serious" GBIF cube for the dataspace cubing engine. It builds a yearly occurrence cube for the
wolf and its three main ungulate prey species on the Veluwe, dimensioned (grid cell x year x species). It answers a
simple question: does wolf occurrence track prey occurrence across the grid? This is why it is (and can be) a GBIF-only
cube. The taxon axis carries all data points.

It is meant as a starting point to copy and adapt: a real recipe, not a smoke test. Everything runs through the
`bmd-dataspace-utils` image, so you don't need a local BmC checkout or the micromamba environment.

Files:

- `veluwe_predator_prey.yaml` - the recipe
- `resolve_taxon_keys.py` - fills in the species keys the recipe needs

## Output

Per cell/year/species it records expected_occurrences (roughly the number of occurrences in that grid cell, but in fact
the outcome of a probabilistic calculation by the cubing engine) and distinct_observers (useful for spotting cells that
are busy only because they sit on a well-walked trail). The cube is generated in Zarr format.

## Step 1 - Resolve the taxon keys

The recipe ships with two keys verified and two left as placeholders, because a wrong key makes a species silently
absent (the engine only errors if the whole cube is empty). Resolve all four against the current GBIF backbone:

```bash
python3 resolve_taxon_keys.py
```

Standard library only, no credentials, but it needs to reach `api.gbif.org`. It prints a `taxon_keys:` line and flags
anything matched fuzzily or marked as a synonym. Paste that line over the `taxon_keys:` entry in the recipe.

## Step 2 - GBIF credentials

The cube run downloads occurrences through GBIF's authenticated download API, so it needs a free GBIF.org account (not
an API key). Register once at gbif.org, then put the three variables in the `.env` you use for the image:

```
GBIF_USER=your_gbif_username
GBIF_MAIL=your_gbif_email
GBIF_PWD=your_gbif_password
```

To skip GBIF entirely, download an occurrence export yourself and point
`sources.gbif.local_file_path` at it - the engine reads the file and makes no network call.

## Step 3 - Run the cube

The image bakes in the recipe path (`/recipe.yaml`) and the CHELSA catalog, so you only mount the recipe and an output
directory and pass `--output-dir`. The output directory must exist first, and the container runs as your host user so
the files are not written as root:

```bash
mkdir -p ./cube_output

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env-file .env \
  -v "$(pwd)/veluwe_predator_prey.yaml:/recipe.yaml:ro" \
  -v "$(pwd)/cube_output:/output" \
  ghcr.io/biodiversity-meets-data/bmd-dataspace-utils:main \
  --output-dir /output
```

The cube lands in `./cube_output/veluwe_predator_prey_2015_2025/` (the name comes from `cube_name` in the recipe),
alongside `meta/` and `logs/` subdirectories.

Exit codes: 0 success, 1 the run finished but produced no output for an enabled source, 2 bad arguments, recipe, or
credentials.

The image is public, so `docker pull` needs no login. If you would rather build it yourself, see the top-level README.

## Knobs worth knowing

The recipe comments cover these, but the three you are most likely to change:

- `max_uncertainty` (5000 m) - the wolf is a sensitive species and its coordinates are often published coarsened. A
  tight cutoff can erase the wolf layer. Raise it to keep more generalized records, lower it for sharper prey placement.
- `vector_processing.topology` (`point_cloud`) - spreads each record over cells by its coordinate uncertainty. Switch to
  `point` with
  `mapping_mode: classification` for a simpler one-record-one-cell first run.
- the bounding box and year range in the `spatial` / `temporal` blocks.
