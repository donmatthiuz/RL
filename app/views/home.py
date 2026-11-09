"""Portada de la demo: qué es PolyRL, el resultado y a dónde ir (EVA-13)."""

from pathlib import Path

import streamlit as st

from core import CLASS_COLOR, POLICIES, card, report

VIEWS = Path(__file__).resolve().parent

st.markdown("# Del dato histórico a la decisión")
st.markdown(
    "Cada hora, Polymarket pregunta si Bitcoin cerrará **arriba o abajo** de su apertura. "
    "Agentes de aprendizaje por refuerzo deciden cada minuto si **comprar YES, comprar NO, vender "
    "o esperar**, y se comparan con reglas simples en mercados que nunca vieron."
)

# data/processed/btc_updown_1h_v1/manifest.json
cols = st.columns(4)
facts = [
    ("Mercados", "12 294", "mayo 2025 a octubre 2026"),
    ("Corte cronológico", "70 / 15 / 15", "train · val · test"),
    ("Agentes", "4", "PPO · DQN · CQL · BC"),
    ("Semillas", "5", "por agente"),
]
for col, (label, value, note) in zip(cols, facts, strict=True):
    col.metric(label, value, note, delta_color="off", delta_arrow="off", border=True)

st.markdown("### El resultado")
left, right = st.columns([3, 2])
with left, card("resultado"):
    st.markdown("#### En test, ningún agente le gana a no operar.")
    st.markdown("PPO, el mejor, queda **equivalente**: no se distingue de no operar.")
    groups = report("test", "comparison.csv")
    if groups is not None:
        normal = groups[~groups["strict"] & (groups["role"] == "principal")]
        row = st.container(horizontal=True)
        for _, item in normal.sort_values("mean", ascending=False).iterrows():
            name = POLICIES[item["group"].split("_")[0]][0]
            row.badge(
                f"{name}: {item['classification']}",
                color=CLASS_COLOR.get(item["classification"], "gray"),
            )
with right, card("aciertos"):
    payoff = report("test", "inspection_payoff.csv")
    rows = None if payoff is None else payoff[payoff["policy"] == "ppo_pnl_risk"]
    if rows is not None and len(rows):
        top = rows.iloc[-1]
        hit, need = st.columns(2)
        hit.metric(
            "PPO acierta",
            f"{top['side_won']:.2%}",
            "a más de 0,98",
            delta_color="off",
            delta_arrow="off",
        )
        need.metric(
            "Necesita",
            f"{top['cost']:.2%}",
            "para no perder",
            delta_color="off",
            delta_arrow="off",
        )
        st.caption(f"Neto en test: {top['net']:+.2f} USDC en {int(top['trades'])} compras.")

st.markdown("### Explorar")
links = [
    ("simulation.py", "Simulación", ":material/play_circle:", "Una hora de mercado, paso a paso."),
    ("comparison.py", "Comparación", ":material/compare_arrows:", "Políticas frente a frente."),
    ("guide.py", "Cómo funciona", ":material/menu_book:", "Mercado, costos, políticas y datos."),
]
for i, (col, (page, title, icon, text)) in enumerate(zip(st.columns(3), links, strict=True)):
    with col, card(f"explorar_{i}"):
        st.page_link(str(VIEWS / page), label=title, icon=icon)
        st.caption(text)
