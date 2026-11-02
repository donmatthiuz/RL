"""Ajuste de los umbrales de los baselines en val (sección 4 del protocolo de EVA-01).

Cada heurística se corre con cada punto de su grilla (`agents.baselines.SEARCH`) en modo normal, y
se queda con el de mayor retorno medio por mercado, la métrica principal. Así los baselines se
eligen igual que los agentes: en val, con una búsqueda fija y registrada.
"""

import json
from itertools import product
from pathlib import Path
from typing import Any

import pandas as pd

from ..agents.baselines import SEARCH, TIED, baselines
from ..env.market_env import PolymarketEnv
from .backtest import run_backtest
from .metrics import summarize

PARAMS_FILE = "baselines_params.json"


def grid(name: str) -> list[dict[str, Any]]:
    """Puntos de la grilla de una heurística, con los parámetros atados ya resueltos."""
    space = SEARCH[name]
    points = []
    for values in product(*space.values()):
        point = dict(zip(space, values, strict=True))
        point |= {TIED[key]: point[key] for key in list(point) if key in TIED}
        points.append(point)
    return points


def tune(env: PolymarketEnv) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    """Tabla con cada punto probado y los parámetros elegidos por heurística."""
    stake = env.stake
    rows = []
    for name in SEARCH:
        for point in grid(name):
            policy = baselines(env.costs, params={name: point})[name]()
            summary = summarize(run_backtest(policy, env), env.config.initial_cash, stake)
            rows.append({"policy": name, "params": json.dumps(point), **summary})
    table = pd.DataFrame(rows)
    best = table.loc[table.groupby("policy", sort=False)["mean_return"].idxmax()]
    chosen = {row.policy: json.loads(row.params) for row in best.itertuples()}
    return table, chosen


def write_tuning(table: pd.DataFrame, chosen: dict[str, Any], out: Path) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "baselines_search.csv", index=False)
    (out / PARAMS_FILE).write_text(json.dumps(chosen, indent=2), encoding="utf-8")
    lines = [
        "## Búsqueda de umbrales de los baselines",
        "",
        "Cada punto se corrió en modo normal; se elige el de mayor retorno medio por mercado.",
        "",
        "| Baseline | Parámetros | Retorno medio | Operaciones por mercado | Mercados sin operar |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in table.itertuples():
        mark = " (elegido)" if json.loads(row.params) == chosen[row.policy] else ""
        lines.append(
            f"| {row.policy}{mark} | `{row.params}` | {row.mean_return:.4f} | "
            f"{row.trades_per_market:.2f} | {row.no_trade_share:.2f} |"
        )
    (out / "baselines_search.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ["baselines_search.csv", "baselines_search.md", PARAMS_FILE]
