from pathlib import Path

import pytest

from polym4v.env.execution import ask, bid, buy, sell, taker_fee
from polym4v.utils.config import CostConfig, load_named

REPO = Path(__file__).resolve().parents[1]
COSTS = CostConfig(
    half_spread=0.01, fee_rate=0.07, fee_exponent=1, fee_decimals=5, min_fee=0.00001, tick=0.001
)
NO_FEES = COSTS.model_copy(update={"fee_rate": 0.0})
OLD_SCHEME = COSTS.model_copy(update={"fee_rate": 0.25, "fee_exponent": 2})


def test_repo_costs_config_is_valid():
    assert load_named(REPO / "configs" / "costs.yaml") == COSTS


@pytest.mark.parametrize(
    ("shares", "price", "costs", "expected"),
    [
        (100, 0.5, COSTS, 1.75),
        (100, 0.9, COSTS, 0.63),
        (100, 0.5, OLD_SCHEME, 1.5625),
        # 0.07 × 0.123456 × 0.876544 = 0.0075750... y 0.07 × 0.31 × 0.69 = 0.014973: a 5 decimales.
        (1, 0.123456, COSTS, 0.00758),
        (1, 0.31, COSTS, 0.01497),
        # 0.00000175 redondea a 0, pero la comisión mínima es 0.00001.
        (0.0001, 0.5, COSTS, 0.00001),
        (100, 0.5, NO_FEES, 0.0),
    ],
    ids=[
        "v2-p05",
        "v2-p09",
        "esquema-anterior",
        "redondeo-arriba",
        "redondeo-abajo",
        "minimo",
        "sin-comision",
    ],
)
def test_taker_fee(shares, price, costs, expected):
    assert taker_fee(shares, price, costs) == expected


def test_prices_cross_the_spread_without_leaving_the_tick_range():
    assert ask(0.5, COSTS) == pytest.approx(0.51)
    assert bid(0.5, COSTS) == pytest.approx(0.49)
    assert ask(0.995, COSTS) == pytest.approx(0.999)
    assert bid(0.005, COSTS) == pytest.approx(0.001)


def test_buy_spends_the_stake_including_the_fee():
    fill = buy(100.0, 0.5, COSTS)

    assert fill.price == pytest.approx(0.51)
    assert fill.fee == taker_fee(fill.shares, 0.51, COSTS)
    assert fill.cash == pytest.approx(-100.0, abs=1e-5)


def test_round_trip_without_price_change_loses_exactly_the_costs():
    bought = buy(100.0, 0.5, COSTS)
    sold = sell(bought.shares, 0.5, COSTS)

    lost = -(bought.cash + sold.cash)
    spread = bought.shares * (bought.price - sold.price)
    assert lost == pytest.approx(spread + bought.fee + sold.fee)
    assert lost > 0


def test_without_fees_the_round_trip_only_pays_the_spread():
    bought = buy(100.0, 0.5, NO_FEES)
    sold = sell(bought.shares, 0.5, NO_FEES)

    assert bought.fee == sold.fee == 0.0
    assert -(bought.cash + sold.cash) == pytest.approx(bought.shares * 0.02)
