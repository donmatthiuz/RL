"""Una hora de mercado con la política elegida, minuto a minuto (EVA-13).

Reproduce la trayectoria grabada: no vuelve a correr la política. El bloque que cambia con cada
minuto es un fragment; mientras se reproduce, se vuelve a dibujar solo cada `SPEEDS` segundos.
"""

import pandas as pd
import streamlit as st

import charts
from core import ACTIONS, Action, card, color, kind, label_of, pretty, simulator
from selection import Selection, select, stop

SPEEDS = {"Lenta": 1.0, "Normal": 0.5, "Rápida": 0.25}
SIDES = {1: "YES", -1: "NO"}
INVALID = "en los últimos 2 minutos no se abren posiciones"


def clock(ts: float) -> str:
    return f"{pd.to_datetime(ts, unit='s', utc=True):%H:%M} UTC"


def held(steps: pd.DataFrame, k: int) -> tuple[int, float]:
    """Lado y acciones con que se llega al minuto `k` (antes de su orden)."""
    if k == 0:
        return 0, 0.0
    row = steps.iloc[k - 1]
    return int(row["position_side"]), float(row["position_size"])


def why_invalid(action: Action, side: int, k: int, last: int) -> str:
    if action == Action.SELL and side == 0:
        return "no tiene nada que vender"
    if action in (Action.BUY_YES, Action.BUY_NO) and side != 0:
        return "ya tiene una posición abierta"
    if k >= last - 1:
        return INVALID
    return "la acción no se puede ejecutar en este estado"


def narrate(steps: pd.DataFrame, k: int, info: pd.DataFrame | None, stake: float) -> str:
    """Qué pasa en el minuto `k`, en una frase para alguien que no conoce el entorno."""
    row = steps.iloc[k]
    lead = f"YES vale {row['p_yes']:.4f}"
    if info is not None:
        spot, opening = info["spot"].iloc[k], info["spot_open"].iloc[0]
        lead += f" y BTC está {change(spot, opening):+.3%} frente a la apertura"
    lead += "."
    side, shares = held(steps, k)
    action = Action(int(row["action"]))
    status = row["order_status"]
    if status == "ejecutada":
        executed = Action(int(row["action_executed"]))
        if executed == Action.SELL:
            got = row["fill_shares"] * row["fill_price"] - row["fee"]
            return (
                f"{lead} El agente **vende** sus {row['fill_shares']:.2f} acciones {SIDES[side]} a "
                f"{row['fill_price']:.4f} y recibe {got:.2f} USDC (comisión {row['fee']:.5f})."
            )
        paid = row["fill_shares"] * row["fill_price"] + row["fee"]
        bought = SIDES[1 if executed == Action.BUY_YES else -1]
        return (
            f"{lead} El agente **compra {bought}**: paga {paid:.2f} USDC por "
            f"{row['fill_shares']:.2f} acciones a {row['fill_price']:.4f} (precio del lado más "
            f"medio spread) y {row['fee']:.5f} de comisión. Si gana {bought}, cada acción paga "
            f"1 USDC: {row['fill_shares']:.2f} USDC."
        )
    if status == "invalida":
        reason = why_invalid(action, side, k, len(steps) - 1)
        return f"{lead} Pidió **{ACTIONS[action]}**, pero {reason}: espera."
    if status == "sin_precio":
        return (
            f"{lead} Pidió **{ACTIONS[action]}**, pero no hubo precio en el minuto siguiente a "
            "t + 2 s: la orden no se ejecuta."
        )
    if side:
        value = shares * (row["p_yes"] if side == 1 else 1 - row["p_yes"])
        return (
            f"{lead} El agente **espera** con {shares:.2f} acciones {SIDES[side]}, que hoy valen "
            f"{value:.2f} USDC a precio de mercado."
        )
    return f"{lead} El agente **espera** sin posición."


def _waited(first: int, last: int, refused: int) -> str:
    span = f"Minutos {first} a {last}" if last > first else f"Minuto {first}"
    if refused:
        asks = "pedido que no se puede" if refused == 1 else "pedidos que no se pueden"
        return f"{span}: espera ({refused} {asks})"
    return f"{span}: espera"


def events(steps: pd.DataFrame, k: int) -> list[str]:
    """Órdenes ejecutadas o sin precio hasta `k`; las esperas y los pedidos inválidos, agrupados."""
    found: list[str] = []
    waiting, refused = None, 0
    end = min(k, len(steps) - 2)
    for i in range(end + 1):
        row = steps.iloc[i]
        status = row["order_status"]
        if status in ("ninguna", "invalida"):
            waiting = i if waiting is None else waiting
            refused += status == "invalida"
            continue
        if waiting is not None:
            found.append(_waited(waiting, i - 1, refused))
            waiting, refused = None, 0
        if status == "ejecutada":
            executed = Action(int(row["action_executed"]))
            found.append(
                f"Minuto {i}: {ACTIONS[executed]} a {row['fill_price']:.4f}, "
                f"{row['fill_shares']:.2f} acciones"
            )
        else:
            found.append(f"Minuto {i}: pidió {ACTIONS[Action(int(row['action']))]}, sin precio")
    if waiting is not None:
        found.append(_waited(waiting, end, refused))
    return found


