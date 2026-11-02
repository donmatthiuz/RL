"""Contratos de datos del dataset procesado (INF-06, S1).

Cada dato guarda cuándo ocurrió (`ts_event`) y cuándo se pudo conocer (`ts_available`). El
simulador solo lee filas con `ts_available <= t`. Todos los tiempos son segundos unix en UTC.

`steps.parquet` no está aquí: depende de qué ve el agente y de cuándo se ejecuta (S3 y S4),
que siguen pendientes.
"""

import math
from typing import Literal

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

KLINE_SECONDS = 60

When = Literal["siempre", "w0", "w1", "nunca"]

# Cuándo se conoce cada columna de markets. "nunca" marca lo que se calcula con el mercado
# completo (calidad y split) y por eso no puede entrar en la observación.
MARKET_AVAILABILITY: dict[str, When] = {
    "market_id": "siempre",
    "slug": "siempre",
    "question": "siempre",
    "yes_token_id": "siempre",
    "no_token_id": "siempre",
    "w0": "siempre",
    "w1": "siempre",
    "fees_enabled": "siempre",
    "fee_rate": "siempre",
    "fee_exponent": "siempre",
    "spot_open": "w0",
    "spot_close": "w1",
    "outcome": "w1",
    "n_points_window": "nunca",
    "max_gap_s": "nunca",
    "split": "nunca",
}


class Market(pa.DataFrameModel):
    """`markets.parquet`: una fila por mercado."""

    market_id: Series[str] = pa.Field(unique=True)
    slug: Series[str]
    question: Series[str]
    yes_token_id: Series[str]
    no_token_id: Series[str]
    w0: Series[int] = pa.Field(ge=0)
    w1: Series[int] = pa.Field(ge=0)
    spot_open: Series[float] = pa.Field(gt=0)
    spot_close: Series[float] = pa.Field(gt=0)
    outcome: Series[int] = pa.Field(isin=[0, 1])
    fees_enabled: Series[bool]
    fee_rate: Series[float] = pa.Field(ge=0)
    fee_exponent: Series[float] = pa.Field(ge=0)
    n_points_window: Series[int] = pa.Field(ge=0)
    max_gap_s: Series[int] = pa.Field(ge=0)
    split: Series[str] = pa.Field(isin=["train", "val", "test"])

    class Config:
        strict = True

    @pa.dataframe_check
    @classmethod
    def window_is_forward(cls, df: pd.DataFrame) -> pd.Series:
        return df["w1"] > df["w0"]


class PriceTick(pa.DataFrameModel):
    """`prices_raw.parquet`: cada punto del historial del CLOB, sin re-muestrear.

    `ts_available` es `ts_event` más la latencia del feed; su valor lo fija S4.
    """

    market_id: Series[str]
    side: Series[str] = pa.Field(isin=["yes", "no"])
    ts_event: Series[int] = pa.Field(ge=0)
    ts_available: Series[int] = pa.Field(ge=0)
    p: Series[float] = pa.Field(ge=0, le=1)

    class Config:
        strict = True
        unique = ["market_id", "side", "ts_event"]

    @pa.dataframe_check
    @classmethod
    def known_after_it_happens(cls, df: pd.DataFrame) -> pd.Series:
        return df["ts_available"] >= df["ts_event"]


class SpotKline(pa.DataFrameModel):
    """`spot_1m.parquet`: klines de 1 minuto de Binance; `ts_event` es su `open_time`.

    La kline que abre en `t` trae datos hasta `t + 59 s`, así que se conoce al cerrar.
    """

    ts_event: Series[int] = pa.Field(ge=0, unique=True)
    ts_available: Series[int] = pa.Field(ge=0)
    open: Series[float] = pa.Field(gt=0)
    high: Series[float] = pa.Field(gt=0)
    low: Series[float] = pa.Field(gt=0)
    close: Series[float] = pa.Field(gt=0)
    volume: Series[float] = pa.Field(ge=0)

    class Config:
        strict = True

    @pa.dataframe_check
    @classmethod
    def known_when_it_closes(cls, df: pd.DataFrame) -> pd.Series:
        return df["ts_available"] == df["ts_event"] + KLINE_SECONDS

    @pa.dataframe_check
    @classmethod
    def prices_inside_range(cls, df: pd.DataFrame) -> pd.Series:
        low, high = df["low"], df["high"]
        return df["open"].between(low, high) & df["close"].between(low, high)


def known_market_fields(t: int, w0: int, w1: int) -> frozenset[str]:
    """Columnas de markets que el simulador puede leer en `t` para la ventana `[w0, w1]`."""
    times = {"siempre": -math.inf, "w0": w0, "w1": w1, "nunca": math.inf}
    return frozenset(c for c, when in MARKET_AVAILABILITY.items() if times[when] <= t)
