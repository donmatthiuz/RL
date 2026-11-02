"""Análisis exploratorio del comportamiento de los agentes (EVA-12).

No forma parte del protocolo de EVA-01: no elige agentes ni cambia la conclusión de test. Describe
qué aprendió cada agente: cuándo y a qué precio compra, cuánto gana o pierde con eso, si el precio
del mercado ya cubre lo que aprovecha y qué features mueven sus decisiones. Lo nuevo se calcula en
val; en test solo se describen las trayectorias que ya dejó EVA-06, sin volver a correr políticas.
"""

import math
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from ..agents.base import Action, Policy
from ..env.execution import buy
from ..env.market_data import MarketData
from ..env.market_env import PolymarketEnv
from ..features.market import MARKET_FEATURES
from ..utils.config import CostConfig, EnvConfig, ExperimentConfig, load_config
from .backtest import run_backtest
from .comparison import AGENT_LABEL, NO_TRADE, agent_groups
from .report import load_trajectories

BUYS = (Action.BUY_YES, Action.BUY_NO)
POS_SIDE = len(MARKET_FEATURES)  # primera feature del estado del agente (S3)
# Precio del lado comprado al ejecutarse la orden; el último tramo es el de "casi decidido".
PRICE_BINS = (0.0, 0.5, 0.8, 0.95, 0.98, 1.0)
SURE = 0.98
SURE_TEXT = f"{SURE:g}".replace(".", ",")
# Mapa de decisiones: minuto del mercado y precio del favorito.
MINUTE_BINS = (0, 10, 20, 30, 40, 45, 50, 55, 58)
FAVORITE_BINS = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99, 1.0)
# Calibración: un mercado por fila en cada minuto.
CALIBRATION_MINUTES = (50, 55)
CALIBRATION_BINS = (0.5, 0.8, 0.95, 0.98, 0.99, 1.0)
# Grupos que se permutan juntos: dentro de cada uno, las features están muy relacionadas. `edge` y
# `edge_tp` mezclan el spot y el precio (`p_fair - p_yes`), así que van aparte.
GROUPS = {
    "precio de Polymarket": ("p_yes", "dp_1", "dp_5", "p_stale"),
    "spot de Binance": ("x", "r_1", "r_5", "sigma", "z", "p_fair"),
    "ventaja (spot contra precio)": ("edge", "edge_tp"),
    "tiempo restante": ("tau",),
}

ACTIVITY = {
    "policy": "Política",
    "seeds": "Semillas",
    "trades": "Operaciones",
    "trades_per_market": "Por mercado",
    "median_minute": "Minuto mediano de compra",
    "favorite_share": "Compra el favorito",
    "sure_share": f"Precio > {SURE}",
    "sold_share": "Vendidas antes del final",
    "side_won": "Lado acertado",
    "profit_share": "Con ganancia",
    "pnl": "PnL total (USDC)",
    "verified_share": "Verificadas",
}
PAYOFF = {
    "policy": "Agente",
    "price": "Precio del lado comprado",
    "trades": "Operaciones",
    "side_won": "Lado acertado",
    "won_lower": "IC 95 % inferior",
    "won_upper": "IC 95 % superior",
    "profit_share": "Con ganancia",
    "mean_gain": "Ganancia media (USDC)",
    "mean_loss": "Pérdida media (USDC)",
    "gains_per_loss": "Ganancias por pérdida",
    "net": "Neto (USDC)",
    "cost": "Costo por acción",
}
CALIBRATION = {
    "minute": "Minuto",
    "price": "Precio del favorito",
    "markets": "Mercados",
    "mean_price": "Precio medio",
    "won": "Acierto del favorito",
    "lower": "IC 95 % inferior",
    "upper": "IC 95 % superior",
    "cost": "Costo por acción",
    "edge": "Ventaja neta",
}
LOSSES = {
    "policy": "Agente",
    "seed": "Semilla",
    "market": "Mercado",
    "k": "Minuto de compra",
    "side": "Lado",
    "price": "Precio",
    "exit": "Salida",
    "pnl": "PnL (USDC)",
    "btc_entry": "BTC contra la apertura al comprar",
    "btc_last": "BTC contra la apertura al final",
    "min_price": "Precio mínimo del lado después de comprar",
}