def closing(
    steps: pd.DataFrame, info: pd.DataFrame | None, initial_cash: float, stake: float
) -> None:
    """Resultado del mercado, liquidación y PnL de la hora."""
    final = steps.iloc[-1]
    side, shares = held(steps, len(steps) - 1)
    pnl = final["portfolio_value"] - initial_cash
    with card("cierre"):
        if info is not None:
            close, opening = info["spot_close"].iloc[0], info["spot_open"].iloc[0]
            won = int(info["outcome"].iloc[0])
            st.markdown(
                f"#### BTC cerró en {close:,.2f} ({close / opening - 1:+.3%} frente a la "
                "apertura): "
                f"gana **{':green[UP]' if won else ':red[DOWN]'}**"
            )
        else:
            won = None
        if side:
            pays = (side == 1) == bool(won) if won is not None else None
            if pays:
                st.markdown(
                    f"Las {shares:.2f} acciones {SIDES[side]} pagan 1 USDC cada una: "
                    f"**{shares:.2f} USDC**."
                )
            elif pays is False:
                st.markdown(f"Las {shares:.2f} acciones {SIDES[side]} no pagan nada.")
        trades = int((steps["order_status"] == "ejecutada").sum())
        tone = "green" if pnl > 0 else "red" if pnl < 0 else "gray"
        st.markdown(
            f"### :{tone}[{pnl:+.2f} USDC] en la hora · {pnl / stake:+.1%} del monto de "
            f"{stake:.0f} USDC"
        )
        if trades == 0:
            st.caption("No operó.")
        elif side and pnl < 0 and won is not None and (side == 1) == bool(won):
            st.caption("Acertó el lado, pero los costos superaron el pago.")
        elif side and pnl > 0:
            cost = stake / shares
            st.caption(f"Pagó {cost:.4f} por acción y cobró 1.")
        st.caption(f"Comisiones: {final['fees_paid']:.4f} USDC · órdenes: {trades}.")


def change(value: float, reference: float) -> float:
    """Cambio relativo sin el -0,000 % que deja el redondeo."""
    ratio = value / reference - 1
    return 0.0 if abs(ratio) < 5e-6 else ratio


def kpis(steps: pd.DataFrame, k: int, info: pd.DataFrame | None, initial_cash: float) -> None:
    row = steps.iloc[k]
    last = len(steps) - 1
    cols = st.columns(6)
    cols[0].metric(
        "Hora (UTC)",
        f"{pd.to_datetime(row['ts'], unit='s', utc=True):%H:%M}",
        f"minuto {k}",
        delta_color="off",
        delta_arrow="off",
        border=True,
        height="stretch",
    )
    if info is not None:
        spot, opening = info["spot"].iloc[k], info["spot_open"].iloc[0]
        cols[1].metric(
            "BTC",
            f"{spot:,.0f}",
            f"{change(spot, opening):+.3%}",
            help="Cambio frente al precio de apertura de la hora.",
            border=True,
            height="stretch",
        )
    else:
        cols[1].metric("BTC", "sin datos", border=True, height="stretch")
    moved = row["p_yes"] - steps.iloc[k - 1]["p_yes"] if k else None
    cols[2].metric(
        "Precio YES",
        f"{row['p_yes']:.4f}",
        None if moved is None else f"{moved:+.4f}",
        border=True,
        height="stretch",
    )
    if k == last:
        side, detail = "liquidada", "al cierre"
    elif row["position_side"]:
        side, detail = SIDES[int(row["position_side"])], f"{row['position_size']:.2f} acciones"
    else:
        side, detail = "ninguna", "sin acciones"
    cols[3].metric(
        "Posición",
        side,
        detail,
        delta_color="off",
        delta_arrow="off",
        border=True,
        height="stretch",
    )
    value = row["portfolio_value"]
    cols[4].metric(
        "Cartera (USDC)",
        f"{value:,.2f}",
        f"{value - initial_cash:+.2f}",
        border=True,
        height="stretch",
    )
    cols[5].metric(
        "Comisiones",
        f"{row['fees_paid']:.4f}",
        "USDC",
        delta_color="off",
        delta_arrow="off",
        border=True,
        height="stretch",
    )


def move(delta: int, last: int) -> None:
    st.session_state.step = min(max(st.session_state.step + delta, 0), last)
    stop()


