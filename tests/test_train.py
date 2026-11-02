import json
from datetime import UTC, datetime

import pytest
import yaml

from polym4v.agents.adapters import SB3Policy
from polym4v.agents.base import Action
from polym4v.agents.train_sb3 import run_id, train
from polym4v.data.steps import align
from polym4v.env.market_env import PolymarketEnv
from polym4v.env.synthetic import synthetic_data, synthetic_frames
from polym4v.evaluation.backtest import run_backtest
from polym4v.evaluation.metrics import summarize
from polym4v.features.market import MARKET_FEATURES, add_features, fit_zscore
from polym4v.utils.config import ExperimentConfig, SimulatorConfig, load_config

SIM = load_config("configs/env.yaml", SimulatorConfig)
TINY = {
    "ppo": {"n_envs": 1, "params": {"n_steps": 64, "batch_size": 32}},
    "dqn": {"n_envs": 1, "params": {"learning_starts": 0, "buffer_size": 1000}},
}


def experiment(algo, timesteps, checkpoints=2, **agent):
    return ExperimentConfig(
        dataset_id="sintetico",
        env=SIM.env,
        reward=SIM.reward,
        seeds=[0],
        eval_split="train",
        agent={
            "algo": algo,
            "learning_rate": 3e-4,
            "gamma": 0.999,
            "total_timesteps": timesteps,
            "checkpoints": checkpoints,
            **(TINY[algo] | agent),
        },
    )


@pytest.mark.parametrize("algo", ["ppo", "dqn"])
def test_train_keeps_the_best_checkpoint_and_records_the_run(algo, tmp_path):
    data = synthetic_data(4, seed=13)
    metrics = train(experiment(algo, 256), 0, data, data, tmp_path / "run")

    run = tmp_path / "run"
    assert {"config.yaml", "metrics.json", "best.zip", "checkpoints", "tensorboard"} <= {
        p.name for p in run.iterdir()
    }
    assert len(metrics["checkpoints"]) == 2 and len(list((run / "checkpoints").iterdir())) == 2
    best = max(c["mean_return"] for c in metrics["checkpoints"])
    assert metrics["best"]["mean_return"] == best and metrics["seed"] == 0
    assert json.loads((run / "metrics.json").read_text())["eval_markets"] == 4
    assert yaml.safe_load((run / "config.yaml").read_text())["agent"]["algo"] == algo
    policy = SB3Policy.load(run / "best.zip", algo)
    obs, _ = PolymarketEnv(data, SIM.env, SIM.reward).reset(seed=0)
    assert policy.act(obs) in set(Action)


def test_run_id_follows_the_convention():
    now = datetime(2026, 11, 1, 12, 30, tzinfo=UTC)
    assert run_id(experiment("ppo", 10), 3, now) == "20261101-123000_ppo_pnl_s3"


@pytest.mark.parametrize("name", ["ppo", "dqn", "cql", "bc"])
def test_agents_use_the_same_simulator_as_the_baselines(name):
    """Los baselines corren con configs/env.yaml: los agentes no pueden tener otras reglas."""
    config = load_config(f"configs/{name}.yaml", ExperimentConfig)
    assert config.env == SIM.env and config.reward == SIM.reward
    assert config.dataset_id == SIM.dataset_id and config.agent.algo == name


def test_cli_train_runs_each_seed(tmp_path, capsys):
    from polym4v import cli

    markets, prices, spot = synthetic_frames(4)
    markets.loc[3, "split"] = "val"
    steps = add_features(align(markets, prices, spot, step_s=60, n_steps=60), 3600)
    for name, frame in (("markets", markets), ("steps", steps), ("prices_raw", prices)):
        frame.to_parquet(tmp_path / f"{name}.parquet")
    (tmp_path / "normalization.json").write_text(json.dumps({"features": fit_zscore(steps)}))
    (tmp_path / "manifest.json").write_text(json.dumps({"config": {"step_seconds": 60}}))
    config = experiment("ppo", 128).model_dump(mode="json")
    (tmp_path / "ppo.yaml").write_text(yaml.safe_dump(config))
    args = ["train", "--config", str(tmp_path / "ppo.yaml"), "--dataset", str(tmp_path)]

    assert cli.main([*args, "--out", str(tmp_path / "models"), "--seed", "1", "--seed", "2"]) == 0

    result = json.loads(capsys.readouterr().out)
    assert [run["seed"] for run in result["runs"]] == [1, 2]
    assert all((tmp_path / "models" / "ppo").glob("*_ppo_pnl_s*"))


def edge_rule(env, threshold=0.12):
    """Regla de referencia en el mercado atrasado: comprar el lado barato según `edge`."""
    edge = MARKET_FEATURES.index("edge")

    class Rule:
        name = "regla_edge"

        def act(self, obs, info=None):
            if obs[-3] != 0:
                return Action.WAIT
            if obs[edge] > threshold:
                return Action.BUY_YES
            return Action.BUY_NO if obs[edge] < -threshold else Action.WAIT

        def reset(self):
            pass

    return summarize(run_backtest(Rule(), env), 1000.0, 20.0)["mean_return"]


@pytest.mark.slow
@pytest.mark.parametrize("algo", ["ppo", "dqn"])
def test_agent_learns_a_real_delay_and_finds_nothing_in_the_null_market(algo, tmp_path):
    """AGT-06: con 2 minutos de retraso supera la regla de referencia; sin retraso, no gana.

    Usa la config real del agente, con 150 000 pasos y la evaluación en los mercados sintéticos.
    """
    config = load_config(f"configs/{algo}.yaml", ExperimentConfig)
    params = config.agent.params
    if algo == "dqn":
        params = params | {"learning_starts": 2000, "target_update_interval": 1000}
    agent = config.agent.model_copy(update={"total_timesteps": 150_000, "params": params})
    config = config.model_copy(update={"agent": agent, "eval_split": "train"})

    lagged_train = synthetic_data(600, lag_s=120, seed=31)
    lagged_eval = synthetic_data(300, lag_s=120, seed=32)
    best = train(config, 0, lagged_train, lagged_eval, tmp_path / "atrasado")["best"]
    reference = edge_rule(PolymarketEnv(lagged_eval, SIM.env, SIM.reward))
    assert best["mean_return"] >= 0.9 * reference > 0

    null_train, null_eval = synthetic_data(600, seed=41), synthetic_data(300, seed=42)
    metrics = train(config, 0, null_train, null_eval, tmp_path / "nulo")
    # Sin retraso no hay nada que aprender: ningún checkpoint pasa del ruido de 300 mercados.
    assert max(c["mean_return"] for c in metrics["checkpoints"]) < 0.1
