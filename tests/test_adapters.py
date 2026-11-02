"""Adaptadores de SB3 y d3rlpy (AGT-02): acciones válidas con observaciones del entorno."""

import numpy as np
import pytest

from polym4v.agents.adapters import D3rlpyPolicy, SB3Policy
from polym4v.agents.base import Action, Policy
from polym4v.env.market_env import PolymarketEnv
from polym4v.env.synthetic import synthetic_data
from polym4v.utils.config import CostConfig, EnvConfig, RewardConfig

COSTS = CostConfig(
    half_spread=0.01, fee_rate=0.07, fee_exponent=1, fee_decimals=5, min_fee=0.00001, tick=0.001
)
ENV = EnvConfig(
    initial_cash=1000.0,
    stake_fraction=0.02,
    latency_s=2,
    tolerance_s=60,
    no_open_last_minutes=2,
    costs=COSTS,
)


@pytest.fixture(scope="module")
def env():
    return PolymarketEnv(synthetic_data(4, seed=12), ENV, RewardConfig(name="pnl"))


def observations(env, n_markets=2):
    """Observaciones reales del entorno, recorriendo mercados con WAIT."""
    out = []
    for market_id in env.data.market_ids[:n_markets]:
        obs, _ = env.reset(options={"market_id": market_id})
        out.append(obs)
        done = False
        while not done:
            obs, _, done, _, _ = env.step(Action.WAIT)
            out.append(obs)
    return np.array(out)


def plays_a_full_episode(policy, env):
    obs, info = env.reset(options={"market_id": env.data.market_ids[0]})
    policy.reset()
    done, steps = False, 0
    while not done:
        action = policy.act(obs, info)
        assert action in set(Action)
        obs, _, done, _, info = env.step(action)
        steps += 1
    return steps == env.data.n_steps


@pytest.mark.parametrize("algo", ["ppo", "dqn"])
def test_sb3_adapter_returns_valid_actions_and_survives_save_and_load(env, algo, tmp_path):
    from stable_baselines3 import DQN, PPO

    model_class = {"ppo": PPO, "dqn": DQN}[algo]
    model = model_class("MlpPolicy", env, seed=0, device="cpu")
    policy = SB3Policy(model, algo)
    assert isinstance(policy, Policy) and plays_a_full_episode(policy, env)

    model.save(tmp_path / algo)
    loaded = SB3Policy.load(tmp_path / f"{algo}.zip", algo)
    obs = observations(env)
    assert [policy.act(o) for o in obs] == [loaded.act(o) for o in obs]


def test_sb3_rejects_unknown_algorithms(tmp_path):
    with pytest.raises(ValueError, match="desconocido"):
        SB3Policy.load(tmp_path / "x.zip", "a2c")


@pytest.mark.parametrize("config", ["DiscreteCQLConfig", "DiscreteBCConfig"])
def test_d3rlpy_adapter_returns_valid_actions_and_survives_save_and_load(env, config, tmp_path):
    import d3rlpy

    algo = getattr(d3rlpy.algos, config)().create(device=False)
    algo.build_with_env(env)
    policy = D3rlpyPolicy(algo, config)
    assert isinstance(policy, Policy) and plays_a_full_episode(policy, env)

    algo.save(tmp_path / "modelo.d3")
    loaded = D3rlpyPolicy.load(tmp_path / "modelo.d3")
    obs = observations(env)
    assert [policy.act(o) for o in obs] == [loaded.act(o) for o in obs]
