"""Portada de la demo: qué es PolyRL, el resultado y a dónde ir (EVA-13)."""

from pathlib import Path

import streamlit as st

from core import BLUE, CLASS_COLOR, POLICIES, report

# data/processed/btc_updown_1h_v1/manifest.json: 12 294 mercados en total.
SPLITS = {"train": 8682, "val": 1861, "test": 1751}
VIEWS = Path(__file__).resolve().parent

st.markdown(
    f'<p style=\'font-family:"JetBrains Mono",monospace;letter-spacing:.14em;font-size:12px;'
    f"color:{BLUE};margin-bottom:0'>APRENDIZAJE POR REFUERZO · UVG</p>",
    unsafe_allow_html=True,
)
st.markdown("# Del dato histórico a la decisión")
st.markdown(
    "Cada hora, Polymarket pregunta si Bitcoin va a cerrar **arriba o abajo** de donde abrió. El "
    "precio de **YES** es la probabilidad que el mercado le da a que suba. Entrenamos agentes de "
    "aprendizaje por refuerzo para decidir, minuto a minuto, si **comprar YES, comprar NO, vender "
    "o esperar**, y los comparamos con reglas simples, con los mismos costos y en mercados que "
    "nunca vieron."
)

cols = st.columns(4)
cols[0].metric(
    "Mercados reales",
    f"{sum(SPLITS.values()):,}".replace(",", " "),
    "mayo 2025 a octubre 2026",
    delta_color="off",
    delta_arrow="off",
    border=True,
)
cols[1].metric(
    "Corte cronológico",
    "70 / 15 / 15",
    "train · val · test",
    delta_color="off",
    delta_arrow="off",
    border=True,
)
cols[2].metric(
    "Agentes", "4", "PPO · DQN · CQL · BC", delta_color="off", delta_arrow="off", border=True
)
cols[3].metric(
    "Semillas por agente",
    "5",
    "para no depender de la suerte",
    delta_color="off",
    delta_arrow="off",
    border=True,
)

st.markdown("### El resultado")
left, right = st.columns([3, 2], gap="medium")
with left, st.container(border=True):
    st.markdown(
        "#### En test, ningún agente le gana a no operar.\n"
        "PPO, el mejor, queda **equivalente**: su diferencia con no operar cabe dentro de ±1 % del "
        "monto, pero no es positiva. Es un resultado válido: el protocolo se fijó antes de mirar "
        "test y se reporta aunque no gane."
    )
    groups = report("test", "comparison.csv")
    if groups is not None:
        normal = groups[~groups["strict"] & (groups["role"] == "principal")].sort_values(
            "mean", ascending=False
        )
        row = st.container(horizontal=True)
        for _, item in normal.iterrows():
            name = POLICIES[item["group"].split("_")[0]][0]
            row.badge(
                f"{name}: {item['classification']}",
                color=CLASS_COLOR.get(item["classification"], "gray"),
            )
with right, st.container(border=True):
    payoff = report("test", "inspection_payoff.csv")
    if payoff is not None:
        top = payoff[(payoff["policy"] == "ppo_pnl_risk") & (payoff["price"] == "0.98-1")]
        if len(top):
            top = top.iloc[0]
            st.metric(
                "PPO acierta a más de 0,98",
                f"{top['side_won']:.2%}",
                f"{int(top['trades'])} compras en test",
                delta_color="off",
                delta_arrow="off",
            )
            st.metric(
                "Necesita para no perder",
                f"{top['cost']:.2%}",
                f"neto {top['net']:+.2f} USDC",
                delta_color="off",
                delta_arrow="off",
            )
    st.caption("Acertar casi siempre no alcanza cuando cada acción cuesta 0,9988 y paga 1.")

st.markdown("### Explorar")
cols = st.columns(3)
links = [
    (
        "simulation.py",
        "Simulación",
        ":material/play_circle:",
        "Una hora de mercado con un agente, minuto a minuto: el precio de BTC, el precio YES, sus "
        "órdenes y el resultado.",
    ),
    (
        "comparison.py",
        "Comparación",
        ":material/compare_arrows:",
        "Las políticas en el mismo mercado y en todo test, y lo que dice el protocolo.",
    ),
    (
        "guide.py",
        "Cómo funciona",
        ":material/menu_book:",
        "El mercado, el entorno, los costos, las acciones, cada política y de dónde salen los "
        "datos.",
    ),
]
for col, (page, title, icon, text) in zip(cols, links, strict=True):
    with col, st.container(border=True):
        st.page_link(str(VIEWS / page), label=title, icon=icon)
        st.caption(text)
