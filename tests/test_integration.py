"""Pipeline completo por la CLI sobre un mini-dataset (INF-07).

Del crudo al dataset, el backtest de un baseline, el entrenamiento de PPO y CQL, la evaluación de
sus mejores checkpoints, el reporte y la demo, con los mismos comandos que se usan con los datos
reales.
"""

import json
from pathlib import Path

import pytest
import yaml
from streamlit.testing.v1 import AppTest
from test_build_dataset import CONFIG, write_raw

from polym4v import cli
from polym4v.utils.config import ExperimentConfig, SimulatorConfig, load_config

pytestmark = pytest.mark.integration


def run(capsys, *args):
    assert cli.main(list(args)) == 0, capsys.readouterr().err
    return json.loads(capsys.readouterr().out)


def test_pipeline_from_raw_data_to_evaluated_agents(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("POLYM4V_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("POLYM4V_MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("POLYM4V_REPORTS_DIR", str(tmp_path / "reports"))
    raw = tmp_path / "data" / "raw"
    write_raw(raw, n=10)
    exclusions = tmp_path / "exclusiones.json"
    exclusions.write_text('{"descripcion": "", "slugs": [], "rangos_end_date_utc": []}')
    data_config = tmp_path / "data.yaml"
    data_config.write_text(
        yaml.safe_dump(CONFIG.model_dump(mode="json") | {"test_exclusions": str(exclusions)})
    )
    dataset = tmp_path / "data" / "processed" / "prueba"

    # 1. Dataset con steps y normalización.
    built = run(capsys, "build-dataset", "--config", str(data_config), "--raw", str(raw))
    assert "steps.parquet" in built["files"] and built["markets_per_split"]["train"] == 7

    # 2. Un baseline por el backtest.
    simulator = load_config("configs/env.yaml", SimulatorConfig)
    sim_path = tmp_path / "env.yaml"
    sim_path.write_text(
        yaml.safe_dump(simulator.model_dump(mode="json") | {"dataset_id": "prueba"})
    )
    baseline = run(capsys, "backtest", "--policy", "fair_value", "--config", str(sim_path))
    assert baseline["markets"] == 7

    # 3. PPO corto, evaluado en train, y su mejor checkpoint por evaluate.
    for algo, steps in (("ppo", 256), ("cql", 200)):
        config = load_config(f"configs/{algo}.yaml", ExperimentConfig)
        agent = config.agent.model_copy(update={"total_timesteps": steps, "checkpoints": 2})
        if algo == "ppo":
            agent = agent.model_copy(
                update={"n_envs": 1, "params": {"n_steps": 64, "batch_size": 32}}
            )
        config = config.model_copy(
            update={"agent": agent, "dataset_id": "prueba", "seeds": [0], "eval_split": "train"}
        )
        path = tmp_path / f"{algo}.yaml"
        path.write_text(yaml.safe_dump(config.model_dump(mode="json")))
        if algo == "cql":
            collected = run(capsys, "collect-offline", "--config", str(path))
            assert collected["episodes"] == 5 * 7

        trained = run(capsys, "train", "--config", str(path))
        folder = trained["runs"][0]["run"]
        evaluated = run(capsys, "evaluate", "--run", folder, "--split", "train")
        assert evaluated["markets"] == 7
        assert evaluated["mean_return"] == pytest.approx(trained["runs"][0]["best"]["mean_return"])

    # 4. Test sigue cerrado sin permiso explícito.
    assert cli.main(["evaluate", "--run", folder, "--split", "test"]) == 1
    assert "una sola vez" in capsys.readouterr().err

    # 5. Reporte de train con el baseline y los dos agentes, y sus curvas de aprendizaje.
    report = run(capsys, "report", "--split", "train", "--config", str(sim_path))
    assert len(report["policies"]) == 3 and len(report["runs"]) == 2
    assert "learning.png" in report["files"]

    # 6. La demo abre las trayectorias del mini-dataset (criterio de EVA-07).
    demo = AppTest.from_file(str(Path(__file__).parents[1] / "app" / "demo.py"), default_timeout=30)
    demo.run()
    demo.switch_page("views/simulation.py").run()
    assert not demo.exception
    assert len(demo.sidebar.selectbox[0].options) == 3
    assert len(demo.sidebar.selectbox[1].options) == 7
    assert dataset.exists()
