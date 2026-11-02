import json

import pandas as pd
import pytest

from polym4v.agents.baselines import FavoritePolicy, NoTradePolicy, RandomPolicy
from polym4v.data.steps import align
from polym4v.env.market_env import INFO_KEYS, PolymarketEnv
from polym4v.env.synthetic import synthetic_data, synthetic_frames
from polym4v.evaluation.backtest import episode_results, run_backtest
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


@pytest.fixture(scope="module")
def env():
    return PolymarketEnv(synthetic_data(15, seed=2), ENV, RewardConfig(name="pnl"))


def test_no_trade_ends_every_market_with_the_initial_cash(env):
    """Criterio de EVA-02."""
    trajectories = run_backtest(NoTradePolicy(), env)
    results = episode_results(trajectories, 1000.0, 20.0)
    assert len(results) == 15 and (results["final_value"] == 1000.0).all()
    assert (results["return_on_stake"] == 0).all()


def test_trajectories_have_every_info_key_and_one_row_per_step(env):
    trajectories = run_backtest(RandomPolicy(seed=0), env)
    expected = {key for key in INFO_KEYS if key != "reward_components"}
    assert expected <= set(trajectories.columns) and {"r_pnl", "r_hold", "reward", "done"} <= set(
        trajectories.columns
    )
    assert len(trajectories) == 15 * 60 and trajectories["done"].sum() == 15
    assert list(trajectories["market_id"].drop_duplicates()) == env.data.market_ids


def test_markets_run_in_the_given_order_once(env):
    chosen = env.data.market_ids[3:6][::-1]
    trajectories = run_backtest(NoTradePolicy(), env, chosen)
    assert list(trajectories["market_id"].drop_duplicates()) == chosen


def test_results_match_the_trajectories(env):
    trajectories = run_backtest(FavoritePolicy(), env)
    results = episode_results(trajectories, 1000.0, 20.0)
    for market_id, row in results.iterrows():
        steps = trajectories[trajectories["market_id"] == market_id]
        assert row["final_value"] == steps["portfolio_value"].iloc[-1]
        assert row["executed"] == (steps["order_status"] == "ejecutada").sum()
        assert row["return_on_stake"] == pytest.approx(steps["r_pnl"].sum() * 1000.0 / 20.0)


def test_cli_backtest_writes_trajectories_and_refuses_test(tmp_path, capsys, monkeypatch):
    from polym4v import cli

    markets, prices, spot = synthetic_frames(4)
    steps = add_features(align(markets, prices, spot, step_s=60, n_steps=60), 3600)
    for name, frame in (("markets", markets), ("steps", steps), ("prices_raw", prices)):
        frame.to_parquet(tmp_path / f"{name}.parquet")
    (tmp_path / "normalization.json").write_text(json.dumps({"features": fit_zscore(steps)}))
    (tmp_path / "manifest.json").write_text(json.dumps({"config": {"step_seconds": 60}}))
    monkeypatch.setenv("POLYM4V_REPORTS_DIR", str(tmp_path / "reports"))
    args = ["backtest", "--policy", "favorite", "--dataset", str(tmp_path)]

    assert cli.main(args) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["markets"] == 4 and summary["split"] == "train"
    assert summary["verified_share"] is None
    assert len(pd.read_parquet(summary["trajectories"])) == 4 * 60

    assert cli.main([*args, "--split", "test"]) == 1
    assert "una sola vez" in capsys.readouterr().err
