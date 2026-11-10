"""Datos y tokens de la demo (EVA-13): trayectorias, mercados, reportes y colores del DESIGN.md.

No calcula nada nuevo: lee los Parquet de `backtest` y `evaluate`, la muestra de mercados de
`app/muestra.py` (o el dataset, si está en la máquina) y los CSV de `reports/`.
"""

import re
import sys
from pathlib import Path
from typing import Literal

import pandas as pd
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

# En Cloud Run el paquete no se instala, porque arrastraría torch (app/requirements.txt).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from polym4v.agents.base import Action  # noqa: E402
from polym4v.evaluation.backtest import episode_results  # noqa: E402
from polym4v.evaluation.report import STRICT_SUFFIX, parse_name  # noqa: E402
from polym4v.utils.config import DataConfig, SimulatorConfig, load_config  # noqa: E402
from polym4v.utils.paths import get_paths  # noqa: E402

SPLITS = ("train", "val", "test")
SAMPLE = Path(__file__).resolve().parent / "trayectorias"
# Las corridas entrenadas son `<fecha>_<agente>_<recompensa>_s<semilla>`; lo demás, baselines.
AGENT_LABEL = re.compile(r"^\d{8}-\d{6}_")
RUN_LABEL = re.compile(r"^\d{8}-\d{6}_(?P<algo>[a-z]+)_.*_s(?P<seed>\d+)$")

# Tokens de entregas/final/presentacion/DESIGN.md, sección 4.1.
INK, PAPER, SURFACE, LINE = "#0B1220", "#F7F8FA", "#FFFFFF", "#D7DEE8"
TEXT_2, BLUE, GREEN, RED, AMBER = "#5A6472", "#1D4ED8", "#0E7C66", "#B42318", "#E8A317"
BTC = "#3B4558"  # contexto neutro: no compite con la decisión ni con las series
SERIES = {"ppo": BLUE, "dqn": "#7C3AED", "cql": "#0891B2", "bc": "#C2410C"}
BASELINE = "#64748B"

POLICIES = {
    "ppo": (
        "PPO",
        "RL en línea (Stable-Baselines3). Mira el precio, BTC y su cartera, y elige una acción.",
    ),
    "dqn": ("DQN", "RL en línea que estima el valor de cada acción y elige la mejor."),
    "cql": (
        "CQL",
        "RL offline (d3rlpy): aprende de trayectorias grabadas y penaliza lo que no vio.",
    ),
    "bc": ("BC", "Imita las acciones del dataset offline; mide cuánto agrega CQL."),
    "no_trade": ("No operar", "Nunca compra. Es la referencia del protocolo."),
    "fair_value": (
        "Valor justo",
        "Estima la probabilidad con la distancia de BTC a la apertura y compra si la ventaja "
        "supera los costos.",
    ),
    "favorite": ("Favorito", "En el minuto 20 compra el lado favorito y lo mantiene al cierre."),
    "momentum": (
        "Momentum",
        "Sigue el cambio reciente del precio y sale con ganancia o pérdida fija.",
    ),
    "mean_reversion": (
        "Reversión a la media",
        "Apuesta a que el cambio reciente del precio se revierte.",
    ),
    "random": ("Al azar", "Elige acciones al azar."),
}

ACTIONS = {
    Action.WAIT: "esperar",
    Action.BUY_YES: "comprar YES",
    Action.BUY_NO: "comprar NO",
    Action.SELL: "vender",
}
BadgeColor = Literal["red", "orange", "yellow", "blue", "green", "violet", "gray"]
CLASS_COLOR: dict[str, BadgeColor] = {
    "mejor": "green",
    "equivalente": "blue",
    "peor, pero no relevante": "orange",
    "inconcluso": "gray",
    "inferior": "red",
}


def card(name: str) -> DeltaGenerator:
    """Tarjeta del DESIGN.md (9.3): borde, superficie blanca y el alto de su fila.

    La clave `card_*` es la que usa el CSS de `demo.py` para pintar la superficie.
    """
    return st.container(border=True, key=f"card_{name}", height="stretch")


def kind(label: str) -> str:
    """`ppo`, `dqn`, `cql`, `bc` o el nombre del baseline."""
    match = RUN_LABEL.match(label)
    return match["algo"] if match else label


