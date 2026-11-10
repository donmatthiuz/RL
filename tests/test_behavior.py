import json

import numpy as np
import pandas as pd
import pytest

from polym4v import cli
from polym4v.agents.base import Action
from polym4v.agents.baselines import FavoritePolicy, MomentumPolicy, NoTradePolicy, RandomPolicy
from polym4v.env.market_env import PolymarketEnv
from polym4v.env.synthetic import synthetic_data
from polym4v.evaluation import behavior
from polym4v.evaluation.backtest import run_backtest
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
DATA = synthetic_data(8, seed=5)
OUTCOMES = {episode.market_id: episode.outcome for episode in DATA}


def backtest(policy):
    return run_backtest(policy, PolymarketEnv(DATA, ENV, RewardConfig(name="pnl")))


@pytest.fixture(scope="module")
def frames():
    return {
        "favorite": backtest(FavoritePolicy(entry_k=30)),
        "momentum": backtest(MomentumPolicy(threshold=0.5, take_profit=0.05, stop_loss=0.05)),
        "random": backtest(RandomPolicy(seed=2)),
        "no_trade": backtest(NoTradePolicy()),
    }


@pytest.mark.parametrize("name", ["favorite", "momentum", "random"])
def test_trades_add_up_to_the_total_pnl(frames, name):
    frame = frames[name]
    trades = behavior.trades(frame, OUTCOMES, ENV.initial_cash)
    executed = frame["order_status"].eq("ejecutada") & frame["action_executed"].isin([1, 2])
    total = frame.loc[frame["done"], "portfolio_value"].sum() - ENV.initial_cash * len(DATA)
    assert len(trades) == executed.sum() > 0
    assert trades["pnl"].sum() == pytest.approx(total)


def test_a_position_held_to_the_end_is_settled_with_its_outcome(frames):
    trades = behavior.trades(frames["favorite"], OUTCOMES, ENV.initial_cash)
    assert (trades["k"] == 30).all() and (trades["exit_k"] == 59).all()
    assert not trades["sold"].any() and trades["favorite"].all()
    won = trades["market_id"].map(OUTCOMES).eq(np.where(trades["side"] == "YES", 1, 0))
    assert (trades["side_won"] == won).all()
    # Ganar paga 1 por acción; perder, 0: el PnL tiene el signo del acierto.
    assert ((trades["pnl"] > 0) == trades["side_won"]).all()
    assert (trades["cost"] > trades["paid"]).all()


def test_sales_close_the_trade_before_the_end(frames):
    trades = behavior.trades(frames["momentum"], OUTCOMES, ENV.initial_cash)
    sold = trades[trades["sold"]]
    assert len(sold) > 0 and (sold["exit_k"] > sold["k"]).all()


def test_activity_and_payoff_tables(frames):
    groups = {"favorite": [frames["favorite"]], "momentum": [frames["momentum"]] * 2}
    by_policy = {
        name: behavior.policy_trades(seeds, OUTCOMES, ENV.initial_cash)
        for name, seeds in groups.items()
    }
    activity = behavior.activity_table(groups, by_policy).set_index("policy")
    assert activity.loc["momentum", "seeds"] == 2
    assert activity.loc["favorite", "trades_per_market"] == pytest.approx(
        len(by_policy["favorite"]) / len(DATA)
    )
    payoff = behavior.payoff_table(by_policy)
    favorite = payoff[payoff["policy"] == "favorite"]
    assert favorite["trades"].sum() == len(by_policy["favorite"])
    assert favorite["net"].sum() == pytest.approx(by_policy["favorite"]["pnl"].sum())
    assert (payoff["won_lower"] <= payoff["side_won"]).all()


def test_decision_map_only_counts_states_where_buying_is_possible(frames):
    table = behavior.decision_map([frames["favorite"]], ENV.no_open_last_minutes)
    assert list(table.columns)[-1] == "55-57"
    assert table.drop(columns="30-39").fillna(0).eq(0).all().all()
    assert table["30-39"].max() > 0 and table.max().max() <= 1


def test_wilson_interval():
    assert behavior.wilson(5, 10) == pytest.approx((0.2366, 0.7634), abs=1e-4)
    assert behavior.wilson(0, 10)[0] == 0 and behavior.wilson(10, 10)[1] == 1
    lower, _ = behavior.wilson(907, 907)
    assert 0.995 < lower < 0.9999


def test_cost_per_share_includes_spread_and_fee():
    # Con p = 0,995 el ask queda en el tope de 0,999; la comisión es 0,07 · 0,999 · 0,001.
    assert behavior.cost_per_share(0.995, COSTS) == pytest.approx(0.999 + 0.07 * 0.999 * 0.001)


def test_calibration_counts_one_market_per_row(frames):
    table = behavior.calibration_table(frames["no_trade"], OUTCOMES, COSTS)
    assert set(table["minute"]) <= set(behavior.CALIBRATION_MINUTES)
    for _, group in table.groupby("minute"):
        assert group["markets"].sum() <= len(DATA)
    assert table["edge"].to_numpy() == pytest.approx((table["won"] - table["cost"]).to_numpy())


def test_effective_turns_invalid_actions_into_wait():
    actions = np.array([Action.BUY_YES, Action.SELL, Action.BUY_NO, Action.SELL])
    flat = np.array([True, True, False, False])
    can_open = np.array([True, True, False, False])
    assert behavior.effective(actions, flat, can_open).tolist() == [1, 0, 0, 3]


