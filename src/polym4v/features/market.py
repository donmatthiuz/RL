"""Features de mercado de la observación (DAT-07, sección 4.1 de docs/08, S3 y ADR-016).

Funciones puras sobre la grilla alineada de `data/steps.py`: cada fila solo usa datos con
`ts_available <= ts`. El estado del agente (`pos_side`, `entry_price` y `upnl`) lo agrega el
entorno.
"""

import math

import numpy as np
import pandas as pd

# Orden de las features de mercado en la observación.
MARKET_FEATURES = (
    "p_yes",
    "dp_1",
    "dp_5",
    "p_stale",
    "x",
    "r_1",
    "r_5",
    "sigma",
    "tau",
    "z",
    "p_fair",
    "edge",
    "edge_tp",
)
# Las que no tienen una escala acotada se normalizan con media y desviación de train.
ZSCORE_FEATURES = ("dp_1", "dp_5", "x", "r_1", "r_5", "sigma")
STALE_CAP_S = 300
Z_CLIP = 5.0

_erf = np.vectorize(math.erf, otypes=[float])


def fair_value(
    x: np.ndarray, sigma: np.ndarray, minutes_left: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """`z` y la probabilidad de UP si el spot sigue un paseo aleatorio sin deriva.

    `x = ln(spot / spot_open)` y `sigma` es la desviación de los retornos de 1 minuto. Con
    volatilidad nula, `z` toma el valor del recorte con el signo de `x`.
    """
    scale = sigma * np.sqrt(minutes_left)
    safe = np.where(scale > 0, scale, 1.0)
    z = np.clip(np.where(scale > 0, x / safe, np.sign(x) * Z_CLIP), -Z_CLIP, Z_CLIP)
    return z, 0.5 * (1.0 + _erf(z / math.sqrt(2.0)))


def add_features(aligned: pd.DataFrame, window_s: int) -> pd.DataFrame:
    """Columnas de `MARKET_FEATURES`, más `p_stale_s`, a partir de la grilla alineada."""
    a = aligned
    out = pd.DataFrame(
        {
            "market_id": a["market_id"],
            "k": a["k"],
            "ts": a["ts"],
            "p_stale_s": a["ts"] - a["p_ts"],
            "spot": a["spot"],
            "p_yes": a["p_yes"],
            "dp_1": a["p_yes"] - a["p_yes_1"],
            "dp_5": a["p_yes"] - a["p_yes_5"],
        }
    )
    out["p_stale"] = np.minimum(out["p_stale_s"] / STALE_CAP_S, 1.0)
    out["x"] = np.log(a["spot"] / a["spot_open"])
    out["r_1"] = np.log(a["spot"] / a["spot_1"])
    out["r_5"] = np.log(a["spot"] / a["spot_5"])
    out["sigma"] = a["sigma"]
    out["tau"] = (a["w1"] - a["ts"]) / window_s
    z, p_fair = fair_value(
        out["x"].to_numpy(), a["sigma"].to_numpy(), ((a["w1"] - a["ts"]) / 60).to_numpy()
    )
    out["z"], out["p_fair"] = z, p_fair
    out["edge"] = out["p_fair"] - out["p_yes"]
    # S3b: la ventaja contra el valor justo del instante en que se registró el precio.
    _, p_fair_tp = fair_value(
        np.log(a["spot_p"] / a["spot_open"]).to_numpy(),
        a["sigma_p"].to_numpy(),
        ((a["w1"] - a["t_p"]) / 60).to_numpy(),
    )
    out["edge_tp"] = p_fair_tp - out["p_yes"]
    return out


def fit_zscore(train: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Media y desviación de cada feature de `ZSCORE_FEATURES`, solo con filas de train."""
    return {
        name: {"mean": float(train[name].mean()), "std": float(train[name].std())}
        for name in ZSCORE_FEATURES
    }


def apply_zscore(steps: pd.DataFrame, stats: dict[str, dict[str, float]]) -> pd.DataFrame:
    """Copia de `steps` con las features de `stats` normalizadas."""
    out = steps.copy()
    for name, s in stats.items():
        out[name] = (out[name] - s["mean"]) / s["std"]
    return out
