"""Recompensas del entorno (ENV-05, docs/02 sección 2.4, S6 y S9).

`V_t` es el valor de la cartera con la posición valorada a liquidación (S9) y `M_t` el mismo valor
con la posición a precio medio. Las variantes son las de la ablación de ENV-08
(`docs/ia/investigaciones/recompensas_rl_trading.md`):

- `pnl`: `ΔV_t`. La suma del episodio es el PnL final, así que los costos cuentan una vez.
- `pnl_mid`: `ΔM_t`. Suma lo mismo; no adelanta el costo de salir.
- `terminal`: solo el PnL final.
- `pnl_risk` y `pnl_hold`: `base` menos el aumento del drawdown de `V` o un monto fijo por cada
  paso con posición.
- `utility`: solo al final, `(1 - exp(-a·x)) / a` con `x` el PnL sobre el monto (CARA).

Todo se divide por `V_0` o por el monto (`scale`). La recompensa del paso es la suma de sus
componentes.
"""

import math
from dataclasses import dataclass

from ..utils.config import RewardConfig

# Claves de `info["reward_components"]`, en el orden en que se reportan.
COMPONENTS = ("pnl", "drawdown", "hold", "invalid", "terminal")


@dataclass
class RewardState:
    """Lo que la recompensa recuerda dentro del episodio: el valor inicial, el máximo y el monto."""

    v0: float
    peak: float
    stake: float


def reward(
    config: RewardConfig,
    state: RewardState,
    *,
    v_prev: float,
    v_now: float,
    mid_prev: float,
    mid_now: float,
    holding: bool,
    invalid: bool,
    done: bool,
) -> tuple[float, dict[str, float]]:
    """Recompensa del paso y sus componentes, para `info["reward_components"]`.

    `holding` dice si hubo posición abierta durante el paso, después de la acción.
    """
    unit = state.v0 if config.scale == "v0" else state.stake
    base = config.base if config.name in ("pnl_risk", "pnl_hold") else config.name
    drawdown_prev = state.peak - v_prev
    state.peak = max(state.peak, v_now)
    drawdown_up = max(0.0, (state.peak - v_now) - drawdown_prev) / unit

    dense = 0.0
    if base == "pnl":
        dense = (v_now - v_prev) / unit
    elif base == "pnl_mid":
        dense = (mid_now - mid_prev) / unit
    terminal = 0.0
    if done and base == "terminal":
        terminal = (v_now - state.v0) / unit
    elif done and base == "utility":
        a, x = config.utility_a, (v_now - state.v0) / state.stake
        terminal = -math.expm1(-a * x) / a * state.stake / unit
    components = {
        "pnl": dense,
        "drawdown": -config.lambda_dd * drawdown_up if config.name == "pnl_risk" else 0.0,
        "hold": -config.lambda_hold if config.name == "pnl_hold" and holding else 0.0,
        "invalid": -config.lambda_invalid if invalid else 0.0,
        "terminal": terminal,
    }
    return sum(components.values()), components
