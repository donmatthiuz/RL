"""Demo de PolyRL (EVA-07): reproduce paso a paso las trayectorias de `backtest` y `evaluate`.

Lee los Parquet de `reports/trajectories/` (o de la carpeta que se elija), así que no necesita GPU
ni red. Muestra un mercado a la vez: el precio YES con las compras y ventas, el valor de la cartera
y el estado del paso elegido. Es funcional; el diseño visual se define al final del proyecto.

Correr con `make demo`.
"""

import time
from pathlib import Path

import pandas as pd
import streamlit as st
from matplotlib.figure import Figure

from polym4v.agents.base import Action
from polym4v.evaluation.report import STRICT_SUFFIX, parse_name
from polym4v.utils.config import SimulatorConfig, load_config
from polym4v.utils.paths import get_paths

SPLITS = ("train", "val", "test")
SIDES = {1: "YES", -1: "NO", 0: "sin posición"}
REWARD_COMPONENTS = ("r_pnl", "r_drawdown", "r_invalid", "r_terminal")
PLAY_PAUSE_S = 0.4


def list_files(folder: Path) -> dict[str, Path]:
    """`etiqueta · split[ · estricto]` → archivo, para los Parquet con nombre de trayectorias."""
    files = {}
    for path in sorted(folder.glob("*.parquet")):
        for split in SPLITS:
            parsed = parse_name(path, split)
            if parsed is not None:
                label, strict = parsed
                name = f"{label} · {split}" + (f" · {STRICT_SUFFIX[1:]}" if strict else "")
                files[name] = path
    return files


@st.cache_data
def load(path: str, mtime: float) -> pd.DataFrame:
    """Trayectorias de un archivo; `mtime` invalida la caché si el archivo se vuelve a generar."""
    return pd.read_parquet(path)


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
    rewards = {name.removeprefix("r_"): row[name] for name in REWARD_COMPONENTS}
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

if playing and k < last:
    time.sleep(PLAY_PAUSE_S)
    st.session_state.advance = True
    st.rerun()