def jump(k: int) -> None:
    st.session_state.step = k
    stop()


def play(last: int) -> None:
    if st.session_state.step >= last:
        st.session_state.step = 0
    st.session_state.playing = True


def slid() -> None:
    st.session_state.step = st.session_state.w_step
    stop()


def controls(last: int) -> None:
    row = st.container(horizontal=True, vertical_alignment="center")
    row.button("Reiniciar", icon=":material/replay:", on_click=jump, args=(0,))
    row.button("Minuto anterior", icon=":material/chevron_left:", on_click=move, args=(-1, last))
    if st.session_state.playing:
        row.button("Pausar", icon=":material/pause:", type="primary", on_click=stop)
    else:
        row.button(
            "Reproducir", icon=":material/play_arrow:", type="primary", on_click=play, args=(last,)
        )
    row.button("Minuto siguiente", icon=":material/chevron_right:", on_click=move, args=(1, last))
    row.button("Ir al cierre", icon=":material/skip_next:", on_click=jump, args=(last,))
    row.segmented_control(
        "Velocidad",
        list(SPEEDS),
        key="w_speed",
        default=st.session_state.speed,
        on_change=lambda: st.session_state.update(speed=st.session_state.w_speed or "Normal"),
        label_visibility="collapsed",
    )


def board(selection: Selection, initial_cash: float, stake: float) -> None:
    """Lo que cambia con cada minuto. Avanza solo si se está reproduciendo."""
    steps = selection.by_market[selection.market_id]
    last = len(steps) - 1
    if st.session_state.ticking and not st.session_state.playing:
        st.session_state.ticking = False
        st.rerun()
    if st.session_state.playing:
        if st.session_state.step < last:
            st.session_state.step += 1
        if st.session_state.step >= last:
            stop()
            st.rerun()
    k = min(st.session_state.step, last)
    st.session_state.w_step = k
    st.slider("Minuto", 0, last, key="w_step", on_change=slid, label_visibility="collapsed")
    kpis(steps, k, selection.info, initial_cash)

    chart, log = st.columns([2.2, 1], gap="medium")
    with chart, card("grafico"):
        spot = None
        if selection.info is not None:
            spot = selection.info[["k", "spot"]].reset_index(drop=True)
        opening = selection.info["spot_open"].iloc[0] if selection.info is not None else None
        for panel in charts.market(spot, steps, k, opening):
            st.altair_chart(
                panel, width="stretch", theme=None, alt="Precio de BTC y precio YES con las órdenes"
            )
    with log, card("registro"):
        st.markdown("**Registro**")
        lines = events(steps, k)
        if k == last:
            lines.append(f"Minuto {last}: cierre y liquidación")
        for i, text in enumerate(reversed(lines)):
            st.markdown(f"**{text}**" if i == 0 else f":gray[{text}]")

    if k < last:
        st.info(
            narrate(steps, k, selection.info, stake),
            title=f"Minuto {k} · {clock(steps.iloc[k]['ts'])}",
            icon=":material/schedule:",
        )
    else:
        closing(steps, selection.info, initial_cash, stake)


selection = select()
if selection is None:
    st.stop()
initial_cash, stake = simulator()
steps = selection.by_market[selection.market_id]
label = label_of(selection.choice)

head, badge = st.columns([5, 1], vertical_alignment="bottom")
question = selection.info["question"].iloc[0] if selection.info is not None else selection.market_id
start = pd.to_datetime(steps["ts"].iloc[0], unit="s", utc=True)
head.markdown(f"## {question}")
head.caption(
    f"{start:%d/%m/%Y} · {start:%H:%M} a {start + pd.Timedelta(hours=1):%H:%M} UTC · "
    f"saldo inicial {initial_cash:,.0f} USDC · {stake:.0f} USDC por orden · split {selection.split}"
)
badge.badge(pretty(label), color="blue" if kind(label) in ("ppo", "dqn", "cql", "bc") else "gray")

controls(len(steps) - 1)
st.session_state.ticking = st.session_state.playing
st.fragment(run_every=SPEEDS[st.session_state.speed] if st.session_state.playing else None)(board)(
    selection, initial_cash, stake
)

with st.expander("Qué recibió el agente como recompensa en este minuto"):
    k = min(st.session_state.step, len(steps) - 1)
    row = steps.iloc[k]
    parts = {name: row[f"r_{name}"] for name in ("pnl", "drawdown", "hold", "invalid", "terminal")}
    st.altair_chart(
        charts.reward_parts(parts, color(label)),
        width="stretch",
        theme=None,
        alt="Componentes de la recompensa del minuto",
    )
    st.caption("`pnl_risk`: cambio del valor de la cartera menos la caída desde el máximo.")
