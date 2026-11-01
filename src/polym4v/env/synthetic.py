"""Mercados sintéticos con un valor justo conocido (ENV-10 y AGT-06).

El spot sigue un paseo aleatorio con klines de 1 minuto y volatilidad `sigma` conocida. El precio
del mercado es la probabilidad exacta de UP con lo que se sabía `lag_s` segundos antes:

- con `lag_s = 0` es el **mercado nulo** de ENV-10: ninguna política puede ganar en promedio sin
  información del futuro;
- con un retraso de 2 minutos o más es el **control positivo** de AGT-06: seguir al spot gana.

Los puntos de precio llegan una vez por minuto, entre 0 y `max_offset_s` segundos después del
minuto, como en los datos reales. Las tablas siguen los contratos de `data/schemas.py`.
"""

import math

import numpy as np
import pandas as pd

from ..data.steps import align
from ..features.market import add_features, fit_zscore
from .market_data import MarketData

HOUR = 3600
START = 1_798_761_600  # 2027-01-01 00:00 UTC


def _fair(x: np.ndarray, sigma: float, returns_left: np.ndarray) -> np.ndarray:
    z = x / (sigma * np.sqrt(np.maximum(returns_left, 1)))
    return 0.5 * (1.0 + np.vectorize(math.erf)(z / math.sqrt(2.0)))


def synthetic_frames(
    n_markets: int,
    *,
    lag_s: int = 0,
    sigma: float = 1e-3,
    max_offset_s: int = 40,
    seed: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """`markets`, `prices_raw` y `spot_1m` de `n_markets` velas consecutivas."""
    rng = np.random.default_rng(seed)
    opens = np.arange(START - 2 * HOUR, START + HOUR * n_markets + HOUR, 60)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, len(opens))))
    open_ = np.concatenate([[100.0], close[:-1]])
    spot = pd.DataFrame(
        {
            "ts_event": opens,
            "ts_available": opens + 60,
            "open": open_,
            "high": np.maximum(open_, close),
            "low": np.minimum(open_, close),
            "close": close,
            "volume": 1.0,
        }
    )
    by_open = pd.Series(np.arange(len(opens)), index=opens)

    markets, prices = [], []
    for i in range(n_markets):
        w0 = START + HOUR * i
        w1 = w0 + HOUR
        spot_open = float(open_[by_open[w0]])
        spot_close = float(close[by_open[w1 - 60]])
        market_id = f"0xsint{i:05d}"
        markets.append(
            {
                "market_id": market_id,
                "slug": f"sintetico-{i}",
                "question": f"Mercado sintético {i}",
                "yes_token_id": f"{i}1",
                "no_token_id": f"{i}2",
                "w0": w0,
                "w1": w1,
                "spot_open": spot_open,
                "spot_close": spot_close,
                "outcome": int(spot_close >= spot_open),
                "fees_enabled": True,
                "fee_rate": 0.07,
                "fee_exponent": 1.0,
                "n_points_window": 60,
                "max_gap_s": 60 + max_offset_s,
                "split": "train",
            }
        )
        ts = np.arange(w0 - HOUR, w1, 60) + rng.integers(0, max_offset_s + 1, 2 * 60)
        ts = ts[ts < w1]
        # Lo que se sabía en ts - lag: las klines cerradas hasta ese instante.
        known = ts - lag_s
        closed = np.floor((known - w0) / 60).astype(int)
        started = closed >= 1
        last = by_open.reindex(w0 + 60 * (np.where(started, closed, 1) - 1)).to_numpy()
        x = np.log(close[last] / spot_open)
        p = np.where(started, _fair(x, sigma, 60 - closed), 0.5)
        for side, values in (("yes", p), ("no", 1.0 - p)):
            prices.append(
                pd.DataFrame(
                    {
                        "market_id": market_id,
                        "side": side,
                        "ts_event": ts,
                        "ts_available": ts,
                        "p": values,
                    }
                )
            )
    return pd.DataFrame(markets), pd.concat(prices, ignore_index=True), spot


def synthetic_data(n_markets: int, **kwargs: int | float) -> MarketData:
    """Episodios sintéticos listos para `PolymarketEnv`, con la normalización ajustada en ellos."""
    markets, prices, spot = synthetic_frames(n_markets, **kwargs)  # type: ignore[arg-type]
    steps = add_features(align(markets, prices, spot, step_s=60, n_steps=60), HOUR)
    return MarketData.from_frames(markets, steps, prices, fit_zscore(steps))
