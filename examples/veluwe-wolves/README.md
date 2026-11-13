# Example: Veluwe predator-prey cube

**_(NOTE: Due to recently introduced, backward-incompatible changes in the GBIF query API, which have not been addressed
yet in the Cubing Engine, this example is currently not working.)_**

A working example of a "serious" GBIF cube for the dataspace cubing engine. It is meant as a starting point to copy and
adapt: a real recipe, not a smoke test.

This example builds a yearly occurrence cube for the wolf and its three main ungulate prey species on the Veluwe, a
Dutch Natura 2000 site. Its dimensions are (grid cell x year x species). It attempts to answer a simple question: does
wolf occurrence track prey occurrence? This is why it is (and can be) a GBIF-only cube. All data points sit on the taxon
axis.

Per cell/year/species the cube contains a metric named "expected_occurrences". That's roughly the number of occurrences,
but the Cubing Engine in fact uses a more complicated, probabilistic algorithm to calculate values for the cells in the
cube. The cube is generated in parquet format.

## Executing the Recipe

If you haven't already, copy `env.template` in the root of this repository to `.env` and edit it to set the GBIF
credentials. If you don't have a GBIF account yet, you can create one for free at [gbif.org](https://www.gbif.org). Also
specify `CUBE_OUTPUT_DIR`, which is the root directory for output from the Cubing Engine. Make sure `CUBE_OUTPUT_DIR`
exists and is writable by the user you are logged in as.

Then, from the root of this repository, run:

```bash
create_cube.sh examples/veluwe-wolves/veluwe_predator_prey.yaml
# Exit codes: 0 success, 1 completed but no output for an enabled source, 2 bad arguments/recipe/credentials
```

Expect to wait a substantial amount of time as the Cubing Engine executes a query against the GBIF API. The cube ends up
in `<CUBE_OUTPUT_DIR>/veluwe_predator_prey_2015_2025/`.

For more information on running the Cubing Engine using the BMD Dataspace Docker image, see [main README](/README.md).

## Useful Recipe Details

- The name of the subdirectory ("veluwe_predator_prey_2015_2025") comes from the `cube_name` field in the recipe.
- `max_uncertainty` (5000 m) — the wolf is a sensitive species and its coordinates are often obfuscated. A tight setting
  can make the wolf layer disappear. Raise it to keep more generalized records, lower it for sharper prey placement.
- `vector_processing.topology` (`point_cloud`) — spreads each record over cells by its coordinate uncertainty. Switch to
  `point` with `mapping_mode: classification` for a simpler one-record-one-cell outcome.
- The bounding box and year range can be set in the `spatial` / `temporal` blocks.

## Output

The cubing engine will in fact output quite a few files — not simply "a cube". The most relevant files are located in
the `gbif` and `meta` subdirectories. The `meta` subdirectory contains the STAC item
(veluwe_predator_prey_2015_2025_gbif_20261106135545.json) that will be picked up by the BMD dataspace and sent to the
STAC server. The `gbif` subdirectory contains four parquet files:

- **gbif_aggregated.parquet** — comes closest to what you might call _the_ cube. However, you can't really do without:
- **gbif_EEA_1km_dimension_table.parquet** — functions as the relational parent of `gbif_aggregated.parquet`. The
  occurrence counts are grouped into 1km x 1km (square) polygons. Each row in `gbif_aggregated.parquet` only contains a
  reference to a fully specified polygon in `gbif_EEA_1km_dimension_table.parquet`.
- `gbif_unaggregated.parquet` — The raw occurrence records. This file is generated because we specified
  `export_unaggregated: true` in the recipe.
- `gbif_source_geometries.parquet` — The geometries (point locations in this case) for the raw occurrence records. The
  file has the same relation to `gbif_unaggregated.parquet` as `gbif_EEA_1km_dimension_table.parquet` has to
  `gbif_aggregated.parquet`. Oddly though, it always gets generated, even with `export_unaggregated: false`, in which
  case it loses its usefulness.

## How to Interpret the Results

To get a feel for what the Cubing Engine outputs, use
the [DuckeDB CLI](https://duckdb.org/docs/2.0/installation?platform=linux&environment=cli) to query the parquet files.
Change directory to `<CUBE_OUTPUT_DIR>/veluwe_predator_prey_2015_2025/gbif` and run `duckdb` to start the CLI. Here are
some useful queries to get you started:

```
SELECT * FROM gbif_aggregated.parquet LIMIT 5;
┌──────────┬────────────┬─────────────────────┐
│ grid_idx │ speciesKey │      datetime       │
│  int64   │  varchar   │      timestamp      │
├──────────┼────────────┼─────────────────────┤
│  8986036 │ T56G       │ 2015-01-01 00:00:00 │
│  8990035 │ T56G       │ 2015-01-01 00:00:00 │
│  8990036 │ T56G       │ 2015-01-01 00:00:00 │
│  8990037 │ T56G       │ 2015-01-01 00:00:00 │
│  8994035 │ T56G       │ 2015-01-01 00:00:00 │
└──────────┴────────────┴─────────────────────┘
```

```
SELECT * FROM gbif_EEA_1km_dimension_table.parquet limit 5;
┌──────────┬─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ grid_idx │         geometry                                                                                │
│  int64   │                                                                                                 │
├──────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤
│  8986036 │ POLYGON ((4037000 3253000, 4037000 3254000, 4036000 3254000, 4036000 3253000, 4037000 3253000)) │                                                                                                                                                                       │
├──────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤
│  8990035 │ POLYGON ((4036000 3252000, 4036000 3253000, 4035000 3253000, 4035000 3252000, 4036000 3252000)) │                                                                                                                                                                      │
├──────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤
│  8990036 │ POLYGON ((4037000 3252000, 4037000 3253000, 4036000 3253000, 4036000 3252000, 4037000 3252000)) │                                                                                                                                                                      │
├──────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤
│  8990037 │ POLYGON ((4038000 3252000, 4038000 3253000, 4037000 3253000, 4037000 3252000, 4038000 3252000)) │                                                                                                                                                                       │
├──────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤
│  8994035 │ POLYGON ((4036000 3251000, 4036000 3252000, 4035000 3252000, 4035000 3251000, 4036000 3251000)) │                                                                                                                                                                 │
└──────────┴─────────────────────────────────────────────────────────────────────────────────────────────────┘
```







