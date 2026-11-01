import math

import pandas as pd
import pytest

from polym4v.agents.baselines import FavoritePolicy, NoTradePolicy
from polym4v.env.market_env import PolymarketEnv
from polym4v.env.synthetic import synthetic_data
from polym4v.evaluation.backtest import run_backtest
from polym4v.evaluation.metrics import capital_curve, max_drawdown, spread_paid, summarize
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


def step(market, k, status="ninguna", executed=0, side=0, final=1000.0, done=False, **fill):
    return {
        "policy": "a_mano",
        "market_id": market,
        "k": k,
        "order_status": status,
        "action_executed": executed,
        "position_side": side,
        "exec_p": fill.get("exec_p"),
        "exec_verified": fill.get("verified"),
        "fill_price": fill.get("price"),
        "fill_shares": fill.get("shares"),
        "portfolio_value": final,
        "fees_paid": fill.get("fees", 0.0),
        "done": done,
    }


def trajectories():
    """Tres mercados: gana 10 USDC, pierde 20 y no opera."""
    return pd.DataFrame(
        [
            # m1: compra YES a 0,51 con el precio en 0,50 y vende a 0,59 con el precio en 0,60.
            step("m1", 0, "ejecutada", 1, 1, exec_p=0.50, price=0.51, shares=30.0, verified=True),
            step("m1", 1, "ejecutada", 3, 0, exec_p=0.60, price=0.59, shares=30.0, verified=False),
            step("m1", 2, final=1010.0, done=True, fees=0.5),
            # m2: compra NO a 0,31 con el precio YES en 0,70 y pierde todo.
            step("m2", 0, "ejecutada", 2, -1, exec_p=0.70, price=0.31, shares=60.0, verified=True),
            step("m2", 1, "invalida", 0, -1),
            step("m2", 2, final=980.0, done=True, fees=0.3),
            # m3: una orden sin precio y nada más.
            step("m3", 0, "sin_precio"),
            step("m3", 1),
            step("m3", 2, done=True),
        ]
    )


def test_max_drawdown_of_hand_made_curves():
    assert max_drawdown(pd.Series([10.0, -10.0, 5.0, -20.0])) == 30.0
    assert max_drawdown(pd.Series([5.0, 8.0, 12.0])) == 0.0
    # Si la primera caída ya pierde, cuenta desde el 0 inicial.
    assert max_drawdown(pd.Series([-4.0, -1.0])) == 4.0
    assert capital_curve(pd.Series([10.0, -30.0, 0.0])).tolist() == [10.0, -20.0, -20.0]


def test_spread_paid_by_hand():
    # m1: 30 × 0,01 al comprar y 30 × 0,01 al vender; m2: 60 × 0,01 al comprar NO a 0,30 + 0,01.
    assert spread_paid(trajectories()) == pytest.approx(0.3 + 0.3 + 0.6)


def test_summary_of_hand_made_markets():
    summary = summarize(trajectories(), initial_cash=1000.0, stake=20.0)
    # R = 10/20, -20/20 y 0.
    assert summary["mean_return"] == pytest.approx((0.5 - 1.0 + 0.0) / 3)
    assert summary["total_pnl"] == pytest.approx(-10.0)
    assert summary["max_drawdown"] == pytest.approx(20.0)
    assert summary["win_rate"] == pytest.approx(0.5)
    assert summary["no_trade_share"] == pytest.approx(1 / 3)
    assert summary["trades_per_market"] == pytest.approx(1.0)
    assert summary["fees_paid"] == pytest.approx(0.8)
    assert summary["invalid_share"] == pytest.approx(1 / 9)
    assert summary["no_price_share"] == pytest.approx(1 / 4)
    assert summary["verified_share"] == pytest.approx(2 / 3)
    r = pd.Series([0.5, -1.0, 0.0])
    assert summary["sharpe"] == pytest.approx(r.mean() / r.std())


def test_no_trade_has_zero_return_and_undefined_ratios():
    env = PolymarketEnv(synthetic_data(5, seed=8), ENV, RewardConfig(name="pnl"))
    summary = summarize(run_backtest(NoTradePolicy(), env), 1000.0, 20.0)
    assert summary["mean_return"] == 0 and summary["max_drawdown"] == 0
    assert math.isnan(summary["sharpe"]) and math.isnan(summary["win_rate"])
    assert summary["no_trade_share"] == 1 and math.isnan(summary["verified_share"])


def test_summary_matches_the_backtest():
    env = PolymarketEnv(synthetic_data(8, seed=9), ENV, RewardConfig(name="pnl"))
    trajectories = run_backtest(FavoritePolicy(), env)
    summary = summarize(trajectories, 1000.0, 20.0)
    finals = trajectories.loc[trajectories["done"], "portfolio_value"]
    assert summary["total_pnl"] == pytest.approx((finals - 1000.0).sum())
    # Favorite compra una sola vez y mantiene: paga medio spread por acción una vez.
    bought = trajectories[trajectories["order_status"] == "ejecutada"]
    assert summary["spread_paid"] == pytest.approx((bought["fill_shares"] * 0.01).sum())