def test_permutation_importance_finds_the_feature_the_policy_uses():
    rng = np.random.default_rng(0)
    states = rng.random((2000, len(MARKET_FEATURES) + 3)).astype(np.float32)
    states[:, behavior.POS_SIDE] = 0
    p_yes = MARKET_FEATURES.index("p_yes")

    def predict(obs):
        return np.where(obs[:, p_yes] > 0.7, Action.BUY_YES, Action.WAIT)

    table = behavior.permutation_importance(predict, states, np.ones(2000, bool)).set_index(
        "feature"
    )
    assert table.loc["p_yes", "changed"] > 0.5
    assert table.loc["precio de Polymarket", "changed"] > 0.5
    unused = [f for f in MARKET_FEATURES if f != "p_yes"] + ["spot de Binance", "tiempo restante"]
    assert (table.loc[unused, ["changed", "new_buys"]] == 0).all().all()


def test_collected_states_are_the_ones_the_backtest_saw(frames):
    env = PolymarketEnv(DATA, ENV, RewardConfig(name="pnl"))
    states, frame = behavior.collect_states(FavoritePolicy(entry_k=30), env)
    assert len(states) == len(frame) == len(frames["favorite"])
    pd.testing.assert_frame_equal(frame, frames["favorite"])
    can_open = behavior.can_open_mask(states, frame, ENV.no_open_last_minutes)
    assert not can_open[frame["k"].to_numpy() >= 58].any()


@pytest.fixture
def folder(tmp_path, frames):
    """Dos semillas de un "agente" y dos baselines, como los deja `evaluate` y `backtest`."""
    out = tmp_path / "trajectories"
    out.mkdir()
    for split in ("val", "test"):
        for seed, name in enumerate(["favorite", "momentum"]):
            frames[name].to_parquet(out / f"20261101-000000_ppo_pnl_s{seed}_{split}.parquet")
        frames["random"].to_parquet(out / f"random_{split}.parquet")
        frames["no_trade"].to_parquet(out / f"no_trade_{split}.parquet")
        frames["random"].to_parquet(out / f"random_{split}_estricto.parquet")
    return out


def test_build_behavior_writes_val_and_test(tmp_path, folder, frames):
    result = behavior.build_behavior("val", folder, tmp_path / "val", OUTCOMES, ENV)
    assert result["policies"] == ["ppo_pnl", "random"]
    for name in result["files"]:
        assert (tmp_path / "val" / name).stat().st_size > 0
    text = (tmp_path / "val" / "behavior.md").read_text(encoding="utf-8")
    assert sum(line.startswith("# ") for line in text.splitlines()) == 1
    assert "## Calibración del precio del favorito" in text and "behavior_map.png" in text

    steps = frames["no_trade"][["market_id", "k", "p_yes"]].assign(x=0.0)
    result = behavior.build_behavior("test", folder, tmp_path / "test", OUTCOMES, ENV, steps=steps)
    assert "inspection_losses.csv" in result["files"]
    losses = pd.read_csv(tmp_path / "test" / "inspection_losses.csv")
    assert (losses["price"] > behavior.SURE).all() and (losses["pnl"] < -1).all()
    text = (tmp_path / "test" / "inspection.md").read_text(encoding="utf-8")
    assert "Calibración" not in text and "comparison.md" in text


def test_cli_behavior_refuses_test_without_the_flag(tmp_path, folder, capsys):
    assert cli.main(["behavior", "--split", "test", "--trajectories", str(folder)]) == 1
    assert "--allow-test" in capsys.readouterr().err


def test_cli_behavior_on_val(tmp_path, folder, capsys, monkeypatch):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    markets = pd.DataFrame({"market_id": list(OUTCOMES), "outcome": list(OUTCOMES.values())})
    markets.to_parquet(dataset / "markets.parquet")
    args = ["behavior", "--split", "val", "--skip-importance", "--dataset", str(dataset)]
    args += ["--trajectories", str(folder), "--out", str(tmp_path / "out")]
    assert cli.main(args) == 0
    assert "behavior.md" in json.loads(capsys.readouterr().out)["files"]


def test_importance_summary_goes_into_the_val_report(tmp_path, folder):
    rng = np.random.default_rng(1)
    states = rng.random((500, len(MARKET_FEATURES) + 3)).astype(np.float32)
    states[:, behavior.POS_SIDE] = 0
    tau = MARKET_FEATURES.index("tau")

    def predict(obs):
        return np.where(obs[:, tau] < 0.3, Action.BUY_NO, Action.WAIT)

    can_open = np.ones(len(states), bool)
    seeds = [behavior.permutation_importance(predict, states, can_open, seed=s) for s in (0, 1)]
    summary = behavior.importance_summary({"ppo_pnl": seeds})
    row = summary.set_index("feature").loc["tiempo restante"]
    assert row["group"] and row["changed"] > 0.5 and row["changed_sd"] >= 0
    assert row["buys"] == 2 * seeds[0].set_index("feature").loc["tau", "buys"]

    result = behavior.build_behavior(
        "val", folder, tmp_path / "val", OUTCOMES, ENV, importance=(summary, 1.0)
    )
    assert {"behavior_importance.csv", "behavior_importance.png"} <= set(result["files"])
    text = (tmp_path / "val" / "behavior.md").read_text(encoding="utf-8")
    assert "| tiempo restante |" in text and "100.00%" in text


def test_agent_runs_finds_each_seed_of_each_agent(tmp_path, folder):
    models = tmp_path / "models"
    for seed in (0, 1):
        run = models / "final" / "ppo" / f"20261101-000000_ppo_pnl_s{seed}"
        run.mkdir(parents=True)
        (run / "config.yaml").write_text("{}")
    runs = behavior.agent_runs(folder, "val", models)
    assert list(runs) == ["ppo_pnl"] and [p.name[-2:] for p in runs["ppo_pnl"]] == ["s0", "s1"]
    with pytest.raises(FileNotFoundError, match="una sola corrida"):
        behavior.agent_runs(folder, "val", tmp_path / "vacio")
