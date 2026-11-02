import json

import numpy as np
import pytest
import yaml
from pydantic import ValidationError

from polym4v.agents.adapters import D3rlpyPolicy
from polym4v.agents.base import Action
from polym4v.agents.baselines import FavoritePolicy, NoTradePolicy
from polym4v.agents.offline import (
    build_offline_dataset,
    collect,
    load_offline_dataset,
    offline_path,
    train_offline,
)
from polym4v.data.steps import align
from polym4v.env.market_env import PolymarketEnv
from polym4v.env.synthetic import synthetic_data, synthetic_frames
from polym4v.features.market import add_features, fit_zscore
from polym4v.utils.config import ExperimentConfig, SimulatorConfig, load_config

SIM = load_config("configs/env.yaml", SimulatorConfig)
OFFLINE = {"policies": ["favorite", "fair_value", "no_trade"], "epsilon": 0.2, "seed": 0}


def experiment(algo, steps=200, **offline):
    return ExperimentConfig(
        dataset_id="sintetico",
        env=SIM.env,
        reward=SIM.reward,
        seeds=[0],
        eval_split="train",
        offline=OFFLINE | offline,
        agent={
            "algo": algo,
            "learning_rate": 3e-4,
            "gamma": 0.999,
            "total_timesteps": steps,
            "checkpoints": 2,
            "params": {"batch_size": 32},
        },
    )


@pytest.fixture(scope="module")
def data():
    return synthetic_data(6, seed=14)


class AlwaysSell:
    name = "siempre_vende"

    def act(self, obs, info=None):
        return Action.SELL

    def reset(self):
        pass


def test_dataset_keeps_the_executed_action_not_the_requested_one(data):
    """S6: SELL sin posición es inválida y queda como WAIT en el dataset."""
    env = PolymarketEnv(data, SIM.env, SIM.reward)
    arrays = collect(env, [AlwaysSell()], epsilon=0.0, seed=0)
    assert (arrays["requested"] == Action.SELL).all() and (arrays["actions"] == Action.WAIT).all()


def test_collection_covers_every_policy_and_market(data):
    env = PolymarketEnv(data, SIM.env, SIM.reward)
    arrays = collect(env, [FavoritePolicy(), NoTradePolicy()], epsilon=0.3, seed=1)
    assert len(arrays["actions"]) == 2 * len(data) * 60 and arrays["terminals"].sum() == 12
    assert arrays["observations"].shape == (2 * len(data) * 60, 16)
    # Con ε = 0,3, NoTrade también explora.
    assert set(np.unique(arrays["actions"])) > {Action.WAIT}
    same = collect(env, [FavoritePolicy(), NoTradePolicy()], epsilon=0.3, seed=1)
    assert np.array_equal(arrays["actions"], same["actions"])


def test_offline_dataset_is_saved_with_its_manifest(data, tmp_path):
    config = experiment("cql")
    path = offline_path(tmp_path, "sintetico", config.offline, config.reward)
    manifest = build_offline_dataset(config, data, path)
    assert manifest["transitions"] == 3 * len(data) * 60 and manifest["episodes"] == 18
    assert json.loads(path.with_suffix(".json").read_text())["sha256"] == manifest["sha256"]
    assert load_offline_dataset(path).transition_count == manifest["transitions"]
    other = offline_path(
        tmp_path, "sintetico", config.offline.model_copy(update={"epsilon": 0.1}), config.reward
    )
    assert other != path
    mid = config.reward.model_copy(update={"name": "pnl_mid"})
    assert offline_path(tmp_path, "sintetico", config.offline, mid) != path


def test_unknown_baselines_and_missing_offline_section_are_errors(data, tmp_path):
    config = experiment("cql", policies=["no_existe"])
    with pytest.raises(ValueError, match="desconocidos"):
        build_offline_dataset(config, data, tmp_path / "x.h5")
    with pytest.raises(ValidationError, match="offline"):
        ExperimentConfig(**(experiment("cql").model_dump() | {"offline": None}))


@pytest.mark.parametrize("algo", ["cql", "bc"])
def test_train_offline_keeps_the_best_checkpoint(data, algo, tmp_path):
    config = experiment(algo)
    path = offline_path(tmp_path, "sintetico", config.offline, config.reward)
    build_offline_dataset(config, data, path)

    metrics = train_offline(config, 0, path, data, tmp_path / algo)

    run = tmp_path / algo
    assert {"best.d3", "metrics.json", "config.yaml"} <= {p.name for p in run.iterdir()}
    assert len(metrics["checkpoints"]) == 2
    assert metrics["best"]["mean_return"] == max(c["mean_return"] for c in metrics["checkpoints"])
    policy = D3rlpyPolicy.load(run / "best.d3")
    obs, _ = PolymarketEnv(data, SIM.env, SIM.reward).reset(seed=0)
    assert policy.act(obs) in set(Action)


def test_cli_collects_then_trains_cql(tmp_path, capsys, monkeypatch):
    from polym4v import cli

    markets, prices, spot = synthetic_frames(4)
    steps = add_features(align(markets, prices, spot, step_s=60, n_steps=60), 3600)
    for name, frame in (("markets", markets), ("steps", steps), ("prices_raw", prices)):
        frame.to_parquet(tmp_path / f"{name}.parquet")
    (tmp_path / "normalization.json").write_text(json.dumps({"features": fit_zscore(steps)}))
    (tmp_path / "manifest.json").write_text(json.dumps({"config": {"step_seconds": 60}}))
    (tmp_path / "cql.yaml").write_text(yaml.safe_dump(experiment("cql").model_dump(mode="json")))
    monkeypatch.setenv("POLYM4V_DATA_DIR", str(tmp_path / "datos"))
    args = ["--config", str(tmp_path / "cql.yaml"), "--dataset", str(tmp_path)]

    assert cli.main(["train", *args]) == 1
    assert "collect-offline" in capsys.readouterr().err

    assert cli.main(["collect-offline", *args]) == 0
    assert json.loads(capsys.readouterr().out)["transitions"] == 3 * 4 * 60
    assert cli.main(["train", *args, "--out", str(tmp_path / "models")]) == 0
    assert json.loads(capsys.readouterr().out)["runs"][0]["seed"] == 0
