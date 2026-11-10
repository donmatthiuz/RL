"""Política y mercado elegidos, compartidos entre las páginas de simulación y comparación.

Los widgets cambian claves propias (`w_*`) y sus callbacks copian el valor a claves que no son de
widgets (`sel_*`), porque Streamlit borra el estado de los widgets de una página que no se dibuja.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from core import (
    file_name,
    first_traded,
    label_of,
    list_files,
    load,
    markets,
    pretty,
    protocol_pick,
    split_of,
)


@dataclass
class Selection:
    files: dict[str, Path]
    choice: str
    split: str
    trajectories: pd.DataFrame
    by_market: dict[str, pd.DataFrame]
    market_id: str
    info: (
        pd.DataFrame | None
    )  # BTC por minuto y datos del mercado; None si no hay muestra ni dataset


def stop() -> None:
    st.session_state.playing = False


def restart() -> None:
    st.session_state.step = 0
    stop()


def _sync(widget: str, target: str) -> None:
    st.session_state[target] = st.session_state[widget]
    restart()


@st.cache_data(max_entries=64)
def split_by_market(path: str, mtime: float) -> dict[str, pd.DataFrame]:
    frame = load(path, mtime)
    return {
        market_id: steps.reset_index(drop=True)
        for market_id, steps in frame.groupby("market_id", sort=False)
    }


@st.cache_data(max_entries=64)
def traded(path: str, mtime: float) -> set[str]:
    frame = load(path, mtime)
    return set(frame.loc[frame["order_status"] == "ejecutada", "market_id"])


def folder_input() -> None:
    with st.sidebar.expander("Carpeta de trayectorias"):
        st.text_input(
            "Carpeta",
            key="w_folder",
            value=st.session_state.folder,
            on_change=_sync,
            args=("w_folder", "folder"),
            help="Parquet que dejan `make backtest` y `polym4v evaluate`. Sin ellos, la demo usa "
            "la muestra de test de app/trayectorias/.",
        )


def policy_label(name: str) -> str:
    strict = " · estricto" if name.endswith("estricto") else ""
    return f"{pretty(label_of(name))} · {split_of(name)}{strict}"


def select() -> Selection | None:
    """Dibuja la selección en la barra lateral; None si la carpeta no tiene trayectorias."""
    files = list_files(Path(st.session_state.folder))
    if not files:
        st.info(
            f"No hay trayectorias en {st.session_state.folder}. Genera algunas con "
            "`make backtest` o `polym4v evaluate`, o cambia la carpeta en la barra lateral."
        )
        return None

    names = list(files)
    if st.session_state.get("sel_policy") not in files:
        picks = protocol_pick("test", names) or protocol_pick("val", names)
        st.session_state.sel_policy = picks[0] if picks else names[0]
        st.session_state.pop("sel_market", None)
    st.session_state.w_policy = st.session_state.sel_policy
    choice = st.sidebar.selectbox(
        "Política",
        names,
        key="w_policy",
        format_func=policy_label,
        on_change=_sync,
        args=("w_policy", "sel_policy"),
    )
    path, mtime = str(files[choice]), files[choice].stat().st_mtime
    by_market = split_by_market(path, mtime)
    market_ids = list(by_market)
    operated = traded(path, mtime)
    if st.session_state.get("sel_market") not in by_market:
        st.session_state.sel_market = market_ids[first_traded(by_market)]

    def market_label(market_id: str) -> str:
        start = pd.to_datetime(by_market[market_id]["ts"].iloc[0], unit="s", utc=True)
        mark = " · operó" if market_id in operated else ""
        return f"{start:%d/%m/%Y %H:%M} UTC{mark}"

    st.session_state.w_market = st.session_state.sel_market
    market_id = st.sidebar.selectbox(
        "Mercado",
        market_ids,
        key="w_market",
        format_func=market_label,
        on_change=_sync,
        args=("w_market", "sel_market"),
    )
    if operated:
        st.sidebar.button(
            "Siguiente mercado donde operó",
            icon=":material/skip_next:",
            on_click=_next_traded,
            args=(market_ids, operated),
            width="stretch",
        )
    st.sidebar.caption(f"{len(operated)} de {len(market_ids)} mercados con alguna orden ejecutada.")

    split = split_of(choice)
    info = markets(split)
    if info is not None:
        info = info[info["market_id"] == market_id]
        info = info if len(info) else None
    return Selection(files, choice, split, load(path, mtime), by_market, market_id, info)


def _next_traded(market_ids: list[str], operated: set[str]) -> None:
    start = market_ids.index(st.session_state.sel_market)
    for market_id in market_ids[start + 1 :] + market_ids[: start + 1]:
        if market_id in operated:
            st.session_state.sel_market = market_id
            break
    restart()


def others(selection: Selection) -> list[str]:
    """Otras políticas del mismo split, en modo normal o estricto según la elegida."""
    strict = selection.choice.endswith("estricto")
    return [
        name
        for name in selection.files
        if name != selection.choice
        and split_of(name) == selection.split
        and name.endswith("estricto") == strict
    ]


def default_others(selection: Selection) -> list[str]:
    """El mejor agente y su baseline del protocolo, más `fair_value`, la mejor heurística."""
    options = others(selection)
    picked = protocol_pick(selection.split, options)
    heuristic = file_name("fair_value", selection.split, False)
    if heuristic in options and heuristic not in picked:
        picked.append(heuristic)
    return picked
