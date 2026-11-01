import math

import numpy as np
import pandas as pd
import pytest

from polym4v.data.steps import align, asof, spot_with_sigma
from polym4v.features.market import MARKET_FEATURES, add_features, apply_zscore, fair_value

W0 = 1_800_000_000 - 1_800_000_000 % 3600
STEP, N = 60, 60


def synthetic(n_markets=3, seed=0):
    """Mercados consecutivos con precio y spot que se mueven, y puntos a deshora."""
    rng = np.random.default_rng(seed)
    markets = pd.DataFrame(
        {
            "market_id": [f"0x{i}" for i in range(n_markets)],
            "w0": [W0 + 3600 * i for i in range(n_markets)],
        }
    )
    markets["w1"] = markets["w0"] + 3600
    times = np.arange(W0 - 2 * 3600, W0 + 3600 * (n_markets + 1), 60)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 1e-3, len(times))))
    spot = pd.DataFrame({"ts_event": times, "close": close})
    spot["ts_available"] = spot["ts_event"] + 60
    markets["spot_open"] = [close[times == w0][0] for w0 in markets["w0"]]
    rows = []
    for m in markets.itertuples():
        # Un punto por minuto con un desfase aleatorio de 0 a 40 s, como en los datos reales.
        for t in range(m.w0 - 3600, m.w1, 60):
            ts = t + int(rng.integers(0, 40))
            p = float(np.clip(rng.uniform(0.05, 0.95), 0, 1))
            rows += [
                {"market_id": m.market_id, "side": "yes", "ts_event": ts, "p": p},
                {"market_id": m.market_id, "side": "no", "ts_event": ts, "p": 1 - p},
            ]
    prices = pd.DataFrame(rows)
    prices["ts_available"] = prices["ts_event"]
    return markets, prices, spot


def steps_of(markets, prices, spot):
    return add_features(align(markets, prices, spot, step_s=STEP, n_steps=N), 3600)


def test_asof_takes_the_last_row_known_at_each_instant():
    table = pd.DataFrame({"ts_available": [10, 20, 30], "v": [1, 2, 3]})
    result = asof(pd.Series([5, 10, 25, 99]), table)
    assert result["v"].tolist()[1:] == [1, 2, 3] and math.isnan(result["v"][0])


def test_spot_at_t_is_the_kline_that_closes_at_t():
    markets, prices, spot = synthetic(n_markets=1)
    aligned = align(markets, prices, spot, step_s=STEP, n_steps=N)
    closing = spot.set_index("ts_event")["close"]
    assert aligned.loc[0, "spot"] == closing[W0 - 60]
    assert aligned.loc[10, "spot"] == closing[W0 + 9 * 60]


def test_price_is_the_last_point_at_or_before_t():
    markets, prices, spot = synthetic(n_markets=1)
    steps = steps_of(markets, prices, spot)
    yes = prices[prices["side"] == "yes"]
    for row in steps.itertuples():
        last = yes[yes["ts_available"] <= row.ts].iloc[-1]
        assert row.p_yes == last["p"] and row.p_stale_s == row.ts - last["ts_event"]


@pytest.mark.parametrize("cut_k", [0, 7, 30, 59])
def test_cutting_the_future_does_not_change_the_past(cut_k):
    """DAT-04 y DAT-07: truncar los datos en `t` no cambia ninguna fila con `ts <= t`."""
    markets, prices, spot = synthetic()
    full = steps_of(markets, prices, spot)
    cut = W0 + 3600 + STEP * cut_k

    truncated = steps_of(
        markets,
        prices[prices["ts_available"] <= cut],
        spot[spot["ts_available"] <= cut],
    )

    past = full["ts"] <= cut
    # Después del corte faltan datos y algunas columnas pasan a float; los valores no cambian.
    pd.testing.assert_frame_equal(full[past], truncated[past], check_dtype=False)


def test_changing_the_future_does_not_change_the_past():
    markets, prices, spot = synthetic()
    full = steps_of(markets, prices, spot)
    cut = W0 + 3600 + STEP * 20
    later_prices, later_spot = prices["ts_available"] > cut, spot["ts_available"] > cut
    prices.loc[later_prices, "p"] = 1 - prices.loc[later_prices, "p"]
    spot.loc[later_spot, "close"] *= 1.5

    changed = steps_of(markets, prices, spot)

    past = full["ts"] <= cut
    pd.testing.assert_frame_equal(full[past], changed[past])
    assert not full[~past].equals(changed[~past])


def test_features_are_complete_and_bounded():
    steps = steps_of(*synthetic())
    assert not steps[list(MARKET_FEATURES)].isna().any().any()
    assert steps["p_stale"].between(0, 1).all() and steps["tau"].between(0, 1).all()
    assert steps["z"].between(-5, 5).all() and steps["edge_tp"].between(-1, 1).all()


def test_fair_value():
    z, p = fair_value(np.array([0.0, 0.01, -0.01, 0.01]), np.array([1e-3] * 3 + [0.0]), np.ones(4))
    assert p[0] == 0.5 and p[1] > 0.99 and p[2] < 0.01
    # Sin volatilidad, z toma el recorte con el signo de x.
    assert z[3] == 5.0


def test_edge_tp_uses_the_fair_value_when_the_price_was_recorded():
    markets, prices, spot = synthetic(n_markets=1)
    aligned = align(markets, prices, spot, step_s=STEP, n_steps=N)
    steps = add_features(aligned, 3600)
    row = aligned.iloc[30]
    assert (
        row["t_p"] == row["p_ts"]
        and row["spot_p"] == asof(pd.Series([row["p_ts"]]), spot_with_sigma(spot)).loc[0, "close"]
    )
    # Antes de la vela no hay referencia: el instante del precio no baja de w0.
    assert aligned.loc[0, "t_p"] == W0 and steps.loc[0, "edge_tp"] == pytest.approx(
        0.5 - steps.loc[0, "p_yes"], abs=0.05
    )


def test_apply_zscore():
    steps = pd.DataFrame({"x": [1.0, 3.0], "p_yes": [0.2, 0.4]})
    out = apply_zscore(steps, {"x": {"mean": 2.0, "std": 1.0}})
    assert out["x"].tolist() == [-1.0, 1.0] and out["p_yes"].tolist() == [0.2, 0.4]
