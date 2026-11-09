"""Gráficos de la demo en Altair, con el estilo de datos del DESIGN.md (sección 4.5)."""

from typing import TypeVar

import altair as alt
import pandas as pd

from core import AMBER, BLUE, BTC, GREEN, INK, LINE, RED, TEXT_2

MONO = "JetBrains Mono, monospace"
C = TypeVar("C", alt.LayerChart, alt.Chart)
MINUTES = alt.Scale(domain=[0, 59], nice=False)


def styled(chart: C) -> C:
    """Ejes en gris, retícula tenue, sin marco ni fondo, etiquetas en mono."""
    return (
        chart.configure(background="transparent")
        .configure_view(stroke=None)
        .configure_axis(
            labelFont=MONO,
            titleFont=MONO,
            labelColor=TEXT_2,
            titleColor=TEXT_2,
            labelFontSize=11,
            titleFontSize=11,
            titleFontWeight="normal",
            gridColor=INK,
            gridOpacity=0.08,
            domainColor=LINE,
            tickColor=LINE,
        )
        .configure_legend(
            labelFont=MONO,
            titleFont=MONO,
            labelColor=TEXT_2,
            titleColor=TEXT_2,
            orient="top",
            labelLimit=0,
        )
    )


def market(
    spot: pd.DataFrame | None, steps: pd.DataFrame, k: int, spot_open: float | None
) -> list[alt.LayerChart]:
    """BTC contra su apertura (arriba) y precio YES con las órdenes (abajo), hasta el minuto `k`.

    Los dominios son los de la hora completa, para que los ejes no salten mientras avanza. Sin
    datos de BTC dibuja solo el precio YES. Son dos gráficos separados, porque uno compuesto no se
    estira al ancho de la columna.
    """
    now = alt.Chart(pd.DataFrame({"k": [k]})).mark_rule(color=AMBER, strokeWidth=2).encode(x="k:Q")
    bottom = _yes(steps, k, now)
    if spot is None or spot_open is None:
        return [styled(bottom)]
    low, high = spot["spot"].min(), spot["spot"].max()
    pad = max(high - low, spot_open * 0.0005) * 0.15
    btc_scale = alt.Scale(
        domain=[min(low, spot_open) - pad, max(high, spot_open) + pad], zero=False
    )

    seen = spot[spot["k"] <= k]
    btc = (
        alt.Chart(seen)
        .mark_line(color=BTC, strokeWidth=2.5, interpolate="monotone")
        .encode(
            x=alt.X("k:Q", scale=MINUTES, title=None),
            y=alt.Y("spot:Q", scale=btc_scale, title="BTC (USDT)", axis=alt.Axis(format=",.0f")),
            tooltip=[
                alt.Tooltip("k:Q", title="Minuto"),
                alt.Tooltip("spot:Q", title="BTC", format=",.2f"),
            ],
        )
    )
    opening = (
        alt.Chart(pd.DataFrame({"y": [spot_open], "text": ["apertura"]}))
        .mark_rule(color=TEXT_2, strokeDash=[4, 4])
        .encode(y="y:Q")
    )
    opening_text = (
        alt.Chart(
            pd.DataFrame({"y": [spot_open], "x": [0], "text": [f"apertura {spot_open:,.2f}"]})
        )
        .mark_text(align="left", dy=-7, font=MONO, fontSize=11, color=TEXT_2)
        .encode(x="x:Q", y="y:Q", text="text:N")
    )
    current = btc.transform_filter(alt.datum.k == k).mark_point(
        filled=True, size=80, color=BTC, opacity=1
    )
    top = (opening + opening_text + btc + current + now).properties(height=190)
    return [styled(top), styled(bottom)]


