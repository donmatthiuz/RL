"""Backtest de una política sobre los mercados de un split (EVA-02).

Recorre cada mercado una vez y en orden cronológico (S7), con la misma política reiniciada al
empezar cada uno, y devuelve una fila por paso con todas las claves de `info` (INF-06). Agentes y
baselines pasan por aquí, así que todos se evalúan con las mismas reglas.
"""

from collections.abc import Iterable

import pandas as pd

from ..agents.base import Policy
from ..env.market_env import INFO_KEYS, PolymarketEnv

STEP_KEYS = tuple(key for key in INFO_KEYS if key != "reward_components")
REWARD_COMPONENTS = ("pnl", "drawdown", "invalid", "terminal")


def run_backtest(
    policy: Policy, env: PolymarketEnv, markets: Iterable[str] | None = None
) -> pd.DataFrame:
    """Trayectorias de `policy` en `markets` (por defecto, todos los del entorno, en orden)."""
    rows = []
    for market_id in env.data.market_ids if markets is None else markets:
        policy.reset()
        obs, info = env.reset(options={"market_id": market_id})
        done = False
        while not done:
            obs, reward, done, _, info = env.step(policy.act(obs, info))
            row = {key: info[key] for key in STEP_KEYS}
            row |= {f"r_{name}": info["reward_components"][name] for name in REWARD_COMPONENTS}
            rows.append(row | {"reward": reward, "done": done})
    frame = pd.DataFrame(rows)
    frame.insert(0, "policy", policy.name)
    return frame


def episode_results(trajectories: pd.DataFrame, initial_cash: float, stake: float) -> pd.DataFrame:
    """Una fila por mercado: valor final, retorno sobre el monto apostado y órdenes por estado.

    `verified` cuenta las ejecuciones respaldadas por trades reales (EVA-11); sin un verificador,
    vale 0.
    """
    status = pd.crosstab(trajectories["market_id"], trajectories["order_status"])
    last = trajectories[trajectories["done"]].set_index("market_id")
    status = status.reindex(
        index=last.index,
        columns=["ejecutada", "sin_precio", "no_verificable", "invalida"],
        fill_value=0,
    )
    verified = trajectories["exec_verified"].eq(True) & trajectories["order_status"].eq("ejecutada")
    return pd.DataFrame(
        {
            "policy": last["policy"],
            "final_value": last["portfolio_value"],
            "return_on_stake": (last["portfolio_value"] - initial_cash) / stake,
            "fees_paid": last["fees_paid"],
            "executed": status["ejecutada"],
            "verified": verified.groupby(trajectories["market_id"]).sum().reindex(last.index),
            "no_price": status["sin_precio"],
            "unverifiable": status["no_verificable"],
            "invalid": status["invalida"],
        }
    )
