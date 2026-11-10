"""Grilla de decisión y alineación point-in-time de cada fuente (DAT-04, S2 y S3, ADR-016).

En cada instante de decisión `t_k = w0 + step·k` se toma, de cada fuente, el último dato con
`ts_available <= t_k`: un *as-of* hacia atrás, como en S3 (opción A). Ninguna columna de una fila
depende de datos con `ts_available > t_k`.
"""

import numpy as np
import pandas as pd

# Retrasos de las diferencias de precio y de los retornos del spot (sección 4.1 de docs/08).
LAGS_S = (60, 300)
# Retornos de 1 minuto con que se mide la volatilidad, y mínimo para calcularla.
SIGMA_WINDOW = 60
SIGMA_MIN_PERIODS = 30


def decision_grid(markets: pd.DataFrame, step_s: int, n_steps: int) -> pd.DataFrame:
    """Una fila por mercado e instante de decisión, ordenada por mercado y paso."""
    grid = markets[["market_id", "w0", "w1", "spot_open"]].merge(
        pd.DataFrame({"k": np.arange(n_steps, dtype="int64")}), how="cross"
    )
    grid["ts"] = grid["w0"] + step_s * grid["k"]
    return grid.sort_values(["market_id", "k"]).reset_index(drop=True)


def asof(at: pd.Series, table: pd.DataFrame, by: pd.Series | None = None) -> pd.DataFrame:
    """Para cada valor de `at`, la última fila de `table` con `ts_available <= at`.

    Devuelve una fila por cada elemento de `at`, en el mismo orden. `by` restringe la búsqueda a
    las filas de `table` con la misma clave (`market_id`).
    """
    query = pd.DataFrame({"_at": at.to_numpy(), "_row": np.arange(len(at))})
    if by is not None:
        query["market_id"] = by.to_numpy()
    merged = pd.merge_asof(
        query.sort_values("_at"),
        table.sort_values("ts_available"),
        left_on="_at",
        right_on="ts_available",
        by="market_id" if by is not None else None,
        direction="backward",
        allow_exact_matches=True,
    )
    return merged.sort_values("_row").drop(columns=["_at", "_row"]).reset_index(drop=True)


def spot_with_sigma(spot: pd.DataFrame) -> pd.DataFrame:
    """Klines con la volatilidad de los retornos de 1 minuto hasta su cierre, inclusive."""
    spot = spot.sort_values("ts_event")
    returns = np.log(spot["close"]).diff()
    sigma = returns.rolling(SIGMA_WINDOW, min_periods=SIGMA_MIN_PERIODS).std()
    return pd.DataFrame(
        {"ts_available": spot["ts_available"], "close": spot["close"], "sigma": sigma}
    ).reset_index(drop=True)


def align(
    markets: pd.DataFrame,
    prices: pd.DataFrame,
    spot: pd.DataFrame,
    *,
    step_s: int,
    n_steps: int,
) -> pd.DataFrame:
    """Grilla con el último precio YES, el spot y sus valores pasados en cada instante.

    `t_p` es el instante del último precio, sin bajar de `w0`: antes de la vela no hay precio de
    referencia y el valor justo es 0,5. Con él se calcula la ventaja en el instante del precio
    (S3b).
    """
    grid = decision_grid(markets, step_s, n_steps)
    yes = prices.loc[prices["side"] == "yes", ["market_id", "ts_available", "ts_event", "p"]]
    spot = spot_with_sigma(spot)

    now = asof(grid["ts"], yes, grid["market_id"])
    grid["p_yes"] = now["p"]
    grid["p_ts"] = now["ts_event"]
    for lag in LAGS_S:
        minutes = lag // 60
        grid[f"p_yes_{minutes}"] = asof(grid["ts"] - lag, yes, grid["market_id"])["p"]
        grid[f"spot_{minutes}"] = asof(grid["ts"] - lag, spot)["close"]
    current = asof(grid["ts"], spot)
    grid["spot"], grid["sigma"] = current["close"], current["sigma"]
    grid["t_p"] = np.maximum(grid["p_ts"].fillna(grid["w0"]), grid["w0"]).astype("int64")
    at_price = asof(grid["t_p"], spot)
    grid["spot_p"], grid["sigma_p"] = at_price["close"], at_price["sigma"]
    return grid
