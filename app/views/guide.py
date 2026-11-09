"""Cómo funciona: el mercado, el entorno, las acciones, las políticas y los datos (EVA-13)."""

from pathlib import Path

import pandas as pd
import streamlit as st

from core import CLASS_COLOR, POLICIES, label_of, list_files, pretty, report, simulator, split_of
from polym4v.env.execution import buy
from polym4v.utils.config import SimulatorConfig, load_config
from polym4v.utils.paths import get_paths
from selection import folder_input

config = load_config(get_paths().configs / "env.yaml", SimulatorConfig)
initial_cash, stake = simulator()

st.markdown("## Cómo funciona")
market, environment, actions, policies, data = st.tabs(
    ["El mercado", "El entorno y los costos", "Las acciones", "Las políticas", "Los datos"]
)

with market:
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown(
            "Cada hora hay un mercado **Bitcoin Up or Down**: gana **YES (Up)** si BTC cierra la "
            "hora "
            "en o por encima del precio con que abrió, y gana **NO (Down)** si cierra abajo.\n\n"
            "- Cada acción ganadora paga **1 USDC** al cierre; la perdedora, 0.\n"
            "- Por eso el precio de YES se lee como la **probabilidad** que el mercado le da a que "
            "suba, y el de NO es `1 − YES`.\n"
            "- Al principio de la hora el precio ronda 0,5. A medida que BTC se aleja de la "
            "apertura y "
            "queda menos tiempo, se va a 0 o a 1.\n\n"
            "Usamos 12 294 mercados horarios reales de mayo de 2025 a octubre de 2026, con su "
            "precio minuto a minuto y el precio de BTC del mismo minuto."
        )
    with right, st.container(border=True):
        st.markdown("**Ejemplo**")
        st.markdown(
            "A las 14:30, BTC está un poco arriba de la apertura y YES vale **0,60**.\n\n"
            f"- Comprar YES con {stake:.0f} USDC da unas {stake / 0.61:.1f} acciones.\n"
            f"- Si BTC cierra arriba, cobra {stake / 0.61:.1f} USDC: gana unos "
            f"{stake / 0.61 - stake:.1f}.\n"
            f"- Si cierra abajo, pierde los {stake:.0f} USDC."
        )

with environment:
    costs = config.env.costs
    st.markdown(
        "El simulador repite cada mercado histórico como un episodio de **60 pasos de un "
        "minuto**.\n\n"
        f"- Cada hora empieza con **{initial_cash:,.0f} USDC ficticios** y cada orden usa "
        f"**{stake:.0f} USDC** ({config.env.stake_fraction:.0%} del saldo). Una posición a la "
        "vez.\n"
        "- La orden se ejecuta al primer precio disponible después de **t + "
        f"{config.env.latency_s} s**, "
        "para que el agente no use un precio que todavía no podía ver.\n"
        f"- En los últimos {config.env.no_open_last_minutes} minutos no se abren posiciones.\n"
        "- Si no vende, la posición se **liquida al cierre**: 1 USDC por acción ganadora, sin "
        "comisión.\n"
        f"- Comprar cuesta el precio del lado **más medio spread ({costs.half_spread})** y la "
        f"comisión taker de Polymarket, `{costs.fee_rate} × p × (1 − p) × acciones`."
    )
    rows = []
    for price in (0.50, 0.80, 0.90, 0.95, 0.98, 0.99):
        fill = buy(stake, price, costs)
        rows.append(
            {
                "Precio del lado": f"{price:.2f}",
                "Precio pagado": f"{fill.price:.3f}",
                "Acciones": f"{fill.shares:.2f}",
                "Comisión (USDC)": f"{fill.fee:.4f}",
                "Si acierta, gana (USDC)": f"{fill.shares - stake:+.2f}",
                "Hay que acertar al menos": f"{stake / fill.shares:.2%}",
            }
        )
    st.markdown(f"**Cuánto cuesta comprar con {stake:.0f} USDC**")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption(
        "La última columna es el costo por acción: la fracción de veces que hay que acertar para "
        "no "
        "perder. A 0,99, cada acción cuesta casi 1 y la ganancia por acierto es mínima."
    )
    st.markdown(
        "**Recompensa.** El agente aprende con `pnl_risk`: el cambio del valor de la cartera en "
        "cada "
        "minuto menos una penalización por la caída desde el máximo de la hora. Ganó la ablación "
        "de recompensas en val."
    )

with actions:
    st.dataframe(
        pd.DataFrame(
            {
                "Acción": ["WAIT", "BUY_YES", "BUY_NO", "SELL"],
                "Qué hace": [
                    "Esperar: no hace nada este minuto.",
                    "Compra YES con el monto fijo, si no tiene posición.",
                    "Compra NO con el monto fijo, si no tiene posición.",
                    "Vende toda la posición al precio del lado menos medio spread.",
                ],
            }
        ),
        hide_index=True,
        width="stretch",
    )
    st.markdown("**Qué le pasa a cada orden** (columna `order_status`)")
    st.dataframe(
        pd.DataFrame(
            {
                "Estado": ["ninguna", "ejecutada", "invalida", "sin_precio"],
                "Significa": [
                    "El agente esperó.",
                    "La orden se hizo al precio del minuto siguiente a t + 2 s.",
                    "No se puede: vender sin posición, comprar con una abierta o abrir en los "
                    "últimos 2 minutos. Se trata como esperar.",
                    "No hubo precio a tiempo; la orden no se ejecuta.",
                ],
            }
        ),
        hide_index=True,
        width="stretch",
    )

