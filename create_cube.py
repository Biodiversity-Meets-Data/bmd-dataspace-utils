#!/usr/bin/env python
"""Generate a data cube from a recipe file.

    create_cube.py RECIPE [--output-dir DIR] [--catalog FILE] [--max-workers N]

The recipe is a YAML file in the BmC recipe format (see config/template_recipe.yaml
in the BmC repository). Paths
that depend on the machine the engine runs on (the output directory and the
CHELSA catalog) can be overridden here, so the same recipe works on a laptop,
in a container and on a cluster.

Precedence for both: command line option, then environment variable
(BMC_OUTPUT_DIR, BMC_CHELSA_CATALOG), then the value in the recipe.

Credentials are read from the environment and never prompted for:
    GBIF_USER, GBIF_MAIL, GBIF_PWD    GBIF source, unless it uses local_file_path
    HDA_USER, HDA_PASSWORD            WEkEO source

Exit status: 0 on success, 1 if cube generation failed or wrote no output for
an enabled source, 2 if the invocation, recipe or credentials are invalid.
"""
import argparse
import faulthandler
import logging
import os
import sys
import tempfile

import yaml

EXIT_FAILED = 1
EXIT_INVALID = 2

CHECKED_SOURCES = ("chelsa", "gbif")
GBIF_VARS = ("GBIF_USER", "GBIF_MAIL", "GBIF_PWD")
WEKEO_VARS = ("HDA_USER", "HDA_PASSWORD")


class InvalidInput(Exception):
    pass


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="create_cube.py",
        description="Generate a data cube from a recipe file.",
    )
    parser.add_argument("recipe", help="path to the YAML recipe")
    parser.add_argument(
        "--output-dir",
        default=os.environ.get("BMC_OUTPUT_DIR"),
        help="replaces base_dir from the recipe; the cube is written to "
        "<output-dir>/<cube_name>",
    )
    parser.add_argument(
        "--catalog",
        default=os.environ.get("BMC_CHELSA_CATALOG"),
        help="replaces sources.chelsa.catalog_path from the recipe",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="number of parallel workers (default: %(default)s)",
    )
    return parser.parse_args(argv)


def load_recipe(path):
    try:
        with open(path, encoding="utf-8") as f:
            recipe = yaml.safe_load(f)
    except OSError as e:
        raise InvalidInput(f"cannot read recipe: {e}")
    except yaml.YAMLError as e:
        raise InvalidInput(f"recipe is not valid YAML: {e}")
    if not isinstance(recipe, dict):
        raise InvalidInput("recipe must be a YAML mapping")
    return recipe


def apply_overrides(recipe, output_dir, catalog):
    if output_dir:
        recipe["base_dir"] = output_dir
    if not recipe.get("base_dir"):
        raise InvalidInput(
            "no output location: set base_dir in the recipe or pass --output-dir"
        )
    if "spatial" not in recipe:
        raise InvalidInput("recipe has no 'spatial' section")

    chelsa = (recipe.get("sources") or {}).get("chelsa")
    if catalog and chelsa is not None:
        chelsa["catalog_path"] = catalog
    if chelsa and chelsa.get("enabled", False):
        path = chelsa.get("catalog_path")
        if not path or not os.path.isfile(path):
            raise InvalidInput(f"CHELSA catalog not found: {path!r}")


def source_enabled(recipe, name):
    cfg = (recipe.get("sources") or {}).get(name)
    return cfg is not None and cfg.get("enabled", True)


def read_credentials(recipe):
    """Collect credentials for the enabled sources.

    The GBIF dictionary is passed on to the engine. Without it the engine
    would fall back to an interactive prompt, which would hang in a container.
    """
    creds = None
    missing = []

    if source_enabled(recipe, "gbif") and not recipe["sources"]["gbif"].get(
        "local_file_path"
    ):
        missing += [v for v in GBIF_VARS if not os.environ.get(v)]
        creds = {v: os.environ.get(v) for v in GBIF_VARS}

    cfg = (recipe.get("sources") or {}).get("wekeo")
    if cfg and cfg.get("enabled", False):
        missing += [v for v in WEKEO_VARS if not os.environ.get(v)]

    if missing:
        raise InvalidInput("missing environment variables: " + ", ".join(missing))
    return creds


def missing_outputs(recipe, cube_dir):
    """Enabled sources for which the engine wrote no files.

    The engine puts the output of each source in <cube_dir>/<source>. It can
    finish without error and still have written nothing, for example when it
    fails to find the code for a source.
    """
    sources = recipe.get("sources") or {}
    missing = []
    for name in CHECKED_SOURCES:
        cfg = sources.get(name)
        if cfg is None or not cfg.get("enabled", name == "gbif"):
            continue
        path = os.path.join(cube_dir, name)
        if not any(files for _, _, files in os.walk(path)):
            missing.append(name)
    return missing


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logger = logging.getLogger("create_cube")

    try:
        recipe = load_recipe(args.recipe)
        apply_overrides(recipe, args.output_dir, args.catalog)
        creds = read_credentials(recipe)
    except InvalidInput as e:
        logger.error("%s", e)
        return EXIT_INVALID

    faulthandler.enable()

    # Imported late: it pulls in GDAL, dask and friends, which takes a while
    # and is wasted effort when the arguments turn out to be wrong.
    from bmc.cube.orchestrator.bmd import bmdCube

    # The engine reads its recipe from a file, so hand it the effective one.
    with tempfile.TemporaryDirectory() as tmp:
        effective = os.path.join(tmp, "recipe.yaml")
        with open(effective, "w", encoding="utf-8") as f:
            yaml.safe_dump(recipe, f, sort_keys=False)
        try:
            bmdCube().process_recipe(
                recipe_file=effective,
                recipe_path=tmp,
                max_workers=args.max_workers,
                logger=logger,
                creds=creds,
            )
        except Exception:
            logger.exception("cube generation failed")
            return EXIT_FAILED

    cube_dir = os.path.join(recipe["base_dir"], recipe.get("cube_name", "default_cube"))
    missing = missing_outputs(recipe, cube_dir)
    if missing:
        logger.error("no output written for: %s", ", ".join(missing))
        return EXIT_FAILED
    logger.info("cube written to %s", cube_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())