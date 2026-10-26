# bmd-dataspace-utils

Python scripts and programs that run on the BMD dataspace (WP4). For now, that is just one thing: running the Cubing
Engine.

## Docker Image

`create_cube.py` is the entrypoint of the image.

```
create_cube.py RECIPE [--output-dir DIR] [--catalog FILE] [--max-workers N]
```

| Option         | Environment variable | Replaces in the recipe        |
|----------------|----------------------|-------------------------------|
| `--output-dir` | `BMC_OUTPUT_DIR`     | `base_dir`                    |
| `--catalog`    | `BMC_CHELSA_CATALOG` | `sources.chelsa.catalog_path` |

The image sets both variables, so recipes need not contain machine-specific
paths. The cube ends up in `<output dir>/<cube_name>`.

Credentials are read from environment variables and are never prompted for:

| Source                                 | Variables                            |
|----------------------------------------|--------------------------------------|
| GBIF (unless `local_file_path` is set) | `GBIF_USER`, `GBIF_MAIL`, `GBIF_PWD` |
| WEkEO                                  | `HDA_USER`, `HDA_PASSWORD`           |

Exit status: `0` success, `1` cube generation failed, `2` invalid arguments,
recipe or credentials.

### Running

Put credentials in a `.env` file next to `docker-compose.yml` (it is ignored by
git), recipes in `recipes/`, and run:

```
docker compose run --rm cube /recipes/smoke_test.yaml
```

Everything after the service name is passed to `create_cube.py`. Cubes appear in
`output/`. The CHELSA data is read over HTTPS from `os.unil.cloud.switch.ch`, so
the container needs internet access.

### BmC Version

The `BMC_REF` argument at the top of the `Dockerfile` is the BmC commit that is
built into the image (also recorded in the image label `bmc.commit`). To ship a
newer engine, change that value. To try another commit or branch of BmC without
editing anything:

```
docker build --build-arg BMC_REF=<commit, tag or branch> -t bmd-dataspace-utils:dev .
```

The pipeline (`.github/workflows/docker.yml`) builds on every pull request and
publishes to `ghcr.io/biodiversity-meets-data/bmd-dataspace-utils` on pushes to
`main` and on `v*` tags.
