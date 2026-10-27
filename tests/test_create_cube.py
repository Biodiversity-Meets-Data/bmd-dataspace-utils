import logging
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

import create_cube
from create_cube import InvalidInput

RECIPE = """
cube_name: demo
spatial: {target_grid: EEA}
sources:
  chelsa: {enabled: true}
  gbif: {enabled: false}
"""

CREDENTIAL_VARS = [
    "GBIF_USER", "GBIF_MAIL", "GBIF_PWD",
    "HDA_USER", "HDA_PASSWORD",
    "BMC_OUTPUT_DIR", "BMC_CHELSA_CATALOG",
]


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in CREDENTIAL_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def catalog(tmp_path):
    path = tmp_path / "catalog.parquet"
    path.touch()
    return path


def write_recipe(tmp_path, text=RECIPE):
    path = tmp_path / "recipe.yaml"
    path.write_text(text)
    return path


def recipe_dict(text=RECIPE):
    return yaml.safe_load(text)


class MockEngine:
    """Stands in for bmc.cube.orchestrator.bmd.bmdCube."""

    def __init__(self):
        self.calls = []
        self.recipes = []
        self.writes = []
        self.error = None


@pytest.fixture
def engine(monkeypatch):
    mock_engine = MockEngine()

    class bmdCube:
        def process_recipe(self, recipe_file, recipe_path, max_workers, logger, creds):
            with open(recipe_file, encoding="utf-8") as f:
                recipe = yaml.safe_load(f)
            mock_engine.recipes.append(recipe)
            mock_engine.calls.append(
                {"recipe_file": recipe_file, "max_workers": max_workers, "creds": creds}
            )
            if mock_engine.error:
                raise mock_engine.error
            cube_dir = Path(recipe["base_dir"]) / recipe["cube_name"]
            for relative in mock_engine.writes:
                target = cube_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("x")

    names = ["bmc", "bmc.cube", "bmc.cube.orchestrator", "bmc.cube.orchestrator.bmd"]
    for name in names:
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    sys.modules["bmc.cube.orchestrator.bmd"].bmdCube = bmdCube
    return mock_engine


def run(tmp_path, catalog, *extra, recipe=RECIPE):
    path = write_recipe(tmp_path, recipe)
    argv = [str(path), "--output-dir", str(tmp_path / "out"), "--catalog", str(catalog)]
    return create_cube.main(argv + list(extra))


class TestParseArgs:
    def test_defaults(self):
        args = create_cube.parse_args(["recipe.yaml"])
        assert args.recipe == "recipe.yaml"
        assert args.output_dir is None
        assert args.catalog is None
        assert args.max_workers == 4

    def test_environment_supplies_defaults(self, monkeypatch):
        monkeypatch.setenv("BMC_OUTPUT_DIR", "/output")
        monkeypatch.setenv("BMC_CHELSA_CATALOG", "/app/catalog.parquet")
        args = create_cube.parse_args(["recipe.yaml"])
        assert args.output_dir == "/output"
        assert args.catalog == "/app/catalog.parquet"

    def test_option_beats_environment(self, monkeypatch):
        monkeypatch.setenv("BMC_OUTPUT_DIR", "/output")
        args = create_cube.parse_args(["recipe.yaml", "--output-dir", "/elsewhere"])
        assert args.output_dir == "/elsewhere"


class TestLoadRecipe:
    def test_reads_a_mapping(self, tmp_path):
        path = write_recipe(tmp_path)
        assert create_cube.load_recipe(path)["cube_name"] == "demo"

    def test_missing_file(self, tmp_path):
        with pytest.raises(InvalidInput, match="cannot read recipe"):
            create_cube.load_recipe(tmp_path / "nope.yaml")

    def test_broken_yaml(self, tmp_path):
        path = write_recipe(tmp_path, "a: [1, 2")
        with pytest.raises(InvalidInput, match="not valid YAML"):
            create_cube.load_recipe(path)

    @pytest.mark.parametrize("text", ["- a\n- b\n", "just text\n", ""])
    def test_not_a_mapping(self, tmp_path, text):
        path = write_recipe(tmp_path, text)
        with pytest.raises(InvalidInput, match="must be a YAML mapping"):
            create_cube.load_recipe(path)


