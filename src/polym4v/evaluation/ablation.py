"""Tabla de la ablación de la recompensa (ENV-08).

Lee los `metrics.json` de una carpeta de modelos, agrupa las semillas por algoritmo y variante de
recompensa, y compara en el split de evaluación el retorno del mejor checkpoint de cada semilla, con
la métrica principal del protocolo (retorno medio por mercado sobre el monto), que no depende de la
recompensa. Las variantes de la etapa A comparten la política óptima (docs/02, sección 2.4), así que
también se reporta la curva de aprendizaje: la diferencia esperada es de velocidad, no de destino.
"""

import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

# `run_id` = <fecha>_<agente>_<recompensa>_s<semilla> (docs/02, sección 5).
RUN_ID = re.compile(r"^\d{8}-\d{6}_(?P<algo>[a-z0-9]+)_(?P<reward>[a-z_]+)_s(?P<seed>\d+)$")
# t de Student bilateral al 95 % por grados de libertad; con más de 9 se usa la normal.
T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262}

COLUMNS = {
    "variant": "Variante",
    "seeds": "Semillas",
    "best_mean": "Retorno del mejor checkpoint",
    "best_std": "DE entre semillas",
    "ci_lower": "IC 95 % inferior",
    "ci_upper": "IC 95 % superior",
    "curve_mean": "Retorno medio de la curva",
    "trades_per_market": "Operaciones por mercado",
    "no_trade_share": "Mercados sin operar",
}


def variant_name(algo: str, reward: dict[str, Any]) -> str:
    """Algoritmo y recompensa, con los parámetros que distinguen una variante de otra."""
    name = reward["name"]
    params = []
    if name in ("pnl_risk", "pnl_hold") and reward.get("base", "pnl") != "pnl":
        params.append(f"base={reward['base']}")
    if name == "pnl_risk":
        params.append(f"λ_dd={reward['lambda_dd']:g}")
    if name == "pnl_hold":
        params.append(f"λ_hold={reward['lambda_hold']:g}")
    if name == "utility":
        params.append(f"a={reward['utility_a']:g}")
    if reward.get("scale", "v0") != "v0":
        params.append(f"scale={reward['scale']}")
    return f"{algo}_{name}" + (f" ({', '.join(params)})" if params else "")


def load_runs(folder: Path, split: str, by_folder: bool = False) -> pd.DataFrame:
    """Una fila por corrida evaluada en `split`, con su variante, semilla y checkpoints.

    Busca en toda la carpeta, así cada etapa o variante puede tener su propia subcarpeta. Con
    `by_folder`, la variante es `<algoritmo>/<carpeta>`, la carpeta de `<carpeta>/<algo>/<run_id>`:
    así se agrupa la búsqueda de hiperparámetros (AGT-09), donde cada punto tiene su carpeta.
    """
    rows = []
    for path in sorted(folder.rglob("metrics.json")):
        metrics = json.loads(path.read_text(encoding="utf-8"))
        match = RUN_ID.match(metrics.get("run_id", ""))
        if match is None or metrics.get("eval_split") != split or not metrics.get("checkpoints"):
            continue
        config = path.parent / "config.yaml"
        reward = (
            yaml.safe_load(config.read_text(encoding="utf-8"))["reward"]
            if config.exists()
            else {"name": match["reward"]}
        )
        variant = (
            f"{match['algo']}/{path.parents[2].name}"
            if by_folder
            else variant_name(match["algo"], reward)
        )
        rows.append(
            {
                "variant": variant,
                "seed": int(match["seed"]),
                "best": metrics["best"],
                "checkpoints": metrics["checkpoints"],
            }
        )
    runs = pd.DataFrame(rows, columns=["variant", "seed", "best", "checkpoints"])
    repeated = runs.duplicated(["variant", "seed"])
    if repeated.any():
        first = runs[repeated].iloc[0]
        raise ValueError(
            f"{first['variant']} tiene más de una corrida con la semilla {first['seed']}"
        )
    return runs


