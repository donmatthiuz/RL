import json

import numpy as np
import pandas as pd
import pytest
from gymnasium.utils.env_checker import check_env

from polym4v.agents.base import Action
from polym4v.data.steps import align
from polym4v.env.execution import buy, sell
from polym4v.env.market_data import MarketData
from polym4v.env.market_env import INFO_KEYS, PolymarketEnv
from polym4v.env.portfolio import FLAT, NO, YES, Portfolio
from polym4v.env.reward import RewardState, reward
from polym4v.env.synthetic import synthetic_data, synthetic_frames
from polym4v.features.market import add_features, fit_zscore
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
PNL = RewardConfig(name="pnl")


@pytest.fixture(scope="module")
def data():
    return synthetic_data(20, seed=3)


def make_env(data, config=ENV, reward_config=PNL):
    return PolymarketEnv(data, config, reward_config)


def run(env, actions, market_id):
    """Corre un episodio con una acción por paso (WAIT al acabarse la lista)."""
    env.reset(options={"market_id": market_id})
    infos, rewards, done, k = [], [], False, 0
    while not done:
        action = actions[k] if k < len(actions) else Action.WAIT
        _, r, done, _, info = env.step(action)
        infos.append(info)
        rewards.append(r)
        k += 1
    return infos, rewards


# --- Portfolio (ENV-02) ---


def test_portfolio_buy_hold_and_settle_by_hand():
    portfolio = Portfolio(cash=1000.0)
    fill = buy(20.0, 0.5, COSTS)
    portfolio.open(YES, fill)
    # Compra a 0,51 con la comisión incluida en los 20 USDC.
    assert fill.price == pytest.approx(0.51)
    assert portfolio.cash == pytest.approx(980.0) and portfolio.cost == pytest.approx(20.0)
    # Valor de liquidación con p = 0,5: vender a 0,49 menos la comisión de venta (S9).
    expected = fill.shares * 0.49 - round(fill.shares * 0.07 * 0.49 * 0.51, 5)
    assert portfolio.liquidation_value(0.5, COSTS) == pytest.approx(expected)
    assert portfolio.settle(1) == pytest.approx(fill.shares - 20.0)
    assert portfolio.cash == pytest.approx(980.0 + fill.shares) and portfolio.side == FLAT


def test_portfolio_no_side_uses_one_minus_p_yes():
    portfolio = Portfolio(cash=1000.0)
    portfolio.open(NO, buy(20.0, 0.3, COSTS))
    assert portfolio.entry_price == pytest.approx(0.31)
    worth_yes_02 = portfolio.liquidation_value(0.2, COSTS)
    assert worth_yes_02 > portfolio.liquidation_value(0.7, COSTS)
    assert portfolio.settle(1) == pytest.approx(-20.0) and portfolio.cash == pytest.approx(980.0)


def test_portfolio_round_trip_loses_spread_and_both_fees():
    portfolio = Portfolio(cash=1000.0)
    opened = buy(20.0, 0.5, COSTS)
    portfolio.open(YES, opened)
    closed = sell(portfolio.shares, 0.5, COSTS)
    pnl = portfolio.close(closed)
    assert pnl == pytest.approx(-(opened.shares * 0.02 + opened.fee + closed.fee))
    assert portfolio.fees_paid == pytest.approx(opened.fee + closed.fee)


def test_portfolio_rejects_impossible_operations():
    portfolio = Portfolio(cash=10.0)
    with pytest.raises(ValueError, match="no hay posición"):
        portfolio.close(sell(1.0, 0.5, COSTS))
    with pytest.raises(ValueError, match="saldo"):
        portfolio.open(YES, buy(20.0, 0.5, COSTS))
    portfolio.open(YES, buy(5.0, 0.5, COSTS))
    with pytest.raises(ValueError, match="ya hay"):
        portfolio.open(NO, buy(1.0, 0.5, COSTS))


# --- Recompensa (ENV-05) ---


