"""Comparación de políticas en el mismo mercado, en todo el split y según el protocolo (EVA-13)."""

import pandas as pd
import streamlit as st

import charts
from core import (
    AGENT_LABEL,
    CLASS_COLOR,
    POLICIES,
    color,
    label_of,
    load,
    market_pnl,
    pretty,
    report,
    simulator,
)
from selection import default_others, others, policy_label, select

DELTA_MIN = 0.01  # Δ_min del protocolo: 1 % del monto (EVA-01, docs/notas/protocolo_eval.md)

selection = select()
if selection is None:
    st.stop()
initial_cash, stake = simulator()

st.markdown("## Comparación")
st.caption(
    "Las mismas reglas, los mismos costos y los mismos mercados para todas las políticas. "
    "La elegida en la barra lateral se compara con las de abajo."
)
chosen = st.multiselect(
    "Comparar con",
    others(selection),
    default=default_others(selection),
    format_func=policy_label,
    key=f"w_compare_{selection.choice}",
)
names = [selection.choice, *chosen]
display = {
    name: pretty(label_of(name)) + (" · estricto" if name.endswith("estricto") else "")
    for name in names
}
colors = {display[name]: color(label_of(name)) for name in names}


def kind_of(name: str) -> str:
    return "agente" if AGENT_LABEL.match(label_of(name)) else "baseline"


frames, missing = {}, []
for name in names:
    frame = load(str(selection.files[name]), selection.files[name].stat().st_mtime)
    if (frame["market_id"] == selection.market_id).any():
        frames[name] = frame
    else:
        missing.append(display[name])
if missing:
    st.warning(f"Sin este mercado, se dejan afuera: {', '.join(missing)}.")

pnl = {
    name: market_pnl(
        str(selection.files[name]), selection.files[name].stat().st_mtime, initial_cash, stake
    )
    for name in frames
}
start = pd.to_datetime(selection.by_market[selection.market_id]["ts"].iloc[0], unit="s", utc=True)

st.markdown(f"### En este mercado · {start:%d/%m/%Y %H:%M} UTC")
inside = pd.concat(
    [
        frame.loc[frame["market_id"] == selection.market_id, ["k", "portfolio_value"]].assign(
            pnl=lambda d: d["portfolio_value"] - initial_cash,
            politica=display[name],
            tipo=kind_of(name),
        )
        for name, frame in frames.items()
    ]
)
left, right = st.columns([2, 1], gap="medium")
with left, st.container(border=True):
    st.altair_chart(
        charts.pnl_by_minute(inside, {display[n]: colors[display[n]] for n in frames}),
        width="stretch",
        theme=None,
    )
with right, st.container(border=True):
    for name, frame in frames.items():
        steps = frame[frame["market_id"] == selection.market_id]
        done = steps[steps["order_status"] == "ejecutada"]
        first = (
            f"primera orden en el minuto {int(done['k'].iloc[0])}" if len(done) else "sin órdenes"
        )
        value = pnl[name].loc[selection.market_id]
        st.metric(display[name], f"{value:+.2f} USDC", first, delta_color="off", delta_arrow="off")

st.markdown(f"### En todo {selection.split}")
position = list(pnl[selection.choice].index).index(selection.market_id) + 1
total = pd.concat(
    [
        pd.DataFrame(
            {
                "inicio": pd.to_datetime(
                    frames[name].groupby("market_id", sort=False)["ts"].first().loc[series.index],
                    unit="s",
                    utc=True,
                ).dt.tz_localize(None),
                "acumulado": series.cumsum().to_numpy(),
                "politica": display[name],
                "tipo": kind_of(name),
            }
        )
        for name, series in pnl.items()
    ]
)
left, right = st.columns([2, 1], gap="medium")
with left, st.container(border=True):
    st.altair_chart(
        charts.cumulative(
            total, {display[n]: colors[display[n]] for n in frames}, start.tz_localize(None)
        ),
        width="stretch",
        theme=None,
    )
    st.caption(
        f"La línea vertical marca el mercado elegido, el número {position} de "
        f"{len(pnl[selection.choice])}."
    )
with right, st.container(border=True):
    for name, series in pnl.items():
        traded = int((series != 0).sum())
        st.metric(
            display[name],
            f"{series.sum():+.2f} USDC",
            f"operó en {traded} de {len(series)} mercados",
            delta_color="off",
            delta_arrow="off",
        )

st.markdown("### Lo que dice el protocolo")
groups = report(selection.split, "comparison.csv")
if groups is None:
    st.caption(f"No hay `reports/{selection.split}/comparison.csv` para este split.")
    st.stop()
mode = st.segmented_control("Modo", ["normal", "estricto"], default="normal", key="w_mode")
strict = mode == "estricto"
table = groups[(groups["strict"] == strict) & (groups["role"] == "principal")].copy()
table["agente"] = table["group"].map(lambda g: POLICIES[g.split("_")[0]][0])
table["clasificacion"] = table["classification"]
table = table.sort_values("mean", ascending=False)
left, right = st.columns([2, 1], gap="medium")
with left, st.container(border=True):
    st.altair_chart(charts.forest(table, DELTA_MIN), width="stretch", theme=None)
    st.caption(
        "Cada punto es la media de D: lo que el agente gana o pierde por mercado frente a no "
        f"operar, como fracción del monto. La línea es su IC del 98,75 % y la banda, la zona de "
        f"equivalencia de ±{DELTA_MIN:g} (1 % del monto)."
    )
with right, st.container(border=True):
    for _, row in table.iterrows():
        st.markdown(f"**{row['agente']}** · media {row['mean']:+.4f}")
        st.badge(row["classification"], color=CLASS_COLOR.get(row["classification"], "gray"))
    st.caption(
        "Equivalente quiere decir que la diferencia con no operar cabe en ±0,01 del monto; no "
        "quiere decir que gane."
    )

payoff = report(
    selection.split, "inspection_payoff.csv" if selection.split == "test" else "behavior_payoff.csv"
)
if payoff is not None:
    best = table.iloc[0]["group"]
    rows = payoff[payoff["policy"] == best]
    if len(rows):
        name = POLICIES[best.split("_")[0]][0]
        st.markdown(f"### Por qué acertar no alcanza · {name}")
        left, right = st.columns([2, 1], gap="medium")
        with left, st.container(border=True):
            st.altair_chart(charts.payoff(rows), width="stretch", theme=None)
        top = rows.iloc[-1]
        with right, st.container(border=True):
            st.metric(
                f"Aciertos a {top['price']}",
                f"{top['side_won']:.2%}",
                f"{int(top['trades'])} compras",
                delta_color="off",
                delta_arrow="off",
            )
            st.metric(
                "Necesario para no perder",
                f"{top['cost']:.2%}",
                "costo por acción",
                delta_color="off",
                delta_arrow="off",
            )
            st.metric("Resultado neto en ese tramo", f"{top['net']:+.2f} USDC", border=False)
            st.caption(
                "Comprar a más de 0,98 deja ganar menos de 2 centavos por acción; un solo error "
                "pierde casi todo el monto. Por eso acertar casi siempre no alcanza."
            )
st.caption(
    f"Fuentes: reports/{selection.split}/comparison.csv y el reporte de comportamiento del split."
)
