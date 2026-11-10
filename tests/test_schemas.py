import pandas as pd
import pandera.pandas as pa
import pytest

from polym4v.data.schemas import (
    MARKET_AVAILABILITY,
    Market,
    PriceTick,
    SpotKline,
    known_market_fields,
)

W0 = 1_793_404_800
W1 = W0 + 3600


def markets(**changes):
    row = {
        "market_id": "0xabc",
        "slug": "bitcoin-up-or-down-october-30-8pm-et",
        "question": "Bitcoin Up or Down - October 30, 8PM ET",
        "yes_token_id": "111",
        "no_token_id": "222",
        "w0": W0,
        "w1": W1,
        "spot_open": 108_000.0,
        "spot_close": 108_250.5,
        "outcome": 1,
        "fees_enabled": True,
        "fee_rate": 0.07,
        "fee_exponent": 1.0,
        "n_points_window": 60,
        "max_gap_s": 60,
        "split": "train",
    }
    return pd.DataFrame([row | changes])


def prices(**changes):
    rows = {
        "market_id": ["0xabc", "0xabc", "0xabc"],
        "side": ["yes", "yes", "no"],
        "ts_event": [W0, W0 + 60, W0],
        "ts_available": [W0, W0 + 60, W0],
        "p": [0.51, 0.55, 0.49],
    }
    return pd.DataFrame(rows | changes)


def klines(**changes):
    rows = {
        "ts_event": [W0, W0 + 60],
        "ts_available": [W0 + 60, W0 + 120],
        "open": [108_000.0, 108_010.0],
        "high": [108_020.0, 108_030.0],
        "low": [107_990.0, 108_000.0],
        "close": [108_010.0, 108_025.0],
        "volume": [12.5, 0.0],
    }
    return pd.DataFrame(rows | changes)


def test_valid_tables_pass():
    Market.validate(markets())
    PriceTick.validate(prices())
    SpotKline.validate(klines())


def test_every_market_column_declares_when_it_is_known():
    assert set(MARKET_AVAILABILITY) == set(Market.to_schema().columns)


@pytest.mark.parametrize(
    ("t", "visible", "hidden"),
    [
        (W0 - 1, {"w0", "w1", "fee_rate"}, {"spot_open", "outcome", "spot_close"}),
        (W0, {"spot_open"}, {"outcome", "spot_close"}),
        (W1 - 1, {"spot_open"}, {"outcome", "spot_close"}),
        (W1, {"outcome", "spot_close"}, set()),
    ],
)
def test_market_fields_appear_only_when_known(t, visible, hidden):
    known = known_market_fields(t, W0, W1)
    assert visible <= known
    assert not hidden & known


def test_quality_and_split_are_never_observable():
    known = known_market_fields(W1 + 10**9, W0, W1)
    assert not {"split", "n_points_window", "max_gap_s"} & known


@pytest.mark.parametrize(
    ("schema", "frame"),
    [
        (Market, markets(outcome=2)),
        (Market, markets(w1=W0)),
        (Market, markets(split="dev")),
        (Market, markets(asset="BTC")),
        (PriceTick, prices(p=[0.51, 5000.49, 0.49])),
        (PriceTick, prices(ts_available=[W0, W0 + 59, W0])),
        (PriceTick, prices(ts_event=[W0, W0, W0], side=["yes", "yes", "no"])),
        (PriceTick, prices(side=["yes", "up", "no"])),
        (SpotKline, klines(ts_available=[W0, W0 + 60])),
        (SpotKline, klines(close=[108_010.0, 108_031.0])),
        (SpotKline, klines(ts_event=[W0, W0])),
    ],
    ids=[
        "outcome-no-binario",
        "ventana-vacia",
        "split-desconocido",
        "columna-extra",
        "precio-fuera-de-rango",
        "disponible-antes-de-ocurrir",
        "punto-duplicado",
        "lado-desconocido",
        "kline-conocida-al-abrir",
        "close-fuera-del-rango",
        "kline-duplicada",
    ],
)
def test_invalid_rows_are_rejected(schema, frame):
    with pytest.raises((pa.errors.SchemaError, pa.errors.SchemaErrors)):
        schema.validate(frame)