def _yes(steps: pd.DataFrame, k: int, now: alt.Chart) -> alt.LayerChart:
    """Precio YES hasta el minuto `k`, con las órdenes ejecutadas."""
    shown = steps[steps["k"] <= k]
    yes = (
        alt.Chart(shown)
        .mark_line(color=INK, strokeWidth=2, interpolate="step-after")
        .encode(
            x=alt.X("k:Q", scale=MINUTES, title="Minuto del mercado"),
            y=alt.Y("p_yes:Q", scale=alt.Scale(domain=[0, 1]), title="Precio YES"),
            tooltip=[
                alt.Tooltip("k:Q", title="Minuto"),
                alt.Tooltip("p_yes:Q", title="YES", format=".4f"),
            ],
        )
    )
    half = alt.Chart(pd.DataFrame({"y": [0.5]})).mark_rule(color=LINE).encode(y="y:Q")
    # El color dice el lado (YES verde, NO rojo) y la forma, la acción (compra o venta).
    sold = shown["position_side"].shift(1, fill_value=0)
    orders = shown.assign(
        lado=lambda d: (
            d["action_executed"].map({1: 1, 2: -1}).fillna(sold).map({1: "YES", -1: "NO"})
        ),
        orden=lambda d: d["action_executed"].map({1: "compra", 2: "compra", 3: "venta"}),
    )
    orders = orders[orders["order_status"] == "ejecutada"]
    marks = (
        alt.Chart(orders)
        .mark_point(size=170, filled=True, opacity=1, stroke="white", strokeWidth=1.5)
        .encode(
            x="k:Q",
            y="exec_p:Q",
            shape=alt.Shape(
                "orden:N",
                scale=alt.Scale(domain=["compra", "venta"], range=["triangle-up", "triangle-down"]),
                legend=alt.Legend(title=None),
            ),
            color=alt.Color(
                "lado:N",
                scale=alt.Scale(domain=["YES", "NO"], range=[GREEN, RED]),
                legend=alt.Legend(title=None),
            ),
            tooltip=[
                alt.Tooltip("k:Q", title="Minuto"),
                alt.Tooltip("orden:N", title="Orden"),
                alt.Tooltip("lado:N", title="Lado"),
                alt.Tooltip("fill_price:Q", title="Precio del lado", format=".4f"),
                alt.Tooltip("fill_shares:Q", title="Acciones", format=".2f"),
                alt.Tooltip("fee:Q", title="Comisión", format=".5f"),
            ],
        )
    )
    current = yes.transform_filter(alt.datum.k == k).mark_point(
        filled=True, size=80, color=INK, opacity=1
    )
    return (half + yes + current + marks + now).properties(height=210)


def pnl_by_minute(
    frame: pd.DataFrame, colors: dict[str, str], k: int | None = None
) -> alt.LayerChart:
    """PnL de cada política dentro del mercado; los baselines van con trazo discontinuo."""
    names = list(colors)
    base = alt.Chart(frame).encode(
        x=alt.X("k:Q", scale=MINUTES, title="Minuto del mercado"),
        y=alt.Y("pnl:Q", title="PnL en este mercado (USDC)"),
        color=alt.Color(
            "politica:N",
            scale=alt.Scale(domain=names, range=list(colors.values())),
            legend=alt.Legend(title=None),
        ),
        strokeDash=alt.StrokeDash(
            "tipo:N",
            scale=alt.Scale(domain=["agente", "baseline"], range=[[1, 0], [6, 4]]),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("politica:N", title="Política"),
            alt.Tooltip("k:Q", title="Minuto"),
            alt.Tooltip("pnl:Q", title="PnL", format="+.2f"),
        ],
    )
    layers = [
        alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=TEXT_2).encode(y="y:Q"),
        base.mark_line(strokeWidth=2.5, interpolate="step-after"),
    ]
    if k is not None:
        layers.append(
            alt.Chart(pd.DataFrame({"k": [k]}))
            .mark_rule(color=AMBER, strokeWidth=2)
            .encode(x="k:Q")
        )
    return styled(alt.LayerChart(layer=layers, height=260))


def cumulative(
    frame: pd.DataFrame, colors: dict[str, str], marker: pd.Timestamp | None
) -> alt.LayerChart:
    """PnL acumulado de cada política en el orden de los mercados."""
    names = list(colors)
    lines = (
        alt.Chart(frame)
        .mark_line(strokeWidth=2.5)
        .encode(
            x=alt.X("inicio:T", title=None, axis=alt.Axis(format="%d/%m")),
            y=alt.Y("acumulado:Q", title="PnL acumulado (USDC)"),
            color=alt.Color(
                "politica:N",
                scale=alt.Scale(domain=names, range=list(colors.values())),
                legend=alt.Legend(title=None),
            ),
            strokeDash=alt.StrokeDash(
                "tipo:N",
                scale=alt.Scale(domain=["agente", "baseline"], range=[[1, 0], [6, 4]]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("politica:N", title="Política"),
                alt.Tooltip("inicio:T", title="Mercado", format="%d/%m/%Y %H:%M UTC"),
                alt.Tooltip("acumulado:Q", title="Acumulado", format="+.2f"),
            ],
        )
    )
    layers = [alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=TEXT_2).encode(y="y:Q"), lines]
    if marker is not None:
        layers.append(
            alt.Chart(pd.DataFrame({"inicio": [marker]}))
            .mark_rule(color=AMBER, strokeWidth=2)
            .encode(x="inicio:T")
        )
    return styled(alt.LayerChart(layer=layers, height=280))