class TestApplyOverrides:
    def test_output_dir_replaces_base_dir(self, catalog):
        recipe = recipe_dict("base_dir: /from/recipe\n" + RECIPE)
        create_cube.apply_overrides(recipe, "/from/option", str(catalog))
        assert recipe["base_dir"] == "/from/option"

    def test_base_dir_from_recipe_is_kept(self, catalog):
        recipe = recipe_dict("base_dir: /from/recipe\n" + RECIPE)
        create_cube.apply_overrides(recipe, None, str(catalog))
        assert recipe["base_dir"] == "/from/recipe"

    def test_no_output_location(self, catalog):
        with pytest.raises(InvalidInput, match="no output location"):
            create_cube.apply_overrides(recipe_dict(), None, str(catalog))

    def test_spatial_section_is_required(self, catalog):
        recipe = recipe_dict("cube_name: demo\n")
        with pytest.raises(InvalidInput, match="no 'spatial' section"):
            create_cube.apply_overrides(recipe, "/out", str(catalog))

    def test_catalog_replaces_catalog_path(self, catalog):
        recipe = recipe_dict(
            "cube_name: demo\nspatial: {}\n"
            "sources: {chelsa: {enabled: true, catalog_path: 'C:/elsewhere.parquet'}}\n"
        )
        create_cube.apply_overrides(recipe, "/out", str(catalog))
        assert recipe["sources"]["chelsa"]["catalog_path"] == str(catalog)

    def test_missing_catalog_file(self, tmp_path):
        with pytest.raises(InvalidInput, match="CHELSA catalog not found"):
            create_cube.apply_overrides(recipe_dict(), "/out", str(tmp_path / "nope"))

    def test_no_catalog_at_all(self):
        with pytest.raises(InvalidInput, match="CHELSA catalog not found: None"):
            create_cube.apply_overrides(recipe_dict(), "/out", None)

    def test_catalog_is_not_needed_without_chelsa(self):
        recipe = recipe_dict(
            "cube_name: demo\nspatial: {}\nsources: {chelsa: {enabled: false}}\n"
        )
        create_cube.apply_overrides(recipe, "/out", None)


class TestReadCredentials:
    GBIF = {"GBIF_USER": "u", "GBIF_MAIL": "m", "GBIF_PWD": "p"}

    def test_nothing_needed_without_gbif_or_wekeo(self):
        assert create_cube.read_credentials(recipe_dict()) is None

    def test_gbif_is_enabled_unless_switched_off(self):
        recipe = recipe_dict("sources: {gbif: {}}\n")
        with pytest.raises(InvalidInput, match="GBIF_USER, GBIF_MAIL, GBIF_PWD"):
            create_cube.read_credentials(recipe)

    def test_gbif_credentials_are_returned(self, monkeypatch):
        for name, value in self.GBIF.items():
            monkeypatch.setenv(name, value)
        recipe = recipe_dict("sources: {gbif: {enabled: true}}\n")
        assert create_cube.read_credentials(recipe) == self.GBIF

    def test_only_the_missing_variables_are_named(self, monkeypatch):
        monkeypatch.setenv("GBIF_USER", "u")
        recipe = recipe_dict("sources: {gbif: {enabled: true}}\n")
        with pytest.raises(InvalidInput) as error:
            create_cube.read_credentials(recipe)
        assert "GBIF_MAIL, GBIF_PWD" in str(error.value)
        assert "GBIF_USER" not in str(error.value)

    def test_local_file_needs_no_gbif_credentials(self):
        recipe = recipe_dict("sources: {gbif: {local_file_path: data.zip}}\n")
        assert create_cube.read_credentials(recipe) is None

    def test_wekeo_is_off_by_default(self):
        recipe = recipe_dict("sources: {wekeo: {}}\n")
        assert create_cube.read_credentials(recipe) is None

    def test_wekeo_needs_credentials_when_enabled(self):
        recipe = recipe_dict("sources: {wekeo: {enabled: true}}\n")
        with pytest.raises(InvalidInput, match="HDA_USER, HDA_PASSWORD"):
            create_cube.read_credentials(recipe)


