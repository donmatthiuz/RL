"""Demo de PolyRL (EVA-07 y EVA-08): reproduce y compara trayectorias de `backtest` y `evaluate`.

Lee los Parquet de `reports/trajectories/` (o de la carpeta que se elija), así que no necesita GPU
ni red. Muestra un mercado a la vez: el precio YES con las compras y ventas, el valor de la cartera
y el estado del paso elegido. Además compara otras políticas del mismo split en ese mercado y en el
PnL acumulado; si existe el reporte del split, propone al mejor agente y al mejor baseline. Es
funcional; el diseño visual se define al final del proyecto.

Correr con `make demo`.
"""

import re
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from matplotlib.figure import Figure

from polym4v.agents.base import Action
from polym4v.env.reward import COMPONENTS
from polym4v.evaluation.backtest import episode_results
from polym4v.evaluation.metrics import capital_curve
from polym4v.evaluation.report import STRICT_SUFFIX, parse_name
from polym4v.utils.config import SimulatorConfig, load_config
from polym4v.utils.paths import get_paths

SPLITS = ("train", "val", "test")
SIDES = {1: "YES", -1: "NO", 0: "sin posición"}
PLAY_PAUSE_S = 0.4
# Las corridas entrenadas son `<fecha>_<agente>_<recompensa>_s<semilla>`; lo demás, baselines.
AGENT_LABEL = re.compile(r"^\d{8}-\d{6}_")


def file_name(label: str, split: str, strict: bool) -> str:
    return f"{label} · {split}" + (f" · {STRICT_SUFFIX[1:]}" if strict else "")


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


@st.cache_data
def load(path: str, mtime: float) -> pd.DataFrame:
    """Trayectorias de un archivo; `mtime` invalida la caché si el archivo se vuelve a generar."""
    return pd.read_parquet(path)


@st.cache_data
def market_pnl(path: str, mtime: float, initial_cash: float, stake: float) -> pd.Series:
    """PnL de cada mercado, en orden cronológico, con la misma cuenta que el reporte."""
    results = episode_results(pd.read_parquet(path), initial_cash, stake)
    return results["final_value"] - initial_cash


def split_of(name: str) -> str:
    return name.split(" · ")[1]


def default_comparison(summary: Path, split: str, options: list[str]) -> list[str]:
    """Mejor agente y mejor baseline del reporte del split, en modo normal, si están disponibles."""
    if not summary.exists():
        return []
    table = pd.read_csv(summary)
    table = table[~table["strict"]].sort_values("mean_return", ascending=False)
    is_agent = table["label"].map(lambda label: bool(AGENT_LABEL.match(label)))
    picked = []
    for rows in (table[is_agent], table[~is_agent]):
        for label in rows["label"]:
            name = file_name(label, split, False)
            if name in options:
                picked.append(name)
                break
    return picked


def market_label(steps: pd.DataFrame) -> str:
    start = pd.to_datetime(steps["ts"].iloc[0], unit="s", utc=True)
    market_id = str(steps["market_id"].iloc[0])
    return f"{start:%Y-%m-%d %H:%M} UTC · {market_id[:10]}…"


def action_name(code: int) -> str:
    return Action(int(code)).name


def figure(steps: pd.DataFrame, k: int, initial_cash: float) -> Figure:
    """Precio YES con las órdenes ejecutadas y valor de la cartera, con el paso actual marcado."""
    fig = Figure(figsize=(9, 5.5))
    price, value = fig.subplots(2, 1, sharex=True, height_ratios=[2, 1])
    price.plot(steps["k"], steps["p_yes"], color="black", linewidth=1, label="p_yes")
    done = steps[steps["order_status"] == "ejecutada"]
    marks = (
        (Action.BUY_YES, "^", "tab:green", "compra YES"),
        (Action.BUY_NO, "v", "tab:red", "compra NO"),
        (Action.SELL, "x", "tab:blue", "venta"),
    )
    for action, marker, color, label in marks:
        rows = done[done["action_executed"] == action]
        if len(rows):
            price.scatter(rows["k"], rows["exec_p"], marker=marker, color=color, s=60, label=label)
    failed = steps[steps["order_status"].isin(["sin_precio", "no_verificable"])]
    if len(failed):
        price.scatter(
            failed["k"],
            failed["p_yes"],
            marker="o",
            facecolors="none",
            edgecolors="gray",
            label="sin ejecutar",
        )
    price.set_ylim(0, 1)
    price.set_ylabel("Precio YES")
    price.legend(fontsize="small", loc="upper left")
    value.plot(steps["k"], steps["portfolio_value"], color="tab:purple")
    value.axhline(initial_cash, color="gray", linewidth=0.8)
    value.set_ylabel("Valor (USDC)")
    value.set_xlabel("Paso (minuto del mercado)")
    for ax in (price, value):
        ax.axvline(k, color="tab:orange", linewidth=1)
    return fig


