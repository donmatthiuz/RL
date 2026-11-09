"""Demo de PolyRL (EVA-07 a EVA-09 y EVA-13): una hora de mercado con un agente, minuto a minuto.

Cuatro páginas: inicio, simulación, comparación y cómo funciona. Reproduce trayectorias ya
calculadas por `backtest` y `evaluate`, así que no necesita GPU ni red, y no vuelve a evaluar test.
La identidad visual sale de `entregas/final/presentacion/DESIGN.md` (tema en `.streamlit/`).

Correr con `make demo`. Sin trayectorias en `reports/trajectories/` usa la muestra de test de
`app/trayectorias/`, que es la que ve la demo publicada en Streamlit Community Cloud (EVA-09).
"""

from pathlib import Path

import streamlit as st

from core import default_folder

STATIC = Path(__file__).resolve().parent / "static"
VIEWS = Path(__file__).resolve().parent / "views"

st.set_page_config(page_title="PolyRL", page_icon=str(STATIC / "polyrl.svg"), layout="wide")
st.logo(str(STATIC / "polyrl_marca.svg"), icon_image=str(STATIC / "polyrl.svg"), size="large")
# Cifras tabulares, para que las métricas no bailen mientras avanza la reproducción, y menos
# margen arriba del contenido.
st.html(
    "<style>[data-testid='stMetricValue']{font-variant-numeric:tabular-nums}"
    "[data-testid='stMainBlockContainer']{padding-top:2.5rem}</style>"
)

st.session_state.setdefault("folder", str(default_folder()))
st.session_state.setdefault("step", 0)
st.session_state.setdefault("playing", False)
st.session_state.setdefault("ticking", False)
st.session_state.setdefault("speed", "Normal")

pages = st.navigation(
    [
        st.Page(VIEWS / "home.py", title="Inicio", icon=":material/home:", default=True),
        st.Page(VIEWS / "simulation.py", title="Simulación", icon=":material/play_circle:"),
        st.Page(VIEWS / "comparison.py", title="Comparación", icon=":material/compare_arrows:"),
        st.Page(VIEWS / "guide.py", title="Cómo funciona", icon=":material/menu_book:"),
    ],
    position="top",
)
pages.run()

st.divider()
st.caption(
    "Simulación con saldo ficticio sobre datos históricos. Polymarket solo se usa como fuente de "
    "datos: el agente nunca opera en vivo ni con dinero real."
)
