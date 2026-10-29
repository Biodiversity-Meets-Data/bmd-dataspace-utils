# bmd-dataspace-utils

Python scripts and programs that run on the BMD Dataspace. The scripts and programs are wrapped in a Docker image. They
are not meant to run directly on the server but inside a Docker container.

Currently, there is just one script inside the Docker image: `create_cube.py`. Therefore, conveniently for now, that is
also the ENTRYPOINT of the Docker image. `create_cube.py` calls
the [Cubing Engine](https://github.com/biodiversity-meets-data/BmC) to create a data cube (see below).

## Creating a Cube

### Using Plain Docker

```
mkdir -p /full/path/to/cubes
docker run --rm --user "$(id -u):$(id -g)" \
  --env-file my.env \
  -v "/full/path/to/cubes:/output" \
  -v "/full/path/to/my-recipe.yaml:/recipe.yaml:ro" \
  ghcr.io/biodiversity-meets-data/bmd-dataspace-utils:main
```

`my.env` contains the credentials the recipe needs (see [below](#data-sources-and-credentials)). Leave out `--env-file`
if the recipe needs none. Make sure `/full/path/to/cubes` exists. Cubes will end up in
`/full/path/to/cubes/<cube_name>`. Use another tag than `main` to run a specific version of the bmd-dataspace-utils
image.

### Using Docker Compose

Alternatively, like the BMD Dataspace itself, you can use `docker compose` and the `docker-compose.yml` file in this
repository:

```
git clone https://github.com/Biodiversity-Meets-Data/bmd-dataspace-utils.git
# or: git@github.com:Biodiversity-Meets-Data/bmd-dataspace-utils.git
cd bmd-dataspace-utils
cp env.template .env
# Edit the .env file: set CUBE_OUTPUT_DIR to the directory where you want the cubes to be created.
# Make sure the directory exists.
docker compose run --rm \
    --user "$(id -u):$(id -g)" \
    -v "/full/path/to/my-recipe.yml:/recipe.yaml:ro" \
    cube
```

A few things to note about the last (`docker compose run`) command:

- This will run the `python` executable inside the Docker container as "you" (`--user "$(id -u):$(id -g)"`). This is
  necessary to give the Cubing Engine write access to CUBE_OUTPUT_DIR.
- The recipe file (`my-recipe.yml`) may live anywhere on your filesystem, but be sure to specify its full path
  (starting with `/`), not a relative path.
- Your recipe file must always be mapped into the container as `/recipe.yaml` (using the `-v` option, as shown above).

A concrete (but useless) example can be found in [smoke_test.sh](tests/smoke_test.sh).

### Data Sources and Credentials

The cubing engine combines data from CHELSA (climate), CLMS (Copernicus land cover) and GBIF (species occurrences)
into one data cube. The sources are enabled in the recipe, and they share the grid and time axis defined there. Only
CHELSA and GBIF have been tested in this image so far. CHELSA needs no credentials. GBIF needs GBIF_USER, GBIF_MAIL and
GBIF_PWD in .env, unless the recipe points to a local GBIF file. CLMS needs a credentials file that this image does not
yet provide.

## Building the Docker Image

### From the Command Line

To build the Docker image from the command line, simply run:

```
docker build -t bmd-dataspace-utils .
```

### In GitHub (GitHub Actions)

Every pull request triggers a build pipeline that runs the unit tests, builds the image and runs
a [smoke test](tests/smoke_test.sh). However, the image only gets _published_ to GitHub's container registry if you
merge or push to `main`, or if you push a git tag starting with `v`. To see the list of published images, go to
https://github.com/Biodiversity-Meets-Data/bmd-dataspace-utils/pkgs/container/bmd-dataspace-utils.

The build pipeline is specified in [.github/workflows/docker.yml](.github/workflows/docker.yml).

### Cubing Engine Version

The `BMC_REF` argument at the top of the [Dockerfile](Dockerfile) specifies which version (commit/tag/branch) of the
Cubing Engine to include in the image. To try out another commit or branch of
the [BmC repository](https://github.com/biodiversity-meets-data/bmC) without editing the `Dockerfile`, run

```
docker build --build-arg BMC_REF=<commit, tag or branch> -t bmd-dataspace-utils:dev .
```
