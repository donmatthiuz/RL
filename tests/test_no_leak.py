"""Tests de no-fuga del simulador (ENV-10, ADR-013 y sección 4.4 de docs/09)."""

import numpy as np
import pytest

from polym4v.agents.base import Action
from polym4v.data.steps import align
from polym4v.env.market_data import MarketData
from polym4v.env.market_env import PolymarketEnv
from polym4v.env.synthetic import synthetic_data, synthetic_frames
from polym4v.features.market import MARKET_FEATURES, add_features
from polym4v.utils.config import CostConfig, EnvConfig, RewardConfig

NO_COSTS = CostConfig(
    half_spread=0.0, fee_rate=0.0, fee_exponent=1, fee_decimals=5, min_fee=0.00001, tick=0.001
)
ENV = EnvConfig(
    initial_cash=1000.0,
    stake_fraction=0.02,
    latency_s=2,
    tolerance_s=60,
    no_open_last_minutes=2,
    costs=NO_COSTS,
)
PNL = RewardConfig(name="pnl")
EDGE = MARKET_FEATURES.index("edge")


def follow_edge(env, market_id, threshold=0.03):
    """Compra el lado que `edge` marca como barato y mantiene hasta la resolución."""
    obs, _ = env.reset(options={"market_id": market_id})
    done = False
    while not done:
        action = Action.WAIT
        if obs[-3] == 0 and obs[EDGE] > threshold:
            action = Action.BUY_YES
        elif obs[-3] == 0 and obs[EDGE] < -threshold:
            action = Action.BUY_NO
        obs, _, done, _, info = env.step(action)
    return info["portfolio_value"] - 1000.0


def t_stat(pnl):
    pnl = np.asarray(pnl)
    return pnl.mean() / (pnl.std(ddof=1) / np.sqrt(len(pnl)))


@pytest.fixture(scope="module")
def null_market():
    return synthetic_data(800, lag_s=0, seed=11)


def test_null_market_gives_no_significant_gain(null_market):
    """Precio = valor justo: seguir `edge` no gana sin costos (el atraso no se explota)."""
    env = PolymarketEnv(null_market, ENV, PNL)
    pnl = [follow_edge(env, market_id) for market_id in null_market.market_ids]
    assert t_stat(pnl) < 2.0


def test_random_policy_gains_nothing_in_the_null_market(null_market):
    env = PolymarketEnv(null_market, ENV, PNL)
    rng = np.random.default_rng(0)
    pnl = []
    for market_id in null_market.market_ids:
        env.reset(options={"market_id": market_id})
        done = False
        while not done:
            _, _, done, _, info = env.step(rng.integers(4))
        pnl.append(info["portfolio_value"] - 1000.0)
    assert abs(t_stat(pnl)) < 2.0


def test_with_costs_following_edge_loses_in_the_null_market(null_market):
    costs = NO_COSTS.model_copy(update={"half_spread": 0.01, "fee_rate": 0.07})
    env = PolymarketEnv(null_market, ENV.model_copy(update={"costs": costs}), PNL)
    free = PolymarketEnv(null_market, ENV, PNL)
    paid = [follow_edge(env, m) for m in null_market.market_ids]
    unpaid = [follow_edge(free, m) for m in null_market.market_ids]
    assert np.mean(paid) < np.mean(unpaid) and np.mean(paid) < 0


def test_positive_control_detects_a_real_delay():
    """Con un precio atrasado 2 minutos, la misma regla sí gana: el test tiene potencia."""
    data = synthetic_data(800, lag_s=120, seed=11)
    env = PolymarketEnv(data, ENV, PNL)
    pnl = [follow_edge(env, market_id) for market_id in data.market_ids]
    assert t_stat(pnl) > 2.0


def test_changing_the_future_does_not_change_past_observations():
    """Alterar precios, spot y resultado posteriores a `t` no cambia las observaciones hasta `t`."""
    markets, prices, spot = synthetic_frames(3, seed=5)
    cut = int(markets.loc[1, "w0"]) + 60 * 25

    def episode_observations(markets, prices, spot):
        steps = add_features(align(markets, prices, spot, step_s=60, n_steps=60), 3600)
        env = PolymarketEnv(MarketData.from_frames(markets, steps, prices), ENV, PNL)
        obs, _ = env.reset(options={"market_id": markets.loc[1, "market_id"]})
        observations, done, k = [obs], False, 0
        while not done:
            action = Action.BUY_YES if k == 10 else Action.SELL if k == 20 else Action.WAIT
            obs, _, done, _, info = env.step(action)
            observations.append(obs)
            k += 1
        return np.array(observations)

    original = episode_observations(markets, prices, spot)
    later_prices, later_spot = prices["ts_available"] > cut, spot["ts_available"] > cut
    prices.loc[later_prices, "p"] = 1 - prices.loc[later_prices, "p"]
    spot.loc[later_spot, ["open", "high", "low", "close"]] *= 1.3
    markets["outcome"] = 1 - markets["outcome"]
    markets["spot_close"] *= 1.3
    altered = episode_observations(markets, prices, spot)

    known = 25 + 1  # la observación de reset y las de k = 1..25
    np.testing.assert_array_equal(original[:known], altered[:known])
    assert not np.array_equal(original[known:], altered[known:])


def test_executions_never_reach_past_the_next_decision(null_market):
    """Una orden de `t` se ejecuta en `(t + latencia, t + 60]`, antes de la decisión siguiente."""
    env = PolymarketEnv(null_market, ENV, PNL)
    rng = np.random.default_rng(1)
    delays = []
    for market_id in null_market.market_ids[:200]:
        env.reset(options={"market_id": market_id})
        done = False
        while not done:
            _, _, done, _, info = env.step(rng.integers(4))
            if info["order_status"] == "ejecutada":
                delays.append(info["exec_ts"] - info["ts"])
    assert delays and min(delays) > 2 and max(delays) <= 60