def _labels(edges: Sequence[float]) -> list[str]:
    return [f"{a:g}-{b:g}" for a, b in zip(edges[:-1], edges[1:], strict=False)]


def _bins(values: pd.Series, edges: Sequence[float], right: bool = True) -> pd.Series:
    """Tramos con etiquetas `a-b`; el primero incluye su borde izquierdo."""
    labels = (
        _labels(edges)
        if right
        else [f"{a}-{b - 1}" for a, b in zip(edges[:-1], edges[1:], strict=False)]
    )
    return pd.cut(values, edges, labels=labels, include_lowest=right, right=right)


def trades(frame: pd.DataFrame, outcomes: Mapping[str, int], initial_cash: float) -> pd.DataFrame:
    """Una fila por operación de una trayectoria: de la compra a la venta o a la liquidación.

    `price` es el precio del lado comprado al ejecutarse, sin costos; `paid`, el precio por acción
    con medio spread, y `cost`, lo mismo con la comisión: el acierto que hace falta para no perder
    si se mantiene hasta el final, porque la acción ganadora paga 1. `pnl` es el cambio del valor
    de la cartera entre antes de comprar y el cierre; sin posición, el valor es la caja, así que la
    suma de las operaciones es el PnL total.
    """
    f = frame.reset_index(drop=True)
    executed = f["order_status"].eq("ejecutada")
    sold = executed & f["action_executed"].eq(Action.SELL)
    opens = np.flatnonzero(executed & f["action_executed"].isin(BUYS))
    closes = np.flatnonzero(sold | f["done"].astype(bool))
    close = closes[np.searchsorted(closes, opens)]
    before = f.groupby("market_id", sort=False)["portfolio_value"].shift(fill_value=initial_cash)
    o, c = f.iloc[opens], f.iloc[close]
    yes = o["action_executed"].eq(Action.BUY_YES).to_numpy()
    outcome = o["market_id"].map(outcomes).to_numpy()
    shares = o["fill_shares"].to_numpy(dtype=float)
    return pd.DataFrame(
        {
            "market_id": o["market_id"].to_numpy(),
            "k": o["k"].to_numpy(),
            "side": np.where(yes, "YES", "NO"),
            "price": np.where(yes, o["exec_p"], 1.0 - o["exec_p"]),
            "paid": o["fill_price"].to_numpy(dtype=float),
            "cost": (shares * o["fill_price"].to_numpy(dtype=float) + o["fee"].to_numpy()) / shares,
            "favorite": np.where(yes, o["p_yes"] > 0.5, o["p_yes"] < 0.5),
            "side_won": np.where(yes, outcome == 1, outcome == 0),
            "sold": sold.iloc[close].to_numpy(),
            "exit_k": c["k"].to_numpy(),
            "pnl": c["portfolio_value"].to_numpy() - before.iloc[opens].to_numpy(),
            "verified": o["exec_verified"].eq(True).to_numpy(),
        }
    )


def policy_frames(
    folder: Path, split: str
) -> tuple[dict[str, list[pd.DataFrame]], dict[str, list[pd.DataFrame]]]:
    """Trayectorias en modo normal: las semillas de cada agente y, aparte, cada baseline.

    `no_trade` queda fuera porque no opera.
    """
    found = {(t.label, t.strict): t.frame for t in load_trajectories(folder, split)}
    if not found:
        raise FileNotFoundError(f"No hay trayectorias de {split} en {folder}")
    agents = agent_groups(found, strict=False)
    baselines = {
        label: [frame]
        for (label, strict), frame in found.items()
        if not strict and label != NO_TRADE and AGENT_LABEL.match(label) is None
    }
    return agents, baselines


def agent_runs(folder: Path, split: str, models: Path) -> dict[str, list[Path]]:
    """La carpeta de cada corrida con trayectorias de `split`, por agente y en orden de semilla."""
    runs: dict[str, dict[int, Path]] = {}
    for path in sorted(folder.glob(f"*_{split}.parquet")):
        label = path.stem.removesuffix(f"_{split}")
        match = AGENT_LABEL.match(label)
        if match is None:
            continue
        found = [p for p in models.rglob(label) if (p / "config.yaml").exists()]
        if len(found) != 1:
            raise FileNotFoundError(f"No hay una sola corrida {label} en {models}")
        runs.setdefault(match["group"], {})[int(match["seed"])] = found[0]
    return {group: [by_seed[s] for s in sorted(by_seed)] for group, by_seed in sorted(runs.items())}