def forest(frame: pd.DataFrame, delta_min: float) -> alt.LayerChart:
    """Media de D con su IC por agente, la línea 0 y la zona de equivalencia de ±Δ_min."""
    domain = ["mejor", "equivalente", "peor, pero no relevante", "inconcluso", "inferior"]
    palette = [GREEN, BLUE, AMBER, "#64748B", RED]
    zone = (
        alt.Chart(pd.DataFrame({"lo": [-delta_min], "hi": [delta_min]}))
        .mark_rect(color=BLUE, opacity=0.07)
        .encode(x="lo:Q", x2="hi:Q")
    )
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=TEXT_2).encode(x="x:Q")
    y = alt.Y("agente:N", title=None, sort=None, axis=alt.Axis(labelFontSize=13))
    color = alt.Color(
        "clasificacion:N",
        scale=alt.Scale(domain=domain, range=palette),
        legend=alt.Legend(title=None),
    )
    interval = (
        alt.Chart(frame)
        .mark_rule(strokeWidth=3)
        .encode(
            x=alt.X("lower:Q", title="D frente a no operar (fracción del monto)"),
            x2="upper:Q",
            y=y,
            color=color,
        )
    )
    point = (
        alt.Chart(frame)
        .mark_point(size=140, filled=True, opacity=1)
        .encode(
            x="mean:Q",
            y=y,
            color=color,
            tooltip=[
                alt.Tooltip("agente:N", title="Agente"),
                alt.Tooltip("mean:Q", title="Media de D", format="+.4f"),
                alt.Tooltip("lower:Q", title="IC inferior", format="+.4f"),
                alt.Tooltip("upper:Q", title="IC superior", format="+.4f"),
                alt.Tooltip("clasificacion:N", title="Clasificación"),
            ],
        )
    )
    return styled(alt.LayerChart(layer=[zone, zero, interval, point], height=230))


def payoff(frame: pd.DataFrame) -> alt.Chart:
    """Aciertos frente a lo mínimo que hay que acertar (el costo por acción), por tramo de "
    "precio."""
    long = frame.melt(
        id_vars=["price", "trades"],
        value_vars=["side_won", "cost"],
        var_name="medida",
        value_name="valor",
    ).replace({"medida": {"side_won": "aciertos", "cost": "necesario para no perder"}})
    return styled(
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X("price:N", title="Precio pagado por el lado comprado", sort=None),
            xOffset="medida:N",
            y=alt.Y(
                "valor:Q", title=None, axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])
            ),
            color=alt.Color(
                "medida:N",
                scale=alt.Scale(
                    domain=["aciertos", "necesario para no perder"], range=[BLUE, "#64748B"]
                ),
                legend=alt.Legend(title=None),
            ),
            tooltip=[
                alt.Tooltip("price:N", title="Tramo"),
                alt.Tooltip("medida:N", title="Medida"),
                alt.Tooltip("valor:Q", title="Valor", format=".2%"),
                alt.Tooltip("trades:Q", title="Compras"),
            ],
        )
        .properties(height=260)
    )


def reward_parts(parts: dict[str, float], color: str) -> alt.Chart:
    """Componentes de la recompensa de un minuto."""
    frame = pd.DataFrame({"componente": list(parts), "valor": list(parts.values())})
    return styled(
        alt.Chart(frame)
        .mark_bar(color=color)
        .encode(
            x=alt.X("valor:Q", title=None),
            y=alt.Y("componente:N", title=None, sort=None),
            tooltip=[
                alt.Tooltip("componente:N", title="Componente"),
                alt.Tooltip("valor:Q", title="Valor", format="+.6f"),
            ],
        )
        .properties(height=160)
    )
