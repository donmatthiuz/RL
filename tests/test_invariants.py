"""Invariantes del entorno con ejemplos generados (ENV-06, docs/05).

Cada ejemplo combina un mercado sintético, una config de costos y ejecución, y una secuencia de
acciones al azar. Pasan con 200 ejemplos o más.
"""

import math

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from polym4v.env.market_env import INFO_KEYS, PolymarketEnv
from polym4v.env.portfolio import FLAT
from polym4v.env.synthetic import synthetic_data
from polym4v.utils.config import CostConfig, EnvConfig, RewardConfig

DATA = synthetic_data(12, seed=21)
LAGGED = synthetic_data(12, lag_s=120, seed=22)

configs = st.builds(
    lambda half_spread, fee_rate, latency, stake, last: EnvConfig(
        initial_cash=1000.0,
        stake_fraction=stake,
        latency_s=latency,
        tolerance_s=60,
        no_open_last_minutes=last,
        costs=CostConfig(
            half_spread=half_spread,
            fee_rate=fee_rate,
            fee_exponent=1,
            fee_decimals=5,
            min_fee=0.00001,
            tick=0.001,
        ),
    ),
    st.sampled_from([0.0, 0.005, 0.01, 0.02, 0.05]),
    st.sampled_from([0.0, 0.07, 0.1]),
    st.integers(0, 30),
    st.floats(0.001, 1.0),
    st.integers(0, 5),
)
rewards = st.builds(
    RewardConfig,
    name=st.sampled_from(["pnl", "pnl_risk", "terminal"]),
    lambda_dd=st.floats(0, 1),
    lambda_invalid=st.floats(0, 0.1),
)
episodes = st.lists(st.integers(0, 3), min_size=60, max_size=60)


def play(config, reward_config, actions, market, data=DATA):
    env = PolymarketEnv(data, config, reward_config)
    obs, info = env.reset(options={"market_id": data.market_ids[market]})
    steps = [(obs, 0.0, info)]
    for action in actions:
        obs, r, done, truncated, info = env.step(action)
        steps.append((obs, r, info))
        if done:
            break
    return env, steps


@settings(max_examples=200, deadline=None)
@given(configs, rewards, episodes, st.integers(0, 11), st.booleans())
def test_money_is_conserved_and_never_negative(config, reward_config, actions, market, lagged):
    """La caja solo cambia por las operaciones y por la liquidación, y nunca es negativa."""
    data = LAGGED if lagged else DATA
    env, steps = play(config, reward_config, actions, market, data)
    cash, fees, shares, side = config.initial_cash, 0.0, 0.0, FLAT
    for _, _, info in steps[1:]:
        if info["order_status"] == "ejecutada":
            fees += info["fee"]
            if info["action_executed"] == 3:
                cash += info["fill_shares"] * info["fill_price"] - info["fee"]
                shares, side = 0.0, FLAT
            else:
                cash -= info["fill_shares"] * info["fill_price"] + info["fee"]
                shares, side = info["fill_shares"], info["position_side"]
        if info is steps[-1][2] and side != FLAT:
            # Liquidación: 1 por acción del lado ganador, sin comisión.
            won = (env.episode.outcome == 1) == (side == 1)
            cash += shares if won else 0.0
        assert info["cash"] >= -1e-9
        assert math.isclose(info["cash"], cash, abs_tol=1e-6)
    last = steps[-1][2]
    assert last["position_side"] == FLAT and last["portfolio_value"] == last["cash"]
    assert math.isclose(last["fees_paid"], fees, abs_tol=1e-9)


@settings(max_examples=200, deadline=None)
@given(configs, episodes, st.integers(0, 11))
def test_pnl_rewards_always_add_up_to_the_final_pnl(config, actions, market):
    _, steps = play(config, RewardConfig(name="pnl"), actions, market)
    total = sum(r for _, r, _ in steps)
    final = steps[-1][2]["portfolio_value"]
    assert math.isclose(total, (final - config.initial_cash) / config.initial_cash, abs_tol=1e-9)


@settings(max_examples=200, deadline=None)
@given(configs, rewards, episodes, st.integers(0, 11))
def test_states_and_observations_stay_valid(config, reward_config, actions, market):
    env, steps = play(config, reward_config, actions, market)
    for obs, r, info in steps:
        assert env.observation_space.contains(obs) and np.isfinite(obs).all()
        assert math.isfinite(r) and tuple(info) == INFO_KEYS
        side, size = info["position_side"], info["position_size"]
        assert side in (-1, 0, 1) and (size > 0) == (side != 0) and size >= 0
        assert info["action_executed"] in (None, 0, info["action"])
        if info["order_status"] == "ejecutada":
            assert 0 < info["fill_price"] < 1
            assert config.latency_s < info["exec_ts"] - info["ts"] <= config.tolerance_s
    assert len(steps) == 61
