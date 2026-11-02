import json
from pathlib import Path

import yaml

from polym4v.agents.hparams import (
    FINAL_SEEDS,
    GRID,
    SEEDS,
    point_id,
    points,
    write_final,
    write_grid,
)
from polym4v.cli import main
from polym4v.utils.config import ExperimentConfig, load_config


def test_la_grilla_respeta_el_limite_de_agt09():
    for algo in GRID:
        assert 1 <= len(points(algo)) <= 20


def test_cada_punto_es_una_config_valida_con_sus_valores(tmp_path):
    written = write_grid(Path("configs"), tmp_path)
    assert len(written) == sum(len(points(algo)) for algo in GRID)
    point = {"learning_rate": 1e-4, "params.ent_coef": 0.01, "net_arch": [128, 128]}
    config = load_config(tmp_path / "ppo" / f"{point_id(point)}.yaml", ExperimentConfig)
    assert config.agent.learning_rate == 1e-4 and config.agent.net_arch == [128, 128]
    assert config.agent.params["ent_coef"] == 0.01 and config.seeds == SEEDS
    base = load_config("configs/ppo.yaml", ExperimentConfig)
    assert config.reward == base.reward and config.env == base.env


def test_la_tabla_agrupa_por_carpeta_y_elige_por_algoritmo(tmp_path, capsys):
    for folder, algo, best in (("a", "ppo", 0.01), ("b", "ppo", 0.03), ("c", "dqn", -0.01)):
        for seed in SEEDS:
            run_id = f"20261102-0800{seed:02d}_{algo}_pnl_risk_s{seed}"
            path = tmp_path / "models" / folder / algo / run_id
            path.mkdir(parents=True)
            point = {
                "timesteps": 100,
                "mean_return": best,
                "trades_per_market": 0.1,
                "no_trade_share": 0.9,
            }
            metrics = {"run_id": run_id, "eval_split": "val", "best": point, "checkpoints": [point]}
            (path / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
            (path / "config.yaml").write_text(yaml.safe_dump({"reward": {"name": "pnl_risk"}}))
    out = tmp_path / "reports"
    assert main(["hparams", "--models", str(tmp_path / "models"), "--out", str(out)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["best_by_algo"] == {"ppo": "ppo/b", "dqn": "dqn/c"}
    assert "Búsqueda de hiperparámetros" in (out / "hparams.md").read_text(encoding="utf-8")


def test_la_config_final_es_el_mejor_punto_con_cinco_semillas(tmp_path):
    write_grid(Path("configs"), tmp_path / "grid")
    point = {"params.alpha": 4.0, "learning_rate": 3e-5}
    best = {"cql": f"cql/{point_id(point)}"}
    (path,) = write_final(tmp_path / "grid", best, tmp_path / "final")
    config = load_config(path, ExperimentConfig)
    assert path.name == "cql.yaml" and config.seeds == FINAL_SEEDS
    assert config.agent.params["alpha"] == 4.0 and config.agent.learning_rate == 3e-5
