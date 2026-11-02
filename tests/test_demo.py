"""Demo de Streamlit (EVA-07), con trayectorias de mercados sintéticos y sin red."""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from polym4v.agents.baselines import FavoritePolicy, RandomPolicy
from polym4v.env.market_env import PolymarketEnv
from polym4v.env.synthetic import synthetic_data
from polym4v.evaluation.backtest import run_backtest
from polym4v.utils.config import SimulatorConfig, load_config

APP = str(Path(__file__).parents[1] / "app" / "demo.py")


@pytest.fixture(scope="module")
def frames():
    config = load_config("configs/env.yaml", SimulatorConfig)
    env = PolymarketEnv(synthetic_data(3, seed=5), config.env, config.reward)
    return {policy.name: run_backtest(policy, env) for policy in (FavoritePolicy(), RandomPolicy())}


@pytest.fixture
def app(tmp_path, monkeypatch, frames):
    """La demo con dos archivos de train en la carpeta por defecto."""
    folder = tmp_path / "reports" / "trajectories"
    folder.mkdir(parents=True)
    for name, frame in frames.items():
        frame.to_parquet(folder / f"{name}_train.parquet")
    monkeypatch.setenv("POLYM4V_REPORTS_DIR", str(tmp_path / "reports"))
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception
    return at


def first_executed(frame):
    market = frame["market_id"].iloc[0]
    steps = frame[frame["market_id"] == market]
    return steps[steps["order_status"] == "ejecutada"].iloc[0]


def test_without_trajectories_it_explains_how_to_create_them(tmp_path, monkeypatch):
    monkeypatch.setenv("POLYM4V_REPORTS_DIR", str(tmp_path))
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception
    assert "make backtest" in at.info[0].value
    assert not at.slider


def test_lists_policies_and_markets_and_starts_at_the_first_step(app, frames):
    policy, market = app.sidebar.selectbox
    assert policy.options == ["favorite · train", "random · train"]
    assert len(market.options) == 3
    assert app.slider[0].value == 0 and app.slider[0].max == 59
    labels = [metric.label for metric in app.metric]
    assert labels == ["Caja", "Posición", "Valor", "Recompensa"]
    assert app.metric[0].value == "1000.00"


def test_buttons_move_one_step_and_stay_inside_the_market(app):
    app.button[1].click().run()
    app.button[1].click().run()
    assert app.slider[0].value == 2
    app.button[0].click().run()
    assert app.slider[0].value == 1
    app.slider[0].set_value(59).run()
    app.button[1].click().run()
    assert app.slider[0].value == 59


def test_changing_market_goes_back_to_the_first_step(app):
    app.slider[0].set_value(10).run()
    market = app.sidebar.selectbox[1]
    market.set_value(market.options[1]).run()
    assert app.slider[0].value == 0


def test_the_panel_shows_an_executed_order(app, frames):
    row = first_executed(frames["favorite"])
    app.slider[0].set_value(int(row["k"])).run()
    order = app.table[0].value["Valor"]
    assert order["Estado de la orden"] == "ejecutada"
    assert order["Acción ejecutada"] in ("BUY_YES", "BUY_NO")
    assert order["Acciones"] == f"{row['fill_shares']:.2f}"
    assert app.metric[0].value == f"{row['cash']:.2f}"


def test_playing_advances_until_the_last_step(app):
    app.slider[0].set_value(58).run()
    app.sidebar.toggle[0].set_value(True).run()
    assert not app.exception
    assert app.slider[0].value == 59


def test_without_a_report_nothing_is_compared_by_default(app):
    compare = app.sidebar.multiselect[0]
    assert compare.options == ["random · train"]
    assert compare.value == []
    assert not [title for title in app.subheader if title.value == "Comparación"]


def test_comparing_shows_both_policies_with_the_pnl_of_the_report(app, frames):
    app.sidebar.multiselect[0].select("random · train").run()
    assert not app.exception
    assert [title.value for title in app.subheader][-1] == "Comparación"
    table = app.table[-1].value
    assert list(table.index) == ["favorite · train", "random · train"]

    market = frames["random"]["market_id"].iloc[0]
    last = frames["random"][frames["random"]["market_id"] == market].iloc[-1]
    assert table.loc["random · train", "PnL en este mercado"] == (
        f"{last['portfolio_value'] - 1000.0:+.2f}"
    )


def test_cumulative_pnl_grows_with_the_chosen_market(app, frames):
    app.sidebar.multiselect[0].select("random · train").run()
    market = app.sidebar.selectbox[1]
    market.select(market.options[1]).run()
    assert not app.exception
    random = frames["random"]
    finals = random[random["done"]]["portfolio_value"].to_numpy() - 1000.0
    table = app.table[-1].value
    column = "PnL acumulado al mercado 2"
    assert table.loc["random · train", column] == f"{finals[:2].sum():+.2f}"


def test_a_policy_without_the_market_is_left_out_with_a_warning(tmp_path, monkeypatch, frames):
    folder = tmp_path / "reports" / "trajectories"
    folder.mkdir(parents=True)
    favorite = frames["favorite"]
    favorite.to_parquet(folder / "favorite_train.parquet")
    other = frames["random"]
    other[other["market_id"] != favorite["market_id"].iloc[0]].to_parquet(
        folder / "random_train.parquet"
    )
    monkeypatch.setenv("POLYM4V_REPORTS_DIR", str(tmp_path / "reports"))
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    at.sidebar.multiselect[0].select("random · train").run()
    assert not at.exception
    assert "random · train" in at.warning[0].value
    assert not [title for title in at.subheader if title.value == "Comparación"]


def test_the_report_proposes_the_best_agent_and_the_best_baseline(tmp_path, monkeypatch, frames):
    """Criterio de EVA-08: el mejor agente frente al mejor baseline, de entrada."""
    reports = tmp_path / "reports"
    folder = reports / "trajectories"
    folder.mkdir(parents=True)
    frames["random"].to_parquet(folder / "20261101-000000_ppo_pnl_s0_test.parquet")
    frames["random"].to_parquet(folder / "20261101-000000_ppo_pnl_s1_test.parquet")
    frames["favorite"].to_parquet(folder / "favorite_test.parquet")
    frames["favorite"].to_parquet(folder / "no_trade_test.parquet")
    frames["favorite"].to_parquet(folder / "momentum_test_estricto.parquet")
    (reports / "test").mkdir()
    pd.DataFrame(
        {
            "label": [
                "momentum",
                "20261101-000000_ppo_pnl_s1",
                "no_trade",
                "20261101-000000_ppo_pnl_s0",
            ],
            "strict": [True, False, False, False],
            "mean_return": [0.9, 0.2, 0.0, -0.1],
        }
    ).to_csv(reports / "test" / "summary.csv", index=False)
    monkeypatch.setenv("POLYM4V_REPORTS_DIR", str(reports))
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception
    assert at.sidebar.selectbox[0].value == "20261101-000000_ppo_pnl_s0 · test"
    assert at.sidebar.multiselect[0].value == [
        "20261101-000000_ppo_pnl_s1 · test",
        "no_trade · test",
    ]
    assert [title.value for title in at.subheader][-1] == "Comparación"
