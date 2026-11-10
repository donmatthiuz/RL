"""Comparación de políticas en el mismo mercado, en todo el split y según el protocolo (EVA-13)."""

import pandas as pd
import streamlit as st

import charts
from core import (
    AGENT_LABEL,
    CLASS_COLOR,
    POLICIES,
    card,
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
with left, card("mercado"):
    st.altair_chart(
        charts.pnl_by_minute(inside, {display[n]: colors[display[n]] for n in frames}),
        width="stretch",
        theme=None,
        alt="PnL de cada política dentro del mercado",
    )
with right, card("mercado_cifras"):
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
with left, card("total"):
    st.altair_chart(
        charts.cumulative(
            total, {display[n]: colors[display[n]] for n in frames}, start.tz_localize(None)
        ),
        width="stretch",
        theme=None,
        alt="PnL acumulado de cada política en el split",
    )
    st.caption(f"Línea vertical: el mercado elegido ({position} de {len(pnl[selection.choice])}).")
with right, card("total_cifras"):
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
with left, card("protocolo"):
    st.altair_chart(
        charts.forest(table, DELTA_MIN),
        width="stretch",
        theme=None,
        alt="Media de D e intervalo de confianza por agente",
    )
    st.caption(
        "Media de D frente a no operar con su IC del 98,75 %. Banda: equivalencia, ±1 % del monto."
    )
with right, card("protocolo_cifras"):
    for _, row in table.iterrows():
        st.markdown(f"**{row['agente']}** · media {row['mean']:+.4f}")
        st.badge(row["classification"], color=CLASS_COLOR.get(row["classification"], "gray"))
    st.caption("Equivalente no significa que gane.")

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
        with left, card("aciertos"):
            st.altair_chart(
                charts.payoff(rows),
                width="stretch",
                theme=None,
                alt="Aciertos frente al costo por acción, por tramo de precio",
            )
        top = rows.iloc[-1]
        with right, card("aciertos_cifras"):
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
            st.caption("A más de 0,98, un acierto gana centavos y un error pierde casi todo.")
st.caption(f"Fuente: reports/{selection.split}/.")
