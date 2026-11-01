"""Recompensas del entorno (ENV-05, docs/02 sección 2.4, S6 y S9).

`V_t` es el valor de la cartera con la posición valorada a liquidación (S9). Con `pnl`, la suma de
las recompensas del episodio es `(V_final - V_0) / V_0`: los costos cuentan una sola vez. Las
variantes se eligen por config para la ablación de ENV-08.
"""

from dataclasses import dataclass

from ..utils.config import RewardConfig


@dataclass
class RewardState:
    """Lo que la recompensa recuerda dentro del episodio: el valor inicial y el máximo."""

    v0: float
    peak: float


def reward(
    config: RewardConfig,
    state: RewardState,
    *,
    v_prev: float,
    v_now: float,
    invalid: bool,
    done: bool,
) -> tuple[float, dict[str, float]]:
    """Recompensa del paso y sus componentes, para `info["reward_components"]`."""
    pnl = (v_now - v_prev) / state.v0
    drawdown_prev = state.peak - v_prev
    state.peak = max(state.peak, v_now)
    drawdown_up = max(0.0, (state.peak - v_now) - drawdown_prev) / state.v0
    components = {
        "pnl": pnl,
        "drawdown": -config.lambda_dd * drawdown_up if config.name == "pnl_risk" else 0.0,
        "invalid": -config.lambda_invalid if invalid else 0.0,
        "terminal": (v_now - state.v0) / state.v0 if done else 0.0,
    }
    if config.name == "terminal":
        total = components["terminal"] + components["invalid"]
    else:
        total = pnl + components["drawdown"] + components["invalid"]
    return total, components