@pytest.mark.parametrize("seed", range(5))
def test_pnl_rewards_add_up_to_the_final_pnl(data, seed):
    """Criterio de ENV-05: con pnl, la suma del episodio es el PnL final sobre V_0."""
    env = make_env(data)
    env.reset(seed=seed)
    rng, total, done = np.random.default_rng(seed), 0.0, False
    while not done:
        _, r, done, _, info = env.step(rng.integers(4))
        total += r
    assert total == pytest.approx((info["portfolio_value"] - 1000.0) / 1000.0)
    assert info["portfolio_value"] == pytest.approx(info["cash"])


def test_drawdown_is_penalized_only_when_it_grows():
    config = RewardConfig(name="pnl_risk", lambda_dd=0.5)
    state = RewardState(v0=100.0, peak=100.0)
    r1, c1 = reward(config, state, v_prev=100.0, v_now=90.0, invalid=False, done=False)
    r2, c2 = reward(config, state, v_prev=90.0, v_now=95.0, invalid=False, done=False)
    assert c1["drawdown"] == pytest.approx(-0.05) and r1 == pytest.approx(-0.15)
    assert c2["drawdown"] == 0.0 and r2 == pytest.approx(0.05)


def test_terminal_reward_only_at_the_end_and_invalid_penalty():
    config = RewardConfig(name="terminal", lambda_invalid=0.01)
    state = RewardState(v0=100.0, peak=100.0)
    r1, _ = reward(config, state, v_prev=100.0, v_now=90.0, invalid=True, done=False)
    r2, _ = reward(config, state, v_prev=90.0, v_now=110.0, invalid=False, done=True)
    assert r1 == pytest.approx(-0.01) and r2 == pytest.approx(0.1)


# --- Entorno (ENV-04) ---


def test_passes_the_gymnasium_checker(data):
    check_env(make_env(data), skip_render_check=True)


def test_order_fills_at_first_price_after_latency(data):
    env = make_env(data)
    episode = data.episodes[0]
    infos, _ = run(env, [Action.WAIT] * 10 + [Action.BUY_YES], episode.market_id)
    info = infos[10]
    t = episode.ts[10]
    later = episode.price_ts > t + 2
    assert info["order_status"] == "ejecutada" and info["action_executed"] == Action.BUY_YES
    assert info["exec_ts"] == episode.price_ts[later][0] <= t + 60
    assert info["exec_p"] == episode.price_p[later][0]
    assert info["fill_price"] == pytest.approx(min(info["exec_p"] + 0.01, 0.999))
    assert info["position_side"] == YES and info["position_size"] == info["fill_shares"]


def test_order_without_price_in_the_window_is_cancelled(data):
    env = make_env(data)
    episode = data.episodes[0]
    gap = data.episodes[0].price_ts.copy()
    # Sin ningún precio después del minuto 10, la orden no encuentra precio.
    cut = episode.ts[10] + 2
    object.__setattr__(episode, "price_ts", gap[gap <= cut])
    try:
        infos, _ = run(env, [Action.WAIT] * 10 + [Action.BUY_NO], episode.market_id)
    finally:
        object.__setattr__(episode, "price_ts", gap)
    assert infos[10]["order_status"] == "sin_precio" and infos[10]["action_executed"] == 0
    assert infos[10]["position_side"] == FLAT


def test_invalid_actions_run_as_wait(data):
    env = make_env(data)
    actions = [Action.SELL, Action.BUY_YES, Action.BUY_NO]
    infos, _ = run(env, actions, data.episodes[1].market_id)
    assert infos[0]["order_status"] == "invalida" and infos[0]["action_valid"] is False
    assert infos[1]["order_status"] == "ejecutada"
    # BUY con una posición abierta (S6): se pide BUY_NO y se ejecuta WAIT.
    assert infos[2]["action"] == Action.BUY_NO and infos[2]["action_executed"] == Action.WAIT


def test_no_new_positions_in_the_last_two_minutes(data):
    env = make_env(data)
    env.reset(options={"market_id": data.episodes[2].market_id})
    for _ in range(57):
        env.step(Action.WAIT)
    assert env.action_masks().tolist() == [True, True, True, False]
    env.step(Action.WAIT)
    assert env.action_masks().tolist() == [True, False, False, False]
    _, _, _, _, info = env.step(Action.BUY_YES)
    assert info["order_status"] == "invalida"