def pretty(label: str) -> str:
    """Nombre para mostrar: `PPO · semilla 0` o el nombre del baseline."""
    match = RUN_LABEL.match(label)
    if match:
        return f"{POLICIES[match['algo']][0]} · semilla {match['seed']}"
    return POLICIES.get(label, (label,))[0]


def color(label: str) -> str:
    return SERIES.get(kind(label), BASELINE)


def file_name(label: str, split: str, strict: bool) -> str:
    return f"{label} · {split}" + (f" · {STRICT_SUFFIX[1:]}" if strict else "")


def split_of(name: str) -> str:
    return name.split(" · ")[1]


def label_of(name: str) -> str:
    return name.split(" · ")[0]


def list_files(folder: Path) -> dict[str, Path]:
    """`etiqueta · split[ · estricto]` → archivo, para los Parquet con nombre de trayectorias."""
    files = {}
    for path in sorted(folder.glob("*.parquet")):
        for split in SPLITS:
            parsed = parse_name(path, split)
            if parsed is not None:
                label, strict = parsed
                files[file_name(label, split, strict)] = path
    return files


def default_folder() -> Path:
    """`reports/trajectories/` si tiene trayectorias; si no, la muestra de la demo publicada."""
    folder = get_paths().reports / "trajectories"
    if not list_files(folder) and list_files(SAMPLE):
        return SAMPLE
    return folder


@st.cache_data(max_entries=64)
def load(path: str, mtime: float) -> pd.DataFrame:
    """Trayectorias de un archivo; `mtime` invalida la caché si el archivo se vuelve a generar."""
    return pd.read_parquet(path)


@st.cache_data(max_entries=64)
def market_pnl(path: str, mtime: float, initial_cash: float, stake: float) -> pd.Series:
    """PnL de cada mercado, en orden cronológico, con la misma cuenta que el reporte."""
    results = episode_results(pd.read_parquet(path), initial_cash, stake)
    return results["final_value"] - initial_cash


@st.cache_data(max_entries=64)
def markets(split: str) -> pd.DataFrame | None:
    """Pregunta, apertura, cierre, BTC por minuto y resultado de cada mercado del split.

    Lee el dataset si está en la máquina y, si no, la muestra de `app/trayectorias/`.
    """
    paths = get_paths()
    sample = SAMPLE / f"mercados_{split}.parquet"
    config = load_config(paths.configs / "data.yaml", DataConfig)
    dataset = paths.processed / config.dataset_id
    if (dataset / "steps.parquet").exists():
        from muestra import market_table

        return market_table(dataset, split)
    if sample.exists():
        return pd.read_parquet(sample)
    return None


def simulator() -> tuple[float, float]:
    """Saldo inicial y monto por operación del simulador."""
    config = load_config(get_paths().configs / "env.yaml", SimulatorConfig)
    return config.env.initial_cash, config.env.initial_cash * config.env.stake_fraction


def report(split: str, name: str) -> pd.DataFrame | None:
    path = get_paths().reports / split / name
    return pd.read_csv(path) if path.exists() else None


def protocol_pick(split: str, options: list[str]) -> list[str]:
    """Mejor agente del protocolo en el split y su baseline, en modo normal, si están disponibles.

    El agente es el grupo con la mayor media de D en `comparison.csv`; se muestra su semilla mediana
    según `summary.csv`, no la mejor, para no elegir una semilla con suerte.
    """
    groups, runs = report(split, "comparison.csv"), report(split, "summary.csv")
    if groups is None or runs is None:
        return []
    groups = groups[~groups["strict"] & (groups["role"] == "principal")]
    if groups.empty:
        return []
    best = groups.sort_values("mean", ascending=False).iloc[0]
    runs = runs[~runs["strict"]]
    pattern = AGENT_LABEL.pattern + re.escape(best["group"]) + r"_s\d+"
    seeds = runs[runs["label"].str.fullmatch(pattern)]
    picked = [file_name(best["baseline"], split, False)]
    if len(seeds):
        median = seeds.sort_values("mean_return")["label"].iloc[(len(seeds) - 1) // 2]
        picked.insert(0, file_name(median, split, False))
    return [name for name in picked if name in options]


def first_traded(by_market: dict[str, pd.DataFrame]) -> int:
    """Posición del primer mercado con alguna orden ejecutada; 0 si no operó en ninguno."""
    for position, steps in enumerate(by_market.values()):
        if (steps["order_status"] == "ejecutada").any():
            return position
    return 0
