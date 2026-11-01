import numpy as np
import pytest

from polym4v.agents.base import Action
from polym4v.data.capture import RawStore
from polym4v.env.market_env import PolymarketEnv
from polym4v.env.portfolio import FLAT
from polym4v.env.synthetic import synthetic_data
from polym4v.evaluation.backtest import episode_results, run_backtest
from polym4v.evaluation.verification import MarketTrades, TradeVerifier
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
T0 = 1_800_000_000


def trade(ts, price, size, side="BUY", outcome_index=0):
    return {
        "timestamp": f"2027-01-15T08:00:{ts:02d}Z",
        "price": str(price),
        "size": str(size),
        "side": side,
        "outcome_index": outcome_index,
    }


@pytest.fixture(scope="module")
def data():
    return synthetic_data(6, seed=7)


def test_trades_are_converted_to_yes_equivalent():
    trades = MarketTrades.from_raw(
        [
            trade(10, 0.3, 100, side="BUY", outcome_index=1),
            trade(5, 0.6, 50, side="SELL", outcome_index=0),
        ]
    )
    # Ordenados por fecha: primero la venta de YES y después la compra de NO.
    assert trades.yes_price.tolist() == pytest.approx([0.6, 0.7])
    # Comprar NO equivale a vender YES.
    assert trades.buy.tolist() == [False, False]
    assert trades.usdc.tolist() == pytest.approx([30.0, 30.0])


def verifier(ts, yes_price, buy, usdc):
    trades = MarketTrades(
        ts=np.array(ts, dtype=np.int64),
        yes_price=np.array(yes_price),
        buy=np.array(buy, dtype=bool),
        usdc=np.array(usdc),
    )
    return TradeVerifier({"m": trades}, latency_s=2, tolerance_s=60, min_usdc=20.0)


def test_a_trade_on_the_same_side_at_a_better_price_backs_the_execution():
    check = verifier([T0 + 10], [0.50], [True], [25.0])
    assert check("m", T0, buy=True, yes_price=0.51) is True
    assert check("m", T0, buy=True, yes_price=0.49) is False
    assert check("m", T0, buy=False, yes_price=0.49) is False


def test_only_trades_inside_the_window_and_with_enough_usdc_count():
    check = verifier(
        [T0 + 2, T0 + 30, T0 + 45, T0 + 61],
        [0.5, 0.5, 0.5, 0.5],
        [True, True, True, True],
        [100.0, 12.0, 9.0, 100.0],
    )
    # El de t + 2 llega antes de la orden y el de t + 61 después de la ventana.
    assert check("m", T0, buy=True, yes_price=0.5) is True  # 12 + 9 >= 20
    assert verifier([T0 + 30], [0.5], [True], [19.0])("m", T0, buy=True, yes_price=0.5) is False


def test_unknown_market_cannot_be_verified():
    assert verifier([], [], [], [])("otro", T0, buy=True, yes_price=0.5) is None


def test_load_reads_the_raw_trades(tmp_path):
    store = RawStore(tmp_path)
    store.write(store.trades_path("0xa"), {"body": [trade(10, 0.4, 100)]})
    loaded = TradeVerifier.load(store, ["0xa", "0xb"], latency_s=2, tolerance_s=60, min_usdc=20.0)
    assert set(loaded.trades) == {"0xa"}


class Recorder:
    """Verificador falso que anota cada consulta y responde lo que se le diga."""

    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def __call__(self, market_id, t, *, buy, yes_price):
        self.calls.append((market_id, t, buy, yes_price))
        return self.answer


def run(env, actions, market_id):
    env.reset(options={"market_id": market_id})
    infos = []
    for action in actions:
        infos.append(env.step(action)[4])
    return infos


def test_each_operation_is_checked_in_yes_equivalent(data):
    recorder = Recorder(True)
    env = PolymarketEnv(data, ENV, PNL, verifier=recorder)
    actions = [Action.WAIT] * 10 + [Action.BUY_NO] + [Action.WAIT] * 9 + [Action.SELL]
    infos = run(env, actions, data.market_ids[0])
    buy_no, sell_no = infos[10], infos[20]
    assert buy_no["order_status"] == sell_no["order_status"] == "ejecutada"
    # Comprar NO a q es vender YES a 1 - q; vender NO a q es comprar YES a 1 - q.
    assert recorder.calls[0][2:] == (False, pytest.approx(1 - buy_no["fill_price"]))
    assert recorder.calls[1][2:] == (True, pytest.approx(1 - sell_no["fill_price"]))
    assert recorder.calls[0][1] == buy_no["ts"] and buy_no["exec_verified"] is True


def test_normal_mode_records_but_still_executes(data):
    env = PolymarketEnv(data, ENV, PNL, verifier=Recorder(False))
    info = run(env, [Action.WAIT] * 10 + [Action.BUY_YES], data.market_ids[1])[10]
    assert info["order_status"] == "ejecutada" and info["exec_verified"] is False


def test_strict_mode_cancels_unbacked_executions(data):
    env = PolymarketEnv(data, ENV, PNL, verifier=Recorder(False), strict=True)
    info = run(env, [Action.WAIT] * 10 + [Action.BUY_YES], data.market_ids[1])[10]
    assert info["order_status"] == "no_verificable" and info["action_executed"] == Action.WAIT
    assert info["position_side"] == FLAT and info["fill_price"] is None
    # Un mercado sin trades tampoco se puede confirmar.
    unknown = PolymarketEnv(data, ENV, PNL, verifier=Recorder(None), strict=True)
    infos = run(unknown, [Action.WAIT] * 10 + [Action.BUY_YES], data.market_ids[1])
    assert infos[10]["order_status"] == "no_verificable"


def test_strict_mode_needs_a_verifier(data):
    with pytest.raises(ValueError, match="modo estricto"):
        PolymarketEnv(data, ENV, PNL, strict=True)


def test_results_count_verified_executions(data):
    from polym4v.agents.baselines import FavoritePolicy

    env = PolymarketEnv(data, ENV, PNL, verifier=Recorder(True))
    results = episode_results(run_backtest(FavoritePolicy(), env), 1000.0, 20.0)
    assert (results["verified"] == results["executed"]).all() and results["executed"].sum() > 0
    strict = PolymarketEnv(data, ENV, PNL, verifier=Recorder(False), strict=True)
    results = episode_results(run_backtest(FavoritePolicy(), strict), 1000.0, 20.0)
    assert results["executed"].sum() == 0 and results["unverifiable"].sum() > 0
    assert (results["final_value"] == 1000.0).all()