def test_sell_is_allowed_until_the_end(data):
    env = make_env(data)
    infos, _ = run(env, [Action.BUY_YES] + [Action.WAIT] * 58 + [Action.SELL], data.market_ids[0])
    assert infos[59]["action_valid"] is True


def test_open_position_is_settled_at_one_or_zero(data):
    env = make_env(data)
    for episode in data.episodes[:6]:
        infos, _ = run(env, [Action.BUY_YES], episode.market_id)
        shares, last = infos[0]["fill_shares"], infos[-1]
        expected = 1000.0 - 20.0 + (shares if episode.outcome == 1 else 0.0)
        assert last["portfolio_value"] == pytest.approx(expected)
        assert last["position_side"] == FLAT


def test_no_trade_ends_with_the_initial_cash(data):
    env = make_env(data)
    for episode in data.episodes:
        infos, rewards = run(env, [], episode.market_id)
        assert infos[-1]["portfolio_value"] == 1000.0 and sum(rewards) == 0.0


def test_info_has_the_agreed_keys(data):
    env = make_env(data)
    _, info = env.reset(seed=0)
    assert tuple(info) == INFO_KEYS and info["action"] is None
    _, _, _, _, info = env.step(Action.WAIT)
    assert tuple(info) == INFO_KEYS and info["reward_components"]["pnl"] == 0.0


def test_observation_carries_the_agent_state(data):
    env = make_env(data)
    env.reset(options={"market_id": data.episodes[0].market_id})
    obs, *_ = env.step(Action.BUY_NO)
    assert obs[-3] == NO and obs[-2] == pytest.approx(env.portfolio.entry_price)
    # PnL no realizado sobre el monto apostado, con la posición valorada a liquidación (S9).
    position = env.portfolio
    worth = position.liquidation_value(float(data.episodes[0].p_yes[1]), COSTS)
    assert obs[-1] == pytest.approx((worth - position.cost) / 20.0, rel=1e-5)


def test_same_seed_gives_the_same_markets(data):
    env = make_env(data)
    first = [env.reset(seed=s)[1]["market_id"] for s in range(5)]
    second = [env.reset(seed=s)[1]["market_id"] for s in range(5)]
    assert first == second and len(set(first)) > 1


def test_cannot_open_without_cash_for_the_rounded_fee(data):
    """Con toda la caja como monto, el redondeo de la comisión no alcanza: no se puede abrir."""
    env = make_env(data, ENV.model_copy(update={"stake_fraction": 1.0}))
    env.reset(options={"market_id": data.market_ids[0]})
    assert env.action_masks().tolist() == [True, False, False, False]


def test_tolerance_cannot_exceed_the_step(data):
    with pytest.raises(ValueError, match="paso de la grilla"):
        make_env(data, ENV.model_copy(update={"tolerance_s": 61}))


def test_load_reads_the_dataset_and_its_normalization(tmp_path):
    markets, prices, spot = synthetic_frames(4)
    markets.loc[3, "split"] = "val"
    steps = add_features(align(markets, prices, spot, step_s=60, n_steps=60), 3600)
    stats = fit_zscore(steps)
    markets.to_parquet(tmp_path / "markets.parquet")
    steps.to_parquet(tmp_path / "steps.parquet")
    prices.to_parquet(tmp_path / "prices_raw.parquet")
    (tmp_path / "normalization.json").write_text(json.dumps({"features": stats}))
    (tmp_path / "manifest.json").write_text(json.dumps({"config": {"step_seconds": 60}}))

    train = MarketData.load(tmp_path, split="train")
    raw = MarketData.load(tmp_path, split="val", normalize=False)

    assert len(train) == 3 and raw.market_ids == [markets.loc[3, "market_id"]]
    x = steps.loc[steps["market_id"] == markets.loc[0, "market_id"], "x"].to_numpy()
    column = list(pd.Index(["p_yes", "dp_1", "dp_5", "p_stale", "x"])).index("x")
    expected = (x - stats["x"]["mean"]) / stats["x"]["std"]
    assert train.episodes[0].features[:, column] == pytest.approx(expected, rel=1e-5)