def comparison_figure(
    frames: dict[str, pd.DataFrame],
    pnl: dict[str, pd.Series],
    market_id: str,
    position: int,
    k: int,
    initial_cash: float,
) -> Figure:
    """PnL de cada política dentro del mercado y acumulado, con el mercado y el paso marcados."""
    fig = Figure(figsize=(9, 6))
    market, total = fig.subplots(2, 1)
    for name, frame in frames.items():
        steps = frame[frame["market_id"] == market_id]
        market.plot(steps["k"], steps["portfolio_value"] - initial_cash, label=name)
        curve = capital_curve(pnl[name])
        total.plot(range(1, len(curve) + 1), curve.to_numpy(), label=name)
    market.axhline(0, color="gray", linewidth=0.8)
    market.axvline(k, color="tab:orange", linewidth=1)
    market.set_xlabel("Paso (minuto del mercado)")
    market.set_ylabel("PnL en este mercado (USDC)")
    market.legend(fontsize="small")
    total.axhline(0, color="gray", linewidth=0.8)
    total.axvline(position, color="tab:orange", linewidth=1)
    total.set_xlabel("Mercado (orden cronológico)")
    total.set_ylabel("PnL acumulado (USDC)")
    fig.tight_layout()
    return fig


def comparison_rows(
    frames: dict[str, pd.DataFrame], pnl: dict[str, pd.Series], market_id: str, position: int
) -> pd.DataFrame:
    """PnL en el mercado, acumulado hasta él y órdenes ejecutadas en él, por política."""
    rows = {}
    for name, frame in frames.items():
        steps = frame[frame["market_id"] == market_id]
        rows[name] = {
            "PnL en este mercado": f"{pnl[name].loc[market_id]:+.2f}",
            f"PnL acumulado al mercado {position}": f"{pnl[name].iloc[:position].sum():+.2f}",
            "Órdenes ejecutadas": int((steps["order_status"] == "ejecutada").sum()),
        }
    return pd.DataFrame(rows).T


def comparison_section(
    choice: str,
    chosen: pd.DataFrame,
    others: list[str],
    files: dict[str, Path],
    market_id: str,
    position: int,
    k: int,
    initial_cash: float,
    stake: float,
) -> None:
    """Compara la política elegida con `others`, dejando afuera las que no tienen este mercado."""
    frames = {choice: chosen}
    missing = []
    for name in others:
        frame = load(str(files[name]), files[name].stat().st_mtime)
        if (frame["market_id"] == market_id).any():
            frames[name] = frame
        else:
            missing.append(name)
    if missing:
        st.warning(f"Sin este mercado, se dejan afuera: {', '.join(missing)}.")
    if len(frames) < 2:
        return
    pnl = {
        name: market_pnl(str(files[name]), files[name].stat().st_mtime, initial_cash, stake)
        for name in frames
    }
    st.subheader("Comparación")
    st.pyplot(comparison_figure(frames, pnl, market_id, position, k, initial_cash))
    st.table(comparison_rows(frames, pnl, market_id, position))


