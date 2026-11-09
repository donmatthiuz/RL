"""Demo de Streamlit (EVA-07 a EVA-09 y EVA-13), con mercados sintéticos y sin red."""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from polym4v.agents.baselines import FavoritePolicy, NoTradePolicy, RandomPolicy
from polym4v.env.execution import buy
from polym4v.env.market_env import PolymarketEnv
from polym4v.env.synthetic import synthetic_data, synthetic_frames
from polym4v.evaluation.backtest import run_backtest
from polym4v.utils.config import SimulatorConfig, load_config

APP = str(Path(__file__).parents[1] / "app" / "demo.py")
SIMULATION, COMPARISON, GUIDE = "views/simulation.py", "views/comparison.py", "views/guide.py"
PPO = "20261101-000000_ppo_pnl_s{}"


@pytest.fixture(scope="module")
def frames():
    config = load_config("configs/env.yaml", SimulatorConfig)
    env = PolymarketEnv(synthetic_data(3, seed=5), config.env, config.reward)
    policies = (FavoritePolicy(), RandomPolicy(), NoTradePolicy())
    return {policy.name: run_backtest(policy, env) for policy in policies}


def dataset(root: Path, trajectory: pd.DataFrame, split: str) -> None:
    """Dataset mínimo con la pregunta, el resultado y BTC por minuto de los mercados sintéticos."""
    folder = root / "processed" / "btc_updown_1h_v1"
    folder.mkdir(parents=True)
    markets = synthetic_frames(3, seed=5)[0].assign(split=split)
    markets.to_parquet(folder / "markets.parquet")
    steps = trajectory[["market_id", "k", "ts"]].merge(markets[["market_id", "spot_open"]])
    steps.assign(spot=lambda d: d["spot_open"] + d["k"]).drop(columns="spot_open").to_parquet(
        folder / "steps.parquet"
    )


def protocol(reports: Path, split: str, seeds: dict[int, float]) -> None:
    """Comparación del protocolo en la que gana PPO, y el retorno de cada semilla."""
    (reports / split).mkdir(parents=True)
    pd.DataFrame(
        {
            "group": ["dqn_pnl", "ppo_pnl", "ppo_pnl"],
            "strict": [False, False, True],
            "role": ["principal"] * 3,
            "baseline": ["no_trade"] * 3,
            "mean": [-0.2, -0.1, 0.5],
            "lower": [-0.3, -0.2, 0.4],
            "upper": [0.1, 0.05, 0.6],
            "classification": ["inconcluso", "equivalente", "mejor"],
        }
    ).to_csv(reports / split / "comparison.csv", index=False)
    pd.DataFrame(
        {
            "label": [PPO.format(seed) for seed in seeds] + ["no_trade", "fair_value"],
            "strict": [False] * (len(seeds) + 2),
            "mean_return": [*seeds.values(), 0.0, 0.9],
        }
    ).to_csv(reports / split / "summary.csv", index=False)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("POLYM4V_REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("POLYM4V_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "reports" / "trajectories").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def app(env, frames):
    """La demo en la simulación, con dos políticas de train y BTC por minuto."""
    folder = env / "reports" / "trajectories"
    frames["favorite"].to_parquet(folder / "favorite_train.parquet")
    frames["random"].to_parquet(folder / "random_train.parquet")
    dataset(env / "data", frames["favorite"], "train")
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.switch_page(SIMULATION).run()
    assert not at.exception
    return at


def button(at, label):
    return next(item for item in at.button if item.label == label)


def metric(at, label):
    return next(item for item in at.metric if item.label == label)


def first_executed(frame):
    executed = frame[frame["order_status"] == "ejecutada"]
    return executed.iloc[0]


def test_every_page_opens_without_errors(app):
    for page in (COMPARISON, GUIDE, "views/home.py"):
        app.switch_page(page).run()
        assert not app.exception, page


def test_the_home_page_shows_the_protocol_result(env):
    protocol(env / "reports", "test", {0: 0.1})
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception
    assert ":blue-badge[PPO: equivalente]" in [item.value for item in at.markdown]


def test_without_trajectories_it_opens_the_test_sample(env):
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.switch_page(SIMULATION).run()
    assert not at.exception
    assert at.session_state.folder == str(Path(APP).parent / "trayectorias")
    assert at.sidebar.selectbox[0].value.endswith(" · test")


def test_an_empty_folder_explains_how_to_create_trajectories(app, env):
    app.session_state.folder = str(env)
    app.run()
    assert not app.exception
    assert "make backtest" in app.info[0].value
    assert not app.slider


def test_it_starts_on_the_first_market_where_the_policy_traded(app, frames):
    favorite = frames["favorite"]
    assert app.sidebar.selectbox[0].value == "favorite · train"
    assert app.sidebar.selectbox[1].value == first_executed(favorite)["market_id"]
    assert app.slider[0].value == 0
    assert metric(app, "Cartera (USDC)").value == "1,000.00"


