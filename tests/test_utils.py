import json
import logging
import random
from pathlib import Path

import pytest
from pydantic import ValidationError

from polym4v.utils.config import DataConfig, load_config, save_resolved
from polym4v.utils.logging import get_logger
from polym4v.utils.paths import get_paths
from polym4v.utils.seeding import set_global_seed

REPO = Path(__file__).resolve().parents[1]

VALID = """
dataset_id: prueba
series_id: 10114
asset: BTC
date_from: 2025-05-28
date_to: 2026-10-30
step_seconds: 60
window_minutes: 60
context_minutes: 60
quality:
  min_points_in_window: 45
  max_gap_seconds: 600
split:
  train: 0.70
  val: 0.15
  test: 0.15
test_exclusions: configs/test_exclusions.json
"""


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in (
        "POLYM4V_ROOT",
        "POLYM4V_DATA_DIR",
        "POLYM4V_MODELS_DIR",
        "POLYM4V_REPORTS_DIR",
        "POLYM4V_LOG_LEVEL",
    ):
        monkeypatch.delenv(name, raising=False)


def write(tmp_path, text, name="data.yaml"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_repo_data_config_is_valid():
    config = load_config(REPO / "configs" / "data.yaml", DataConfig)
    assert config.series_id == 10114
    assert config.step_seconds == 60 and config.window_minutes == 60


def test_unknown_keys_are_rejected(tmp_path):
    with pytest.raises(ValidationError, match="extra"):
        load_config(write(tmp_path, VALID + "fee_rate: 0.07\n"), DataConfig)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("test: 0.15", "test: 0.20", "suma"),
        ("date_to: 2026-10-30", "date_to: 2025-01-01", "date_from"),
        ("step_seconds: 60", "step_seconds: 70", "divide"),
    ],
)
def test_inconsistent_values_are_rejected(tmp_path, old, new, message):
    with pytest.raises(ValidationError, match=message):
        load_config(write(tmp_path, VALID.replace(old, new)), DataConfig)


def test_config_is_immutable(tmp_path):
    config = load_config(write(tmp_path, VALID), DataConfig)
    with pytest.raises(ValidationError):
        config.series_id = 1


def test_resolved_config_round_trips(tmp_path):
    config = load_config(write(tmp_path, VALID), DataConfig)
    saved = save_resolved(config, tmp_path / "run" / "config.yaml")
    assert load_config(saved, DataConfig) == config


def test_paths_default_to_root(tmp_path):
    paths = get_paths(env_file=tmp_path / "no-existe.env", root=tmp_path)
    assert paths.raw == tmp_path / "data" / "raw"
    assert paths.models == tmp_path / "models"
    assert paths.configs == tmp_path / "configs"


def test_environment_overrides_env_file(tmp_path, monkeypatch):
    env_file = write(tmp_path, "POLYM4V_DATA_DIR=/desde/archivo\nPOLYM4V_MODELS_DIR=/m\n", ".env")
    monkeypatch.setenv("POLYM4V_DATA_DIR", str(tmp_path / "desde-entorno"))
    paths = get_paths(env_file=env_file, root=tmp_path)
    assert paths.data == tmp_path / "desde-entorno"
    assert paths.processed == tmp_path / "desde-entorno" / "processed"
    assert paths.models == Path("/m")


def test_same_seed_same_numbers():
    set_global_seed(123)
    first = [random.random() for _ in range(3)]
    set_global_seed(123)
    assert [random.random() for _ in range(3)] == first
    set_global_seed(124)
    assert [random.random() for _ in range(3)] != first


def test_seed_also_controls_numpy():
    np = pytest.importorskip("numpy")
    set_global_seed(7)
    first = np.random.rand(3)
    set_global_seed(7)
    assert np.array_equal(np.random.rand(3), first)


def test_logger_has_one_handler_and_env_level(monkeypatch):
    monkeypatch.setenv("POLYM4V_LOG_LEVEL", "DEBUG")
    logger = get_logger("polym4v.prueba")
    again = get_logger("polym4v.prueba")
    assert logger is again
    assert len(logging.getLogger("polym4v").handlers) == 1
    assert logging.getLogger("polym4v").level == logging.DEBUG


def test_cli_config_prints_resolved_config(tmp_path, capsys):
    from polym4v import cli

    assert cli.main(["config", str(write(tmp_path, VALID))]) == 0
    resolved = json.loads(capsys.readouterr().out)
    assert resolved["split"] == {"train": 0.7, "val": 0.15, "test": 0.15}
    assert resolved["date_from"] == "2025-05-28"