class TestMissingOutputs:
    def cube(self, tmp_path, *files):
        for relative in files:
            target = tmp_path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x")
        return str(tmp_path)

    def test_files_in_the_chelsa_folder(self, tmp_path):
        cube = self.cube(tmp_path, "chelsacube/monthly/tas.nc")
        assert create_cube.missing_outputs(recipe_dict(), cube) == []

    def test_older_folder_name(self, tmp_path):
        cube = self.cube(tmp_path, "chelsa/bioclim/bio01.nc")
        assert create_cube.missing_outputs(recipe_dict(), cube) == []

    def test_only_meta_and_logs(self, tmp_path):
        cube = self.cube(tmp_path, "meta/provenance.json", "logs/run_chelsa.log")
        assert create_cube.missing_outputs(recipe_dict(), cube) == ["chelsa"]

    def test_empty_folder(self, tmp_path):
        (tmp_path / "chelsacube").mkdir()
        assert create_cube.missing_outputs(recipe_dict(), str(tmp_path)) == ["chelsa"]

    def test_cube_folder_does_not_exist(self, tmp_path):
        assert create_cube.missing_outputs(recipe_dict(), str(tmp_path / "x")) == ["chelsa"]

    def test_each_enabled_source_is_checked(self, tmp_path):
        recipe = recipe_dict("sources: {chelsa: {enabled: true}, gbif: {}}\n")
        cube = self.cube(tmp_path, "chelsacube/monthly/tas.nc")
        assert create_cube.missing_outputs(recipe, cube) == ["gbif"]

    def test_disabled_sources_are_ignored(self, tmp_path):
        recipe = recipe_dict("sources: {chelsa: {enabled: false}, gbif: {enabled: false}}\n")
        assert create_cube.missing_outputs(recipe, str(tmp_path)) == []


class TestMain:
    def test_success(self, tmp_path, catalog, engine, caplog):
        caplog.set_level(logging.INFO)
        engine.writes = ["chelsacube/monthly/tas.nc"]
        assert run(tmp_path, catalog) == 0
        assert "cube written to" in caplog.text

    def test_engine_gets_the_effective_recipe(self, tmp_path, catalog, engine):
        engine.writes = ["chelsacube/monthly/tas.nc"]
        run(tmp_path, catalog)
        sent = engine.recipes[0]
        assert sent["base_dir"] == str(tmp_path / "out")
        assert sent["sources"]["chelsa"]["catalog_path"] == str(catalog)
        assert Path(engine.calls[0]["recipe_file"]).is_absolute()

    def test_max_workers_is_passed_on(self, tmp_path, catalog, engine):
        engine.writes = ["chelsacube/monthly/tas.nc"]
        run(tmp_path, catalog, "--max-workers", "2")
        assert engine.calls[0]["max_workers"] == 2

    def test_gbif_credentials_are_passed_on(self, tmp_path, catalog, engine, monkeypatch):
        for name in ("GBIF_USER", "GBIF_MAIL", "GBIF_PWD"):
            monkeypatch.setenv(name, name.lower())
        engine.writes = ["chelsacube/monthly/tas.nc", "gbif/occurrences.parquet"]
        recipe = RECIPE.replace("{enabled: false}", "{enabled: true}")
        assert run(tmp_path, catalog, recipe=recipe) == 0
        assert engine.calls[0]["creds"] == {
            "GBIF_USER": "gbif_user", "GBIF_MAIL": "gbif_mail", "GBIF_PWD": "gbif_pwd",
        }

    def test_engine_failure(self, tmp_path, catalog, engine, caplog):
        engine.error = RuntimeError("boom")
        assert run(tmp_path, catalog) == 1
        assert "cube generation failed" in caplog.text
        assert "boom" in caplog.text

    def test_silent_failure_of_the_engine(self, tmp_path, catalog, engine, caplog):
        assert run(tmp_path, catalog) == 1
        assert "no output written for: chelsa" in caplog.text

    def test_invalid_recipe_does_not_reach_the_engine(self, tmp_path, catalog, engine):
        assert run(tmp_path, catalog, recipe="- not a mapping\n") == 2
        assert engine.calls == []

    def test_missing_credentials_do_not_reach_the_engine(self, tmp_path, catalog, engine, caplog):
        recipe = RECIPE.replace("{enabled: false}", "{enabled: true}")
        assert run(tmp_path, catalog, recipe=recipe) == 2
        assert "GBIF_USER" in caplog.text
        assert engine.calls == []

    def test_recipe_file_does_not_exist(self, tmp_path, catalog, engine):
        argv = [str(tmp_path / "nope.yaml"), "--output-dir", str(tmp_path), "--catalog", str(catalog)]
        assert create_cube.main(argv) == 2