def ablation_table(runs: pd.DataFrame) -> pd.DataFrame:
    """Una fila por variante, ordenadas de mayor a menor retorno del mejor checkpoint."""
    rows = []
    for variant, group in runs.groupby("variant"):
        best = group["best"].map(lambda b: b["mean_return"]).to_numpy(dtype=float)
        curve = [c["mean_return"] for run in group["checkpoints"] for c in run]
        n = len(best)
        mean = float(best.mean())
        std = float(best.std(ddof=1)) if n > 1 else math.nan
        half = T95.get(n - 1, 1.96) * std / math.sqrt(n) if n > 1 else math.nan
        rows.append(
            {
                "variant": variant,
                "seeds": n,
                "best_mean": mean,
                "best_std": std,
                "ci_lower": mean - half,
                "ci_upper": mean + half,
                "curve_mean": float(sum(curve) / len(curve)),
                "trades_per_market": float(
                    group["best"].map(lambda b: b["trades_per_market"]).mean()
                ),
                "no_trade_share": float(group["best"].map(lambda b: b["no_trade_share"]).mean()),
            }
        )
    table = pd.DataFrame(rows, columns=list(COLUMNS))
    return table.sort_values("best_mean", ascending=False, ignore_index=True)


def learning_curves(runs: pd.DataFrame) -> dict[str, pd.Series]:
    """Retorno medio entre semillas de cada checkpoint, por variante."""
    curves = {}
    for variant, group in runs.groupby("variant"):
        points = pd.DataFrame([c for run in group["checkpoints"] for c in run])
        curves[str(variant)] = points.groupby("timesteps")["mean_return"].mean()
    return curves


def plot_curves(curves: dict[str, pd.Series], path: Path) -> None:
    fig = Figure(figsize=(9, 5))
    ax = fig.add_subplot()
    for variant, curve in curves.items():
        ax.plot(curve.index, curve.to_numpy(), marker=".", label=variant)
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.set_xlabel("Pasos de entrenamiento")
    ax.set_ylabel("Retorno medio por mercado sobre el monto (media de las semillas)")
    ax.legend(fontsize="small")
    FigureCanvasAgg(fig)
    fig.savefig(path, dpi=120, bbox_inches="tight")


def _cell(value: Any) -> str:
    if isinstance(value, float):
        return "—" if math.isnan(value) else f"{value:.4f}"
    return str(value)


def ablation_markdown(
    table: pd.DataFrame, split: str, title: str = "Ablación de la recompensa"
) -> str:
    lines = [
        f"## {title} en {split}",
        "",
        "Cada semilla aporta el retorno de su mejor checkpoint en este split. El IC es de la media",
        "entre semillas (t de Student), así que solo mide la variación entre semillas.",
        "",
        "| " + " | ".join(COLUMNS.values()) + " |",
        "| " + " | ".join("---" for _ in COLUMNS) + " |",
    ]
    for _, row in table.iterrows():
        lines.append("| " + " | ".join(_cell(row[c]) for c in COLUMNS) + " |")
    return "\n".join(lines) + "\n"


def build_ablation(
    models: Path,
    split: str,
    out: Path,
    *,
    name: str = "ablation",
    title: str = "Ablación de la recompensa",
    by_folder: bool = False,
) -> dict[str, Any]:
    """Escribe `<name>.csv`, `<name>.md` y `<name>.png` en `out`."""
    runs = load_runs(models, split, by_folder)
    if runs.empty:
        raise FileNotFoundError(f"No hay corridas evaluadas en {split} en {models}")
    table = ablation_table(runs)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / f"{name}.csv", index=False)
    (out / f"{name}.md").write_text(ablation_markdown(table, split, title), encoding="utf-8")
    plot_curves(learning_curves(runs), out / f"{name}.png")
    algos = table["variant"].str.split(r"[_/]", n=1).str[0]
    return {
        "split": split,
        "runs": len(runs),
        "variants": table["variant"].tolist(),
        "best": table["variant"].iloc[0],
        "best_by_algo": table.groupby(algos, sort=False)["variant"].first().to_dict(),
        "files": [f"{name}.csv", f"{name}.md", f"{name}.png"],
    }
