# bmd-dataspace-utils

Python scripts and programs that run on the BMD Dataspace. The scripts and programs are wrapped in a Docker image. They
are not meant to run directly on the server but via a `docker compose run` call.

Currently, there is just one script inside the Docker image: `create_cube.py`. Therefore, conveniently for now, that is
also the ENTRYPOINT of the Docker image. `create_cube.py` calls
the [Cubing Engine](https://github.com/biodiversity-meets-data/bmC) to create a data cube (see below).

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

## Cubing Engine Version

The `BMC_REF` argument at the top of the [Dockerfile](Dockerfile) specifies which version (commit/tag/branch) of the
Cubing Engine to include in the image. To try out another commit or branch of
the [BmC repository](https://github.com/biodiversity-meets-data/bmC) without editing the `Dockerfile`, run

```
docker build --build-arg BMC_REF=<commit, tag or branch> -t bmd-dataspace-utils:dev .
```

## GitHub Actions

## Creating a Cube

To create a data cube using the Docker image, first copy [env.template](env.template) to `.env`. Set CUBE_OUTPUT_DIR in
`.env` to the directory where you want the cube to be created. Set the other variables as and when needed. Then run:

```
docker compose run --rm --user "$(id -u):$(id -g)" -v "/full/path/to/my-recipe.yml:/recipe.yaml:ro" cube
```

A few things to note here:

- This will run the `python` executable inside the Docker container as "you" (`--user "$(id -u):$(id -g)"`). This is
  necessary to give the Cubing Engine write access to CUBE_OUTPUT_DIR.
- The recipe file (`my-recipe.yml`) may live anywhere on your filesystem, but be sure to specify its full path
  (starting with `/`), not a relative path.
- Your recipe file must always be mapped into the container as `/recipe.yaml` (using the `-v` option, as shown above).

A concrete (but useless) example can be found in [smoke_test.sh](tests/smoke_test.sh).
