"""Demo de PolyRL (EVA-07 a EVA-09 y EVA-13): una hora de mercado con un agente, minuto a minuto.

Cuatro páginas: inicio, simulación, comparación y cómo funciona. Reproduce trayectorias ya
calculadas por `backtest` y `evaluate`, así que no necesita GPU ni red, y no vuelve a evaluar test.
La identidad visual sale de `entregas/final/presentacion/DESIGN.md` (tema en `.streamlit/`).

Correr con `make demo`. Sin trayectorias en `reports/trajectories/` usa la muestra de test de
`app/trayectorias/`, que es la que ve la demo publicada en Cloud Run (EVA-09).
"""

from pathlib import Path

import streamlit as st

from core import default_folder
from selection import folder_input

STATIC = Path(__file__).resolve().parent / "static"
PAGES = Path(__file__).resolve().parent / "app_pages"

st.set_page_config(page_title="PolyRL [DEMO]", page_icon=str(STATIC / "polyrl.svg"), layout="wide")
st.logo(str(STATIC / "polyrl_marca.svg"), icon_image=str(STATIC / "polyrl.svg"), size="large")
# DESIGN.md 9.3: tarjetas y métricas sobre superficie blanca, etiquetas de métrica en mono y
# mayúsculas, y cifras tabulares para que no bailen mientras avanza la reproducción.
st.html(
    "<style>"
    "[class*='st-key-card_'],[data-testid='stMetric']{background:#FFFFFF}"
    "[data-testid='stMetricValue']{font-variant-numeric:tabular-nums}"
    "[data-testid='stMetricLabel'] p{font-family:'JetBrains Mono',monospace;"
    "text-transform:uppercase;letter-spacing:.12em;font-size:11px}"
    "</style>"
)

st.session_state.setdefault("folder", str(default_folder()))
st.session_state.setdefault("step", 0)
st.session_state.setdefault("playing", False)
st.session_state.setdefault("ticking", False)
st.session_state.setdefault("speed", "Normal")

pages = st.navigation(
    [
        st.Page(PAGES / "home.py", title="Inicio", icon=":material/home:", default=True),
        st.Page(PAGES / "simulation.py", title="Simulación", icon=":material/play_circle:"),
        st.Page(PAGES / "comparison.py", title="Comparación", icon=":material/compare_arrows:"),
        st.Page(PAGES / "guide.py", title="Cómo funciona", icon=":material/menu_book:"),
    ],
    position="top",
)
folder_input()  # en todas las páginas, así la barra lateral existe y se puede contraer
pages.run()
