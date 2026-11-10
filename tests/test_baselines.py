import numpy as np
import pytest

from polym4v.agents.base import Action, Policy
from polym4v.agents.baselines import (
    FairValuePolicy,
    FavoritePolicy,
    MeanReversionPolicy,
    MomentumPolicy,
    NoTradePolicy,
    RandomPolicy,
    baselines,
)
from polym4v.env.market_env import PolymarketEnv
from polym4v.env.synthetic import synthetic_data
from polym4v.features.market import MARKET_FEATURES
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


def obs(k=10, side=0, upnl=0.0, **features):
    """Observación sintética: features de mercado neutras, salvo las que se pasan."""
    values = dict.fromkeys(MARKET_FEATURES, 0.0) | {"p_yes": 0.5, "tau": (60 - k) / 60}
    values |= features
    market = [values[name] for name in MARKET_FEATURES]
    return np.array([*market, side, 0.5 if side else 0.0, upnl], dtype=np.float32)


def test_every_baseline_follows_the_policy_protocol():
    for name, make in baselines(COSTS).items():
        policy = make()
        assert isinstance(policy, Policy) and policy.name == name


def test_no_trade_always_waits():
    policy = NoTradePolicy()
    assert {policy.act(obs(k=k, p_yes=p)) for k in range(60) for p in (0.1, 0.9)} == {0}


def test_random_is_reproducible_and_uses_every_action():
    first, second = RandomPolicy(seed=1), RandomPolicy(seed=1)
    seq = [first.act(obs()) for _ in range(200)]
    assert seq == [second.act(obs()) for _ in range(200)] and set(seq) == set(Action)


def test_favorite_buys_the_favorite_only_at_its_step():
    policy = FavoritePolicy(entry_k=30)
    assert policy.act(obs(k=30, p_yes=0.7)) == Action.BUY_YES
    assert policy.act(obs(k=30, p_yes=0.3)) == Action.BUY_NO
    assert policy.act(obs(k=29, p_yes=0.7)) == Action.WAIT
    assert policy.act(obs(k=30, p_yes=0.7, side=1)) == Action.WAIT


def test_momentum_follows_and_mean_reversion_fades_the_move():
    up = obs(dp_5=2.0)
    assert MomentumPolicy().act(up) == Action.BUY_YES
    assert MeanReversionPolicy().act(up) == Action.BUY_NO
    assert MomentumPolicy().act(obs(dp_5=0.5)) == Action.WAIT


@pytest.mark.parametrize(
    ("upnl", "expected"), [(0.25, Action.SELL), (-0.25, Action.SELL), (0.05, Action.WAIT)]
)
def test_momentum_exits_at_its_thresholds(upnl, expected):
    assert MomentumPolicy().act(obs(side=1, upnl=upnl)) == expected


def test_fair_value_buys_only_when_the_edge_beats_the_costs():
    policy = FairValuePolicy(COSTS)
    # Con p = 0,5, comprar cuesta 0,01 de medio spread y unos 0,0175 de comisión por acción.
    assert policy.act(obs(p_yes=0.5, edge_tp=0.05)) == Action.BUY_YES
    assert policy.act(obs(p_yes=0.5, edge_tp=-0.05)) == Action.BUY_NO
    assert policy.act(obs(p_yes=0.5, edge_tp=0.02)) == Action.WAIT
    # Usa la ventaja en el instante del precio, no la que mezcla spot fresco y precio viejo.
    assert policy.act(obs(p_yes=0.5, edge=0.3, edge_tp=0.0)) == Action.WAIT


def test_fair_value_wins_the_positive_control_and_no_trade_keeps_the_cash():
    """Con el precio atrasado 2 minutos, FairValue gana; NoTrade termina igual que empezó."""
    data = synthetic_data(300, lag_s=120, seed=4)
    env = PolymarketEnv(data, ENV, RewardConfig(name="pnl"))
    results = {}
    for policy in (FairValuePolicy(COSTS), NoTradePolicy()):
        pnl = []
        for market_id in data.market_ids:
            policy.reset()
            observation, info = env.reset(options={"market_id": market_id})
            done = False
            while not done:
                observation, _, done, _, info = env.step(policy.act(observation, info))
            pnl.append(info["portfolio_value"] - 1000.0)
        results[policy.name] = np.array(pnl)
    assert results["fair_value"].mean() > 0
    assert (results["no_trade"] == 0).all()
