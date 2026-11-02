"""Métricas por política sobre un split (EVA-03, secciones 3 y 8 del protocolo de EVA-01).

La métrica principal es el retorno por mercado sobre el monto apostado, `R_i = PnL_i / stake`; un
mercado sin operar tiene `R_i = 0`. Las demás son secundarias: ayudan a entender el resultado pero
no cambian la conclusión.
"""

import math
from typing import Any

import numpy as np
import pandas as pd

from .backtest import episode_results


def capital_curve(pnl: pd.Series) -> pd.Series:
    """PnL acumulado en el orden de los mercados, que es el temporal."""
    return pnl.cumsum()


def max_drawdown(curve: pd.Series) -> float:
    """Mayor caída desde un máximo previo de la curva, contando el punto de partida en 0."""
    values = np.concatenate([[0.0], curve.to_numpy(dtype=float)])
    return float((np.maximum.accumulate(values) - values).max())


def spread_paid(trajectories: pd.DataFrame) -> float:
    """Spread pagado: acciones por la distancia entre el precio del lado y el de la operación."""
    held = trajectories.groupby("market_id", sort=False)["position_side"].shift(fill_value=0)
    done = trajectories[trajectories["order_status"] == "ejecutada"]
    side = np.where(done["action_executed"] == 3, held[done.index], done["position_side"])
    side_price = np.where(side == 1, done["exec_p"], 1.0 - done["exec_p"])
    return float((done["fill_shares"] * (done["fill_price"] - side_price).abs()).sum())


def summarize(trajectories: pd.DataFrame, initial_cash: float, stake: float) -> dict[str, Any]:
    """Métrica principal y secundarias de una política en un split."""
    results = episode_results(trajectories, initial_cash, stake)
    r = results["return_on_stake"]
    pnl = results["final_value"] - initial_cash
    traded = results["executed"] > 0
    std = float(r.std(ddof=1)) if len(r) > 1 else math.nan
    orders = results[["executed", "no_price", "unverifiable"]].to_numpy().sum()
    executed = int(results["executed"].sum())
    verified = trajectories["exec_verified"].notna().any()
    return {
        "policy": str(trajectories["policy"].iloc[0]),
        "markets": len(results),
        "mean_return": float(r.mean()),
        "total_pnl": float(pnl.sum()),
        "sharpe": float(r.mean() / std) if std > 0 else math.nan,
        "max_drawdown": max_drawdown(capital_curve(pnl)),
        "win_rate": float((pnl[traded] > 0).mean()) if traded.any() else math.nan,
        "trades_per_market": float(results["executed"].mean()),
        "no_trade_share": float((~traded).mean()),
        "fees_paid": float(results["fees_paid"].sum()),
        "spread_paid": spread_paid(trajectories),
        "invalid_share": float(results["invalid"].sum() / len(trajectories)),
        "no_price_share": float(results["no_price"].sum() / orders) if orders else math.nan,
        "verified_share": (
            float(results["verified"].sum() / executed) if verified and executed else math.nan
        ),
    }
