"""Reporte comparativo de un split: tabla y figuras (EVA-05).

Lee lo que ya calcularon otros comandos, sin volver a correr políticas:

- las trayectorias de `backtest` y `evaluate` (`<etiqueta>_<split>[_estricto].parquet`), una por
  baseline o corrida, de las que salen la tabla con las métricas de EVA-03 y las figuras de capital
  y de distribución del retorno;
- los `metrics.json` de las corridas entrenadas, con la evaluación de cada checkpoint, de los que
  salen las curvas de aprendizaje. Solo entran las corridas evaluadas en el mismo split.

Todas las políticas tienen que cubrir los mismos mercados: la comparación es pareada (EVA-01). Los
intervalos de confianza y la prueba del protocolo llegan con EVA-04.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from .backtest import STEP_KEYS, episode_results
from .metrics import capital_curve, summarize

STRICT_SUFFIX = "_estricto"

# Orden y nombre de las columnas de la tabla. La métrica principal va primero.
COLUMNS = {
    "label": "Política",
    "strict": "Estricto",
    "markets": "Mercados",
    "mean_return": "Retorno medio",
    "total_pnl": "PnL total",
    "sharpe": "Sharpe",
    "max_drawdown": "Drawdown máx.",
    "win_rate": "Aciertos",
    "trades_per_market": "Órdenes por mercado",
    "no_trade_share": "Sin operar",
    "fees_paid": "Comisiones",
    "spread_paid": "Spread",
    "invalid_share": "Inválidas",
    "no_price_share": "Sin precio",
    "verified_share": "Verificadas",
}


@dataclass(frozen=True)
class Trajectories:
    """Un archivo de trayectorias: qué política, en qué modo y sus filas."""

    label: str
    strict: bool
    frame: pd.DataFrame


def parse_name(path: Path, split: str) -> tuple[str, bool] | None:
    """Etiqueta y modo de `<etiqueta>_<split>[_estricto].parquet`; None si es de otro split."""
    stem = path.stem
    strict = stem.endswith(STRICT_SUFFIX)
    if strict:
        stem = stem.removesuffix(STRICT_SUFFIX)
    suffix = f"_{split}"
    if not stem.endswith(suffix) or stem == suffix:
        return None
    return stem.removesuffix(suffix), strict


def load_trajectories(folder: Path, split: str) -> list[Trajectories]:
    """Las trayectorias de un split, ordenadas por etiqueta (primero el modo normal)."""
    found = []
    for path in sorted(folder.glob("*.parquet")):
        parsed = parse_name(path, split)
        if parsed is not None:
            label, strict = parsed
            frame = pd.read_parquet(path)
            missing = [key for key in STEP_KEYS if key not in frame.columns]
            if missing:
                raise ValueError(
                    f"{path.name} no tiene {', '.join(missing)}: es de una versión anterior del "
                    "backtest; vuelve a correr backtest o evaluate"
                )
            found.append(Trajectories(label, strict, frame))
    found.sort(key=lambda t: (t.label, t.strict))
    return found


def check_same_markets(items: list[Trajectories]) -> None:
    """Comparación pareada: todas las políticas sobre los mismos mercados y en el mismo orden."""
    reference = None
    for item in items:
        markets = list(pd.unique(item.frame["market_id"]))
        if reference is None:
            reference = (item.label, markets)
        elif markets != reference[1]:
            raise ValueError(
                f"{item.label} no cubre los mismos mercados que {reference[0]}: "
                "las trayectorias son de otro dataset o de otra corrida del split"
            )


def summary_table(items: list[Trajectories], initial_cash: float, stake: float) -> pd.DataFrame:
    """Una fila por archivo con las métricas de EVA-03, de mayor a menor retorno medio."""
    rows = []
    for item in items:
        metrics = summarize(item.frame, initial_cash, stake)
        rows.append({"label": item.label, "strict": item.strict, **metrics})
    table = pd.DataFrame(rows)
    table = table.sort_values(["mean_return", "label"], ascending=[False, True], kind="stable")
    return table.reset_index(drop=True)


def _cell(value: Any) -> str:
    if isinstance(value, bool):
        return "sí" if value else "no"
    if isinstance(value, float):
        return "—" if pd.isna(value) else f"{value:.4f}"
    return str(value)


def to_markdown(table: pd.DataFrame, split: str) -> str:
    """Tabla en Markdown con los nombres de columna en español."""
    columns = [c for c in COLUMNS if c in table.columns]
    lines = [
        f"## Comparación en {split}",
        "",
        "| " + " | ".join(COLUMNS[c] for c in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in table.iterrows():
        lines.append("| " + " | ".join(_cell(row[c]) for c in columns) + " |")
    return "\n".join(lines) + "\n"


def _name(item: Trajectories) -> str:
    return f"{item.label} (estricto)" if item.strict else item.label


def _save(fig: Figure, path: Path) -> None:
    FigureCanvasAgg(fig)
    fig.savefig(path, dpi=120, bbox_inches="tight")


def plot_capital(items: list[Trajectories], initial_cash: float, stake: float, path: Path) -> None:
    """PnL acumulado mercado a mercado, en orden cronológico."""
    fig = Figure(figsize=(9, 5))
    ax = fig.add_subplot()
    for item in items:
        results = episode_results(item.frame, initial_cash, stake)
        curve = capital_curve(results["final_value"] - initial_cash)
        ax.plot(range(1, len(curve) + 1), curve.to_numpy(), label=_name(item))
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.set_xlabel("Mercado (orden cronológico)")
    ax.set_ylabel("PnL acumulado (USDC)")
    ax.legend(fontsize="small")
    _save(fig, path)


def plot_distribution(
    items: list[Trajectories], initial_cash: float, stake: float, path: Path
) -> None:
    """Distribución del retorno por mercado sobre el monto, una caja por política, en orden."""
    fig = Figure(figsize=(9, 1 + 0.5 * len(items)))
    ax = fig.add_subplot()
    returns = [
        episode_results(item.frame, initial_cash, stake)["return_on_stake"].to_numpy()
        for item in items
    ]
    # El triángulo marca la media, que es la métrica principal; la línea, la mediana.
    labels = [_name(item) for item in items]
    ax.boxplot(returns, orientation="horizontal", tick_labels=labels, showmeans=True)
    ax.invert_yaxis()
    ax.axvline(0, color="gray", linewidth=0.8)
    ax.set_xlabel("Retorno por mercado sobre el monto")
    _save(fig, path)


def load_runs(folder: Path, split: str) -> list[dict[str, Any]]:
    """Los `metrics.json` de `models/<algo>/<run_id>/` evaluados en `split`."""
    runs = []
    for path in sorted(folder.glob("*/*/metrics.json")):
        metrics = json.loads(path.read_text(encoding="utf-8"))
        if metrics.get("eval_split") == split and metrics.get("checkpoints"):
            runs.append(metrics)
    return runs


def plot_learning(runs: list[dict[str, Any]], path: Path) -> None:
    """Retorno medio de cada checkpoint, una línea por corrida; el punto marca el elegido."""
    fig = Figure(figsize=(9, 5))
    ax = fig.add_subplot()
    for run in runs:
        points = sorted((c["timesteps"], c["mean_return"]) for c in run["checkpoints"])
        steps, values = zip(*points, strict=True)
        (line,) = ax.plot(steps, values, marker=".", label=run["run_id"])
        best = run["best"]
        ax.plot(best["timesteps"], best["mean_return"], "o", color=line.get_color())
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.set_xlabel("Pasos de entrenamiento")
    ax.set_ylabel("Retorno medio por mercado sobre el monto")
    ax.legend(fontsize="small")
    _save(fig, path)


def build_report(
    split: str,
    trajectories: Path,
    models: Path,
    out: Path,
    initial_cash: float,
    stake: float,
) -> dict[str, Any]:
    """Escribe la tabla (CSV y Markdown) y las figuras de un split en `out`."""
    items = load_trajectories(trajectories, split)
    if not items:
        raise FileNotFoundError(
            f"No hay trayectorias de {split} en {trajectories}: corre antes backtest o evaluate"
        )
    check_same_markets(items)
    out.mkdir(parents=True, exist_ok=True)
    table = summary_table(items, initial_cash, stake)
    table.to_csv(out / "summary.csv", index=False)
    (out / "summary.md").write_text(to_markdown(table, split), encoding="utf-8")
    plot_capital(items, initial_cash, stake, out / "capital.png")
    plot_distribution(items, initial_cash, stake, out / "returns.png")
    files = ["summary.csv", "summary.md", "capital.png", "returns.png"]
    runs = load_runs(models, split)
    if runs:
        plot_learning(runs, out / "learning.png")
        files.append("learning.png")
    return {
        "split": split,
        "policies": [_name(item) for item in items],
        "markets": int(table["markets"].iloc[0]),
        "runs": [run["run_id"] for run in runs],
        "out": str(out),
        "files": files,
    }