def policy_trades(
    frames: Sequence[pd.DataFrame], outcomes: Mapping[str, int], initial_cash: float
) -> pd.DataFrame:
    """Las operaciones de todas las semillas de una política, con la semilla en orden."""
    parts = [trades(frame, outcomes, initial_cash).assign(seed=i) for i, frame in enumerate(frames)]
    return pd.concat(parts, ignore_index=True)


def _share(mask: pd.Series) -> float:
    return float(mask.mean()) if len(mask) else math.nan


def activity_table(
    frames: Mapping[str, Sequence[pd.DataFrame]],
    by_policy: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    """Una fila por política: cuánto opera, cuándo, a qué precio y con qué resultado."""
    rows = []
    for policy, t in by_policy.items():
        seeds = len(frames[policy])
        markets = frames[policy][0]["market_id"].nunique()
        rows.append(
            {
                "policy": policy,
                "seeds": seeds,
                "trades": len(t),
                "trades_per_market": len(t) / (markets * seeds),
                "median_minute": float(t["k"].median()) if len(t) else math.nan,
                "favorite_share": _share(t["favorite"]),
                "sure_share": _share(t["price"] > SURE),
                "sold_share": _share(t["sold"]),
                "side_won": _share(t["side_won"]),
                "profit_share": _share(t["pnl"] > 0),
                "pnl": float(t["pnl"].sum()),
                "verified_share": _share(t["verified"]),
            }
        )
    return pd.DataFrame(rows, columns=list(ACTIVITY))


def payoff_table(by_policy: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Por agente y tramo de precio: qué tan seguido acierta y cuánto gana o pierde al hacerlo."""
    rows = []
    for policy, t in by_policy.items():
        for interval, group in t.groupby(_bins(t["price"], PRICE_BINS), observed=True):
            gains, losses = group["pnl"][group["pnl"] > 0], group["pnl"][group["pnl"] < 0]
            mean_gain = float(gains.mean()) if len(gains) else math.nan
            mean_loss = float(losses.mean()) if len(losses) else math.nan
            lower, upper = wilson(int(group["side_won"].sum()), len(group))
            rows.append(
                {
                    "policy": policy,
                    "price": str(interval),
                    "trades": len(group),
                    "side_won": float(group["side_won"].mean()),
                    "won_lower": lower,
                    "won_upper": upper,
                    "profit_share": float((group["pnl"] > 0).mean()),
                    "mean_gain": mean_gain,
                    "mean_loss": mean_loss,
                    "gains_per_loss": -mean_loss / mean_gain if mean_gain > 0 else math.nan,
                    "net": float(group["pnl"].sum()),
                    "cost": float(group["cost"].mean()),
                }
            )
    return pd.DataFrame(rows, columns=list(PAYOFF))


def decision_map(frames: Sequence[pd.DataFrame], no_open_last: int) -> pd.DataFrame:
    """Proporción de estados en que la política pidió comprar, por precio del favorito y minuto.

    Solo cuentan los estados en que podía comprar: sin posición y antes de los últimos
    `no_open_last` minutos (S10). Se usa la acción pedida, no la ejecutada: es la decisión.
    """
    parts = []
    for frame in frames:
        flat = frame.groupby("market_id", sort=False)["position_side"].shift(fill_value=0).eq(0)
        n_steps = int(frame["k"].max()) + 1
        can = flat & (frame["k"] < n_steps - no_open_last)
        parts.append(frame.loc[can, ["k", "p_yes", "action"]])
    states = pd.concat(parts, ignore_index=True)
    favorite = np.maximum(states["p_yes"], 1.0 - states["p_yes"])
    minute = _bins(states["k"], MINUTE_BINS, right=False)
    price = _bins(favorite, FAVORITE_BINS)
    bought = states["action"].isin(BUYS)
    return bought.groupby([price, minute], observed=False).mean().unstack()


def plot_decision_maps(maps: Mapping[str, pd.DataFrame], path: Path) -> None:
    """Un mapa por agente, cada uno con su escala: los niveles de compra son muy distintos."""
    n = len(maps)
    cols = min(n, 2)
    rows = math.ceil(n / cols)
    fig = Figure(figsize=(6.5 * cols, 4.5 * rows), layout="constrained")
    for i, (policy, table) in enumerate(maps.items(), start=1):
        ax = fig.add_subplot(rows, cols, i)
        values = table.to_numpy(dtype=float)
        top = float(np.nanmax(values)) if np.isfinite(values).any() else 0.0
        top = top or 1.0
        image = ax.imshow(values, origin="lower", aspect="auto", cmap="viridis", vmin=0, vmax=top)
        for (r, c), value in np.ndenumerate(values):
            if not np.isnan(value) and value > 0:
                color = "black" if value > top / 2 else "white"
                ax.text(c, r, f"{value:.1%}", ha="center", va="center", fontsize=6, color=color)
        ax.set_xticks(range(len(table.columns)), list(table.columns))
        ax.set_yticks(range(len(table.index)), list(table.index))
        ax.tick_params(axis="x", labelsize=7, rotation=45)
        ax.tick_params(axis="y", labelsize=7)
        ax.set_title(policy, fontsize=10)
        ax.set_xlabel("Minuto del mercado")
        ax.set_ylabel("Precio del favorito")
        fig.colorbar(image, ax=ax, label="Pide comprar", format="{x:.1%}")
    _save(fig, path)


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de Wilson para una proporción; con 0 o n éxitos no se sale de [0, 1]."""
    if n == 0:
        return math.nan, math.nan
    p = successes / n
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(center - half, 0.0), min(center + half, 1.0)


def cost_per_share(p: float, costs: CostConfig) -> float:
    """Lo que cuesta cada acción comprada a precio `p`, con medio spread y comisión."""
    fill = buy(1.0, p, costs)
    return -fill.cash / fill.shares


def calibration_table(
    frame: pd.DataFrame, outcomes: Mapping[str, int], costs: CostConfig
) -> pd.DataFrame:
    """Qué tan seguido gana el favorito según su precio en un minuto, y lo que cuesta comprarlo.

    `frame` es cualquier trayectoria del split: el precio de cada paso no depende de la política.
    `edge = won - cost` es lo que se espera ganar por acción comprando el favorito a ese precio y
    manteniendo hasta el final, si el acierto observado fuera el verdadero.
    """
    rows = []
    for minute in CALIBRATION_MINUTES:
        step = frame[frame["k"] == minute]
        favorite = np.maximum(step["p_yes"], 1.0 - step["p_yes"])
        outcome = step["market_id"].map(outcomes)
        won = np.where(step["p_yes"] >= 0.5, outcome == 1, outcome == 0)
        bins = _bins(favorite, CALIBRATION_BINS)
        data = pd.DataFrame({"price": favorite.to_numpy(), "won": won, "bin": bins.to_numpy()})
        for interval, group in data.groupby("bin", observed=True):
            n, wins = len(group), int(group["won"].sum())
            lower, upper = wilson(wins, n)
            cost = float(np.mean([cost_per_share(p, costs) for p in group["price"]]))
            rows.append(
                {
                    "minute": minute,
                    "price": str(interval),
                    "markets": n,
                    "mean_price": float(group["price"].mean()),
                    "won": wins / n,
                    "lower": lower,
                    "upper": upper,
                    "cost": cost,
                    "edge": wins / n - cost,
                }
            )
    return pd.DataFrame(rows, columns=list(CALIBRATION))


class StateRecorder:
    """Pasa cada decisión a la política y guarda la observación que recibió."""

    def __init__(self, policy: Policy) -> None:
        self.policy, self.name = policy, policy.name
        self.states: list[np.ndarray] = []

    def act(self, obs: np.ndarray, info: Mapping[str, Any] | None = None) -> int:
        self.states.append(obs)
        return self.policy.act(obs, info)

    def reset(self) -> None:
        self.policy.reset()


def collect_states(policy: Policy, env: PolymarketEnv) -> tuple[np.ndarray, pd.DataFrame]:
    """Corre la política en todos los mercados del entorno y devuelve cada estado que visitó."""
    recorder = StateRecorder(policy)
    frame = run_backtest(recorder, env)
    return np.stack(recorder.states), frame


def effective(actions: np.ndarray, flat: np.ndarray, can_open: np.ndarray) -> np.ndarray:
    """La decisión que ejecutaría el entorno: una acción inválida queda en WAIT (S6)."""
    valid = (np.isin(actions, BUYS) & can_open) | ((actions == Action.SELL) & ~flat)
    return np.where(valid, actions, Action.WAIT)


def feature_columns() -> dict[str, list[int]]:
    """Columnas que se permutan juntas: los grupos y luego cada feature de mercado sola."""
    index = {name: i for i, name in enumerate(MARKET_FEATURES)}
    columns = {name: [index[f] for f in features] for name, features in GROUPS.items()}
    return columns | {name: [i] for name, i in index.items()}


def permutation_importance(
    predict: Callable[[np.ndarray], np.ndarray],
    states: np.ndarray,
    can_open: np.ndarray,
    *,
    repeats: int = 3,
    seed: int = 0,
) -> pd.DataFrame:
    """Cuánto cambian las decisiones al desordenar cada grupo de features entre los estados.

    Las columnas de un grupo se permutan juntas, con la misma permutación de filas, y la decisión
    se compara con la original. `changed` es la proporción de compras originales que cambian
    (dejan de comprar o cambian de lado) y `new_buys`, las compras que aparecen en estados donde no
    compraba, por cada compra original. Mide qué información usa la política, no si esa
    información predice.
    """
    flat = states[:, POS_SIDE] == 0
    base = effective(predict(states), flat, can_open)
    bought = np.isin(base, BUYS)
    idle = ~bought & can_open
    rng = np.random.default_rng(seed)
    rows = []
    for name, idx in feature_columns().items():
        changed, new = [], []
        for _ in range(repeats):
            shuffled = states.copy()
            shuffled[:, idx] = states[rng.permutation(len(states))][:, idx]
            decision = effective(predict(shuffled), flat, can_open)
            changed.append(np.mean(decision[bought] != base[bought]) if bought.any() else math.nan)
            new.append(int(np.isin(decision[idle], BUYS).sum()) / max(int(bought.sum()), 1))
        rows.append(
            {
                "feature": name,
                "group": name in GROUPS,
                "buys": int(bought.sum()),
                "changed": float(np.mean(changed)),
                "new_buys": float(np.mean(new)),
            }
        )
    return pd.DataFrame(rows)


def can_open_mask(states: np.ndarray, frame: pd.DataFrame, no_open_last: int) -> np.ndarray:
    """Estados sin posición y antes de los últimos `no_open_last` minutos (S10)."""
    n_steps = int(frame["k"].max()) + 1
    return (states[:, POS_SIDE] == 0) & (frame["k"].to_numpy() < n_steps - no_open_last)


def importance_summary(per_seed: Mapping[str, Sequence[pd.DataFrame]]) -> pd.DataFrame:
    """Media y desviación entre semillas de la importancia de cada feature, por agente."""
    rows = []
    for policy, tables in per_seed.items():
        joined = pd.concat([t.assign(seed=i) for i, t in enumerate(tables)])
        for feature, group in joined.groupby("feature", sort=False):
            rows.append(
                {
                    "policy": policy,
                    "feature": feature,
                    "group": bool(group["group"].iloc[0]),
                    "buys": int(group["buys"].sum()),
                    "changed": float(group["changed"].mean()),
                    "changed_sd": float(group["changed"].std(ddof=1)) if len(group) > 1 else 0.0,
                    "new_buys": float(group["new_buys"].mean()),
                    "new_buys_sd": float(group["new_buys"].std(ddof=1)) if len(group) > 1 else 0.0,
                }
            )
    return pd.DataFrame(rows)


def plot_importance(summary: pd.DataFrame, path: Path) -> None:
    features = summary[~summary["group"]]
    policies = list(dict.fromkeys(features["policy"]))
    fig = Figure(figsize=(5 * len(policies), 5), layout="constrained")
    for i, policy in enumerate(policies, start=1):
        ax = fig.add_subplot(1, len(policies), i)
        rows = features[features["policy"] == policy].sort_values("changed")
        ax.barh(rows["feature"], rows["changed"], xerr=rows["changed_sd"], color="tab:blue")
        ax.set_xlim(0, 1)
        ax.set_title(policy, fontsize=10)
        ax.set_xlabel("Compras que cambian al desordenar la feature")
    _save(fig, path)


def loss_details(
    by_policy: Mapping[str, pd.DataFrame], steps: pd.DataFrame, *, threshold: float = -1.0
) -> pd.DataFrame:
    """Las compras a más de `SURE` que perdieron más de `-threshold` USDC, con el recorrido de BTC.

    `steps` trae `market_id`, `k`, `p_yes` y `x` (logaritmo del spot sobre el de la apertura) sin
    normalizar, como queda en `steps.parquet`.
    """
    path = steps.set_index(["market_id", "k"]).sort_index()
    rows = []
    for policy, t in by_policy.items():
        for trade in t[(t["price"] > SURE) & (t["pnl"] < threshold)].itertuples():
            market = path.loc[trade.market_id]
            held = market.loc[trade.k : trade.exit_k, "p_yes"]
            side = held if trade.side == "YES" else 1.0 - held
            rows.append(
                {
                    "policy": policy,
                    "seed": trade.seed,
                    "market": str(trade.market_id)[:10],
                    "k": trade.k,
                    "side": trade.side,
                    "price": trade.price,
                    "exit": f"venta en {trade.exit_k}" if trade.sold else "liquidación",
                    "pnl": trade.pnl,
                    "btc_entry": math.expm1(market.loc[trade.k, "x"]),
                    "btc_last": math.expm1(market["x"].iloc[-1]),
                    "min_price": float(side.min()),
                }
            )
    return pd.DataFrame(rows, columns=list(LOSSES))


def _cell(value: Any, column: str = "") -> str:
    if isinstance(value, bool | np.bool_):
        return "sí" if value else "no"
    if isinstance(value, float | np.floating):
        if math.isnan(value):
            return "—"
        if column.startswith("btc_"):
            return f"{value:+.3%}"
        if column in ("pnl", "net", "mean_gain", "mean_loss"):
            return f"{value:.2f}"
        if column == "median_minute":
            return f"{value:.0f}"
        if column == "gains_per_loss":
            return f"{value:.1f}"
        return f"{value:.4f}"
    return str(value)


def to_markdown(table: pd.DataFrame, columns: Mapping[str, str]) -> str:
    lines = [
        "| " + " | ".join(columns.values()) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in table.iterrows():
        lines.append("| " + " | ".join(_cell(row[c], c) for c in columns) + " |")
    return "\n".join(lines) + "\n"


def importance_markdown(summary: pd.DataFrame, column: str) -> str:
    """Grupos en filas y agentes en columnas, con la media ± la desviación entre semillas."""
    groups = summary[summary["group"]]
    policies = list(dict.fromkeys(groups["policy"]))
    lines = [
        "| Grupo | " + " | ".join(policies) + " |",
        "| --- | " + " | ".join("---" for _ in policies) + " |",
    ]
    for feature in GROUPS:
        cells = []
        for policy in policies:
            row = groups[(groups["policy"] == policy) & (groups["feature"] == feature)].iloc[0]
            cells.append(f"{row[column]:.3f} ± {row[column + '_sd']:.3f}")
        lines.append(f"| {feature} | " + " | ".join(cells) + " |")
    buys = [str(int(groups[groups["policy"] == p]["buys"].iloc[0])) for p in policies]
    lines.append("| Compras originales | " + " | ".join(buys) + " |")
    return "\n".join(lines) + "\n"


def _save(fig: Figure, path: Path) -> None:
    FigureCanvasAgg(fig)
    fig.savefig(path, dpi=120, bbox_inches="tight")


def run_importance(
    runs: Mapping[str, Sequence[Path]], data: MarketData, *, repeats: int = 3
) -> tuple[pd.DataFrame, float]:
    """Importancia por permutación de cada agente, semilla por semilla, en los mercados de `data`.

    Devuelve también la menor coincidencia entre las acciones por lotes y las del backtest paso a
    paso: si no es 1, las permutaciones no miden la misma política que se evaluó.
    """
    from ..agents.adapters import load_policy

    per_seed: dict[str, list[pd.DataFrame]] = {}
    agreement = 1.0
    for group, dirs in runs.items():
        tables = []
        for run in dirs:
            config = load_config(run / "config.yaml", ExperimentConfig)
            policy = load_policy(run, config.agent.algo)
            states, frame = collect_states(policy, PolymarketEnv(data, config.env, config.reward))
            actions = frame["action"].to_numpy()
            agreement = min(agreement, float(np.mean(policy.act_batch(states) == actions)))
            can_open = can_open_mask(states, frame, config.env.no_open_last_minutes)
            tables.append(
                permutation_importance(policy.act_batch, states, can_open, repeats=repeats)
            )
        per_seed[group] = tables
    return importance_summary(per_seed), agreement


VAL_INTRO = """\
Análisis exploratorio (EVA-12), fuera del protocolo de EVA-01: describe qué aprendió cada agente; no
decide cuál es mejor ni cambia la conclusión de test. Usa las trayectorias de val en modo normal:
las semillas de cada agente final y los baselines con sus umbrales de val. Val se usó para elegir
checkpoints e hiperparámetros, así que lo que se ve aquí puede ser mejor que lo que el agente
generaliza.
"""
TEST_INTRO = """\
Descripción de las trayectorias que dejó la evaluación final en test (EVA-06), sin volver a correr
ninguna política ni cambiar ningún modelo (EVA-12). No es una prueba nueva ni cambia la conclusión
de test, que es la de [comparison.md](comparison.md).
"""
ACTIVITY_NOTES = """\
- Una operación va de la compra a la venta o a la liquidación al final del mercado; su PnL es el
  cambio del valor de la cartera en ese tramo, después de costos, y suma las semillas.
- Lado acertado: el lado comprado fue el ganador. Con ganancia: la operación terminó con PnL
  positivo; una venta antes del final puede perder aunque el lado gane.
- Verificadas: ejecuciones respaldadas por trades reales (EVA-11).
"""
MAP_NOTES = """\
Entre los estados en que la política no tenía posición y podía comprar, la proporción en que pidió
comprar, por minuto del mercado y precio del favorito (el lado con precio mayor a 0,5), sumando las
semillas. Cada mapa tiene su escala. No dice qué lado compra: eso está en "Compra el favorito".
"""
PAYOFF_NOTES = """\
- Precio del lado comprado: al ejecutarse la orden, sin costos.
- Costo por acción: lo pagado por cada acción, con medio spread y comisión. La acción ganadora paga
  1, así que manteniendo hasta el final hay que acertar al menos esa proporción para no perder.
- Ganancias por pérdida: cuántas ganancias medias hacen falta para cubrir una pérdida media.
- IC de Wilson al 95 % del lado acertado. Las semillas operan en los mismos mercados, así que las
  operaciones no son independientes y el intervalo es optimista.
"""
CALIBRATION_NOTES = """\
- Un mercado por fila: el precio del favorito en ese minuto y si ganó.
- IC de Wilson al 95 %. Los mercados de un mismo día no son independientes, así que el intervalo es
  optimista.
- Ventaja neta = acierto − costo por acción: lo que se esperaría ganar por acción comprando el
  favorito a ese precio y manteniendo hasta el final. Positiva quiere decir que el precio
  subestima al favorito más de lo que cuestan el spread y la comisión.
- Es evidencia limitada: un solo período, dos minutos y tramos de precio gruesos.
"""
IMPORTANCE_NOTES = """\
- Cada agente se vuelve a correr en val para guardar los estados que visitó; las acciones por lotes
  coinciden con las del backtest en el {agreement:.2%} de los pasos, como mínimo. Luego se
  desordenan las columnas de un grupo entre los estados, todas con la misma permutación, y se
  compara la decisión con la original. Las acciones inválidas cuentan como WAIT, igual que en el
  entorno.
- Mide qué información usa la política, no si esa información predice el resultado ni si el agente
  gana con ella.
- No es SHAP ni Integrated Gradients: no reparte una decisión entre las features ni explica un
  estado puntual. Desordenar crea estados que no existen (por ejemplo, un `z` alto con BTC en la
  apertura); por eso las features muy relacionadas se desordenan en grupo, y la figura de features
  sueltas subestima las que tienen un sustituto en otra columna.
- Con pocas compras originales, las proporciones son ruidosas.
"""
LOSS_NOTES = f"""\
- Compras a más de {SURE_TEXT} que perdieron más de 1 USDC.
- BTC contra la apertura: variación del spot de Binance respecto del de la apertura del mercado, al
  comprar y en el último paso. El mercado se resuelve UP si BTC cierra por encima de la apertura.
- Precio mínimo del lado: el más bajo que tuvo el lado comprado en los pasos de la grilla, de
  minuto en minuto, mientras se mantuvo la posición. Una venta se ejecuta al precio siguiente, así
  que puede ser mucho peor.
"""


def build_behavior(
    split: str,
    folder: Path,
    out: Path,
    outcomes: Mapping[str, int],
    env: EnvConfig,
    *,
    importance: tuple[pd.DataFrame, float] | None = None,
    steps: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Escribe el análisis de val (`behavior.*`) o la inspección de test (`inspection.*`) en `out`.

    `importance` es la salida de `run_importance` (solo val) y `steps`, el `steps.parquet` sin
    normalizar de los mercados de test, para describir las pérdidas grandes.
    """
    agents, baselines = policy_frames(folder, split)
    frames = agents | baselines
    by_policy = {p: policy_trades(f, outcomes, env.initial_cash) for p, f in frames.items()}
    activity = activity_table(frames, by_policy)
    payoff = payoff_table({p: by_policy[p] for p in agents})
    name = "behavior" if split == "val" else "inspection"
    out.mkdir(parents=True, exist_ok=True)
    files = [f"{name}.md", f"{name}_activity.csv", f"{name}_payoff.csv"]
    activity.to_csv(out / files[1], index=False)
    payoff.to_csv(out / files[2], index=False)
    if split == "val":
        title = "Comportamiento de los agentes en val"
        intro = VAL_INTRO
    else:
        title = "Inspección posterior de test"
        intro = TEST_INTRO
    lines = [f"# {title}", "", intro, "## Qué hace cada política", ""]
    lines += [to_markdown(activity, ACTIVITY), ACTIVITY_NOTES]
    if split == "val":
        maps = {p: decision_map(agents[p], env.no_open_last_minutes) for p in agents}
        plot_decision_maps(maps, out / f"{name}_map.png")
        files.append(f"{name}_map.png")
        lines += [f"![Decisiones de compra]({name}_map.png)", "", MAP_NOTES]
    lines += ["## Precisión contra rentabilidad", "", to_markdown(payoff, PAYOFF), PAYOFF_NOTES]
    if split == "val":
        reference = next(iter(frames.values()))[0]
        calibration = calibration_table(reference, outcomes, env.costs)
        calibration.to_csv(out / f"{name}_calibration.csv", index=False)
        files.append(f"{name}_calibration.csv")
        lines += ["## Calibración del precio del favorito", ""]
        lines += [to_markdown(calibration, CALIBRATION), CALIBRATION_NOTES]
    if importance is not None:
        summary, agreement = importance
        summary.to_csv(out / f"{name}_importance.csv", index=False)
        plot_importance(summary, out / f"{name}_importance.png")
        files += [f"{name}_importance.csv", f"{name}_importance.png"]
        lines += ["## Qué información usa cada agente", ""]
        lines += ["Compras que cambian al desordenar cada grupo de features (media ± desviación"]
        lines += ["entre semillas):", ""]
        lines += [importance_markdown(summary, "changed")]
        lines += ["Compras nuevas por cada compra original:", ""]
        lines += [importance_markdown(summary, "new_buys")]
        lines += [f"![Importancia de cada feature]({name}_importance.png)", ""]
        lines += [IMPORTANCE_NOTES.format(agreement=agreement)]
    if steps is not None:
        losses = loss_details({p: by_policy[p] for p in agents}, steps)
        losses.to_csv(out / f"{name}_losses.csv", index=False)
        files.append(f"{name}_losses.csv")
        lines += [f"## Pérdidas grandes en compras a más de {SURE_TEXT}", ""]
        lines += [to_markdown(losses, LOSSES), LOSS_NOTES]
    (out / files[0]).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"split": split, "policies": list(frames), "files": files}