def test_btc_and_the_question_come_from_the_dataset(app, frames):
    market = app.sidebar.selectbox[1].value
    question = synthetic_frames(3, seed=5)[0].set_index("market_id").loc[market, "question"]
    assert app.markdown[0].value == f"## {question}"
    assert "frente a la apertura" in app.info[0].value
    assert metric(app, "BTC").delta == "+0.000%"


def test_buttons_move_one_minute_and_stay_inside_the_market(app):
    button(app, "Minuto siguiente").click().run()
    button(app, "Minuto siguiente").click().run()
    assert app.session_state.step == 2
    button(app, "Minuto anterior").click().run()
    assert app.session_state.step == 1
    button(app, "Ir al cierre").click().run()
    button(app, "Minuto siguiente").click().run()
    assert app.session_state.step == 59
    button(app, "Reiniciar").click().run()
    assert app.session_state.step == 0


def test_play_advances_and_pause_keeps_the_minute(app):
    button(app, "Reproducir").click().run()
    assert app.session_state.playing
    assert app.session_state.step == 1
    app.run()
    assert app.session_state.step == 2
    button(app, "Pausar").click().run()
    assert not app.session_state.playing
    app.run()
    assert app.session_state.step == 2


def test_playing_stops_by_itself_at_the_close(app):
    button(app, "Minuto siguiente").click().run()
    app.session_state.step = 58
    button(app, "Reproducir").click().run()
    assert not app.exception
    assert app.session_state.step == 59
    assert not app.session_state.playing


def test_the_minute_of_a_purchase_is_narrated(app, frames):
    row = first_executed(frames["favorite"])
    app.session_state.step = int(row["k"])
    app.run()
    text = app.info[0].value
    assert "compra" in text
    assert f"{row['fill_shares']:.2f} acciones a {row['fill_price']:.4f}" in text
    assert metric(app, "Posición").value in ("YES", "NO")


def test_the_close_shows_the_outcome_and_the_pnl(app, frames):
    market = app.sidebar.selectbox[1].value
    favorite = frames["favorite"]
    final = favorite[(favorite["market_id"] == market) & favorite["done"]].iloc[0]
    button(app, "Ir al cierre").click().run()
    texts = [item.value for item in app.markdown]
    assert any(text.startswith("#### BTC cerró en") for text in texts)
    assert any(f"{final['portfolio_value'] - 1000.0:+.2f} USDC" in text for text in texts)
    assert metric(app, "Posición").value == "liquidada"


def test_changing_market_goes_back_to_the_first_minute(app):
    app.session_state.step = 10
    app.run()
    market = app.sidebar.selectbox[1]
    before = market.value
    market.select_index(1 if market.index == 0 else 0).run()
    assert app.sidebar.selectbox[1].value != before
    assert app.session_state.step == 0


def test_the_protocol_opens_the_median_seed_of_the_best_agent(env, frames):
    """Criterio de EVA-08: el mejor agente frente al mejor baseline en un mercado de test."""
    folder = env / "reports" / "trajectories"
    for seed in range(3):
        frames["favorite"].to_parquet(folder / f"{PPO.format(seed)}_test.parquet")
    frames["no_trade"].to_parquet(folder / "no_trade_test.parquet")
    frames["random"].to_parquet(folder / "fair_value_test.parquet")
    frames["random"].to_parquet(folder / "momentum_test.parquet")
    # La mejor semilla de PPO es s2: no se elige.
    protocol(env / "reports", "test", {0: 0.1, 1: -0.3, 2: 0.4})
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.switch_page(SIMULATION).run()
    assert not at.exception
    assert at.sidebar.selectbox[0].value == f"{PPO.format(0)} · test"
    assert at.sidebar.selectbox[1].value == first_executed(frames["favorite"])["market_id"]

    at.switch_page(COMPARISON).run()
    assert not at.exception
    assert at.multiselect[0].value == ["no_trade · test", "fair_value · test"]
    assert any(item.value == "### Lo que dice el protocolo" for item in at.markdown)


def test_comparison_shows_the_pnl_of_each_policy_in_the_market(app, frames):
    app.switch_page(COMPARISON).run()
    app.multiselect[0].select("random · train").run()
    assert not app.exception
    market = app.sidebar.selectbox[1].value
    random = frames["random"]
    final = random[(random["market_id"] == market) & random["done"]].iloc[0]
    assert metric(app, "Al azar").value == f"{final['portfolio_value'] - 1000.0:+.2f} USDC"


def test_the_guide_computes_the_cost_of_buying(app):
    app.switch_page(GUIDE).run()
    assert not app.exception
    costs = app.dataframe[0].value
    row = costs[costs["Precio del lado"] == "0.98"].iloc[0]
    costs_config = load_config("configs/env.yaml", SimulatorConfig).env.costs
    fill = buy(20.0, 0.98, costs_config)
    assert row["Precio pagado"] == "0.990"
    assert row["Hay que acertar al menos"] == f"{20.0 / fill.shares:.2%}"