with policies:
    groups = report("test", "comparison.csv")
    activity = report("test", "inspection_activity.csv")
    verdict = {}
    if groups is not None:
        normal = groups[~groups["strict"] & (groups["role"] == "principal")]
        verdict = {
            row["group"].split("_")[0]: row["classification"] for _, row in normal.iterrows()
        }
    habits = {}
    if activity is not None:
        habits = {row["policy"].split("_")[0]: row for _, row in activity.iterrows()}
    st.markdown("**Agentes de aprendizaje por refuerzo**")
    cols = st.columns(2)
    for i, key in enumerate(("ppo", "dqn", "cql", "bc")):
        name, text = POLICIES[key]
        with cols[i % 2], st.container(border=True):
            st.markdown(f"#### {name}")
            st.markdown(text)
            if key in verdict:
                st.badge(f"test: {verdict[key]}", color=CLASS_COLOR.get(verdict[key], "gray"))
            if key in habits:
                habit = habits[key]
                st.caption(
                    f"En test: {int(habit['trades'])} compras en 5 semillas, minuto mediano "
                    f"{habit['median_minute']:.0f}, el {habit['favorite_share']:.0%} al favorito."
                )
    st.markdown("**Baselines (reglas simples)**")
    cols = st.columns(3)
    for i, key in enumerate(
        ("no_trade", "fair_value", "favorite", "momentum", "mean_reversion", "random")
    ):
        name, text = POLICIES[key]
        with cols[i % 3], st.container(border=True):
            st.markdown(f"**{name}** · `{key}`")
            st.caption(text)

with data:
    st.markdown(
        "La demo no vuelve a correr ningún agente: **reproduce trayectorias grabadas**. Cada fila "
        "de una trayectoria es un minuto de un mercado con lo que el agente vio, pidió y "
        "obtuvo.\n\n"
        "- `make backtest POLICY=<baseline> SPLIT=<split>` y `polym4v evaluate --run <corrida> "
        "--split <split>` las escriben en `reports/trajectories/`.\n"
        "- El nombre dice qué es: `<fecha>_<agente>_<recompensa>_s<semilla>_<split>.parquet` para "
        "los agentes, `<baseline>_<split>.parquet` para las reglas, y `_estricto` si solo se "
        "aceptan ejecuciones respaldadas por trades reales.\n"
        "- La demo publicada no tiene esa carpeta, que pesa unos 140 MB: usa la muestra de test de "
        "`app/trayectorias/` (PPO semilla 0, no operar y valor justo) más el precio de BTC de cada "
        "mercado (`make demo-muestra`)."
    )
    folder_input()
    files = list_files(Path(st.session_state.folder))
    st.markdown(f"**Carpeta actual:** `{st.session_state.folder}` · {len(files)} archivos")
    if files:
        st.dataframe(
            pd.DataFrame(
                {
                    "Política": [pretty(label_of(name)) for name in files],
                    "Split": [split_of(name) for name in files],
                    "Modo": [
                        "estricto" if name.endswith("estricto") else "normal" for name in files
                    ],
                    "Archivo": [path.name for path in files.values()],
                    "MB": [round(path.stat().st_size / 1e6, 2) for path in files.values()],
                }
            ),
            hide_index=True,
            width="stretch",
        )
    st.markdown("**Columnas principales**")
    st.dataframe(
        pd.DataFrame(
            {
                "Columna": [
                    "k",
                    "ts",
                    "p_yes",
                    "action",
                    "action_executed",
                    "order_status",
                    "fill_price",
                    "fill_shares",
                    "fee",
                    "position_side",
                    "cash",
                    "portfolio_value",
                    "reward",
                ],
                "Qué es": [
                    "Minuto del mercado, de 0 a 59",
                    "Hora del minuto (Unix, UTC)",
                    "Precio YES que vio el agente",
                    "Acción pedida (0 esperar, 1 comprar YES, 2 comprar NO, 3 vender)",
                    "Acción que de verdad se ejecutó",
                    "Qué le pasó a la orden",
                    "Precio pagado o recibido por acción",
                    "Acciones compradas o vendidas",
                    "Comisión en USDC",
                    "Posición después del minuto: 1 YES, −1 NO, 0 nada",
                    "Caja en USDC",
                    "Caja más la posición a precio de mercado (al final, liquidada)",
                    "Recompensa que recibió el agente",
                ],
            }
        ),
        hide_index=True,
        width="stretch",
    )
