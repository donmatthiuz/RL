"""Smoke de entrenamiento (INF-08): cada config real de agente entrena unos 2 000 pasos sin errores.

Usa `configs/<agente>.yaml` tal cual, salvo los pasos, la semilla y el dataset, que es el
mini-dataset de los tests. Corre en su propio job de la CI (`make smoke`), así un cambio en una
config o en una librería de RL se nota en el PR y no recién al entrenar con los datos reales.
"""

import json
import math

import pytest
import yaml
from test_build_dataset import CONFIG, write_raw

from polym4v import cli
from polym4v.utils.config import ExperimentConfig, load_config

pytestmark = pytest.mark.smoke

STEPS = {"ppo": 2048, "dqn": 2048, "cql": 2000, "bc": 2000}


def run(capsys, *args):
    assert cli.main(list(args)) == 0, capsys.readouterr().err
    return json.loads(capsys.readouterr().out)


@pytest.mark.parametrize("algo", list(STEPS))
def test_real_config_trains_and_its_best_checkpoint_evaluates(algo, tmp_path, capsys, monkeypatch):
    for name in ("DATA", "MODELS", "REPORTS"):
        monkeypatch.setenv(f"POLYM4V_{name}_DIR", str(tmp_path / name.lower()))
    raw = tmp_path / "data" / "raw"
    write_raw(raw, n=10)
    exclusions = tmp_path / "exclusiones.json"
    exclusions.write_text('{"descripcion": "", "slugs": [], "rangos_end_date_utc": []}')
    data_config = tmp_path / "data.yaml"
    data_config.write_text(
        yaml.safe_dump(CONFIG.model_dump(mode="json") | {"test_exclusions": str(exclusions)})
    )
    run(capsys, "build-dataset", "--config", str(data_config), "--raw", str(raw))

    config = load_config(f"configs/{algo}.yaml", ExperimentConfig)
    params = config.agent.params
    if algo == "dqn":
        # Con los 5 000 pasos de la config, DQN no llegaría a actualizar la red.
        params = params | {"learning_starts": 500}
    agent = config.agent.model_copy(
        update={"total_timesteps": STEPS[algo], "checkpoints": 2, "params": params}
    )
    config = config.model_copy(
        update={"agent": agent, "dataset_id": "prueba", "seeds": [0], "eval_split": "train"}
    )
    path = tmp_path / f"{algo}.yaml"
    path.write_text(yaml.safe_dump(config.model_dump(mode="json")))
    if config.offline is not None:
        run(capsys, "collect-offline", "--config", str(path))

    trained = run(capsys, "train", "--config", str(path))
    evaluated = run(capsys, "evaluate", "--run", trained["runs"][0]["run"], "--split", "train")
    assert evaluated["markets"] == 7 and math.isfinite(evaluated["mean_return"])