def step_panel(row: pd.Series, initial_cash: float) -> None:
    """Estado de la cartera y de la orden en un paso."""
    cols = st.columns(4)
    cols[0].metric("Caja", f"{row['cash']:.2f}")
    side = SIDES[int(row["position_side"])]
    size = f" ({row['position_size']:.2f} acciones)" if row["position_side"] else ""
    cols[1].metric("Posición", side + size)
    cols[2].metric(
        "Valor", f"{row['portfolio_value']:.2f}", f"{row['portfolio_value'] - initial_cash:+.2f}"
    )
    cols[3].metric("Recompensa", f"{row['reward']:+.6f}")

    order = {
        "Hora": f"{pd.to_datetime(row['ts'], unit='s', utc=True):%H:%M} UTC",
        "Precio YES": f"{row['p_yes']:.3f}",
        "Acción pedida": action_name(row["action"]),
        "Acción ejecutada": action_name(row["action_executed"]),
        "Estado de la orden": str(row["order_status"]),
    }
    if row["order_status"] == "ejecutada":
        order |= {
            "Precio de la operación": f"{row['fill_price']:.4f}",
            "Acciones": f"{row['fill_shares']:.2f}",
            "Comisión": f"{row['fee']:.5f}",
        }
    if pd.notna(row["exec_verified"]):
        order["Respaldada por trades reales"] = "sí" if row["exec_verified"] else "no"
    left, right = st.columns(2)
    left.table(pd.DataFrame({"Valor": order}))
    rewards = {name: row[f"r_{name}"] for name in COMPONENTS}
    right.table(pd.DataFrame({"Componente de la recompensa": rewards}))


def move(delta: int, last: int) -> None:
    st.session_state.step = min(max(st.session_state.step + delta, 0), last)


def restart() -> None:
    st.session_state.step = 0


st.set_page_config(page_title="PolyRL · demo", layout="wide")
st.title("PolyRL: reproducción de trayectorias")

paths = get_paths()
config = load_config(paths.configs / "env.yaml", SimulatorConfig)
initial_cash = config.env.initial_cash
stake = initial_cash * config.env.stake_fraction

folder = Path(st.sidebar.text_input("Carpeta de trayectorias", str(paths.reports / "trajectories")))
files = list_files(folder)
if not files:
    st.info(
        f"No hay trayectorias en {folder}. Genera algunas con `make backtest` o `polym4v evaluate`."
    )
    st.stop()

choice = st.sidebar.selectbox("Política y split", list(files), on_change=restart)
trajectories = load(str(files[choice]), files[choice].stat().st_mtime)
markets = {
    market_id: steps.reset_index(drop=True)
    for market_id, steps in trajectories.groupby("market_id", sort=False)
}
market_id = st.sidebar.selectbox(
    "Mercado",
    list(markets),
    format_func=lambda m: market_label(markets[m]),
    on_change=restart,
)
steps = markets[market_id]
last = len(steps) - 1

split = split_of(choice)
options = [name for name in files if name != choice and split_of(name) == split]
others = st.sidebar.multiselect(
    "Comparar con",
    options,
    default=default_comparison(paths.reports / split / "summary.csv", split, options),
    key=f"compare_{choice}",
)

st.session_state.setdefault("step", 0)
st.session_state.step = min(st.session_state.step, last)
playing = st.sidebar.toggle("Reproducir", key="playing")
if playing and st.session_state.step < last and st.session_state.get("advance"):
    st.session_state.step += 1
st.session_state.advance = False

pnl = steps["portfolio_value"].iloc[-1] - initial_cash
st.subheader(market_label(steps))
st.caption(
    f"Mercado {market_id} · {steps['policy'].iloc[0]} · PnL {pnl:+.2f} USDC "
    f"({pnl / stake:+.1%} del monto) · comisiones {steps['fees_paid'].iloc[-1]:.2f} USDC"
)

back, slider, forward = st.columns([1, 8, 1])
back.button("Anterior", on_click=move, args=(-1, last))
k = slider.slider("Paso", 0, last, key="step")
forward.button("Siguiente", on_click=move, args=(1, last))

st.pyplot(figure(steps, k, initial_cash))
step_panel(steps.iloc[k], initial_cash)
position = list(markets).index(market_id) + 1
comparison_section(choice, trajectories, others, files, market_id, position, k, initial_cash, stake)

if playing and k < last:
    time.sleep(PLAY_PAUSE_S)
    st.session_state.advance = True
    st.rerun()
