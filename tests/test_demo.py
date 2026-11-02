"""Demo de Streamlit (EVA-07), con trayectorias de mercados sintéticos y sin red."""

from pathlib import Path

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
