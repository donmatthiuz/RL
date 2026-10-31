"""¿Es realista la ejecución de S4 en un CLOB? Compara el modelo con los trades taker reales.

Uso, desde la raíz del repositorio y con el dataset construido (`make dataset`):

    uv run python notebooks/s4_ejecucion_clob/analisis.py descargar <carpeta>
    uv run python notebooks/s4_ejecucion_clob/analisis.py analizar <carpeta>

`descargar` baja los trades taker públicos de 60 mercados de train repartidos en el tiempo (unos
3 minutos). `analizar` imprime las cifras de la sección 6.2 de `docs/09_sistema_simulacion.md`.
Solo usa train.
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DATASET = Path("data/processed/btc_updown_1h_v1")
MEDIO_SPREAD = 0.01
LATENCIA = 2
TOLERANCIA = 60
ORDEN_USDC = 100


def descargar(carpeta: Path) -> None:
    from polymarket import PublicClient

    markets = pd.read_parquet(DATASET / "markets.parquet")
    train = markets[markets["split"] == "train"].reset_index(drop=True)
    muestra = train.iloc[np.linspace(0, len(train) - 1, 60).astype(int)]
    filas = []
    with PublicClient() as client:
        for mercado in muestra.itertuples():
            trades = client.list_trades(
                condition_id=mercado.market_id, taker_only=True, full_history=True, page_size=500
            )
            for t in trades.iter_items():
                filas.append(
                    {
                        "market_id": mercado.market_id,
                        "ts": int(t.timestamp.timestamp()),
                        "side": t.side,
                        "outcome_index": int(t.outcome_index),
                        "price": float(t.price),
                        "size": float(t.size),
                    }
                )
    carpeta.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas).to_parquet(carpeta / "trades.parquet", index=False)
    muestra[["market_id", "w0", "w1", "spot_open"]].to_parquet(carpeta / "mercados.parquet")
    print(f"{len(filas):,} trades de {len(muestra)} mercados")


def _vwap(trades: pd.DataFrame, t: int) -> tuple[float, float]:
    """VWAP de los primeros ORDEN_USDC en (t + latencia, t + tolerancia] y el flujo total."""
    d = trades[(trades["ts"] > t + LATENCIA) & (trades["ts"] <= t + TOLERANCIA)]
    if d.empty:
        return math.nan, 0.0
    toma = d[d["usdc"].cumsum().shift(fill_value=0) < ORDEN_USDC]
    return (toma["yp"] * toma["size"]).sum() / toma["size"].sum(), float(d["usdc"].sum())


def _comparar(instantes: pd.DataFrame, por_lado: dict, titulo: str) -> None:
    filas = []
    for r in instantes.itertuples():
        trades = por_lado.get((r.market_id, r.lado))
        if trades is None:
            continue
        real, flujo = _vwap(trades, r.t)
        modelo = r.p_next + (MEDIO_SPREAD if r.lado == "BUY" else -MEDIO_SPREAD)
        # Positivo: el modelo le da al agente un precio mejor que el real.
        filas.append((real - modelo if r.lado == "BUY" else modelo - real, flujo))
    res = pd.DataFrame(filas, columns=["diferencia", "flujo"])
    ok = res["diferencia"].notna()
    print(
        f"{titulo}: {len(res):,} órdenes; con trades del lado {ok.mean():.1%}; "
        f"con >= {ORDEN_USDC} USDC {(res['flujo'] >= ORDEN_USDC).mean():.1%}; real - modelo: "
        f"mediana {res['diferencia'][ok].median():.4f}, media {res['diferencia'][ok].mean():.4f}, "
        f"p90 {res['diferencia'][ok].quantile(0.9):.4f}"
    )


def analizar(carpeta: Path) -> None:
    trades = pd.read_parquet(carpeta / "trades.parquet")
    mercados = pd.read_parquet(carpeta / "mercados.parquet")
    precios = pd.read_parquet(DATASET / "prices_raw.parquet")
    precios = precios[(precios["side"] == "yes") & precios["market_id"].isin(mercados["market_id"])]

    # Todo en equivalente YES: comprar NO a y es vender YES a 1 - y.
    es_yes = trades["outcome_index"] == 0
    trades["yp"] = np.where(es_yes, trades["price"], 1 - trades["price"])
    al_reves = np.where(trades["side"] == "BUY", "SELL", "BUY")
    trades["lado"] = np.where(es_yes, trades["side"], al_reves)
    trades["usdc"] = trades["price"] * trades["size"]
    trades = trades.merge(mercados[["market_id", "w0", "w1"]], on="market_id")
    ventana = trades[(trades["ts"] >= trades["w0"]) & (trades["ts"] < trades["w1"])]
    ventana = ventana.sort_values("ts")
    print(f"Trades en la ventana: {len(ventana):,} de {len(trades):,}")

    # 1. ¿El historial es el último trade o un punto medio?
    puntos = precios.merge(mercados[["market_id", "w0", "w1"]], on="market_id")
    puntos = puntos[(puntos["ts_event"] >= puntos["w0"]) & (puntos["ts_event"] < puntos["w1"])]
    puntos = puntos.sort_values("ts_event")[["market_id", "ts_event", "p"]]
    medio_tick = (np.round(puntos["p"] * 10000).astype(int) % 10) == 5
    print(f"Puntos del historial en medio tick: {medio_tick.mean():.1%}")
    comp = puntos
    for lado, columna in ((None, "ultimo"), ("BUY", "compra"), ("SELL", "venta")):
        fuente = ventana if lado is None else ventana[ventana["lado"] == lado]
        comp = pd.merge_asof(
            comp,
            fuente[["market_id", "ts", "yp"]].rename(
                columns={"ts": f"ts_{columna}", "yp": columna}
            ),
            left_on="ts_event",
            right_on=f"ts_{columna}",
            by="market_id",
            direction="backward",
            tolerance=TOLERANCIA,
        )
    comp = comp.dropna(subset=["ultimo", "compra", "venta"])
    medio = (comp["compra"] + comp["venta"]) / 2
    print(
        f"Igual al último trade: {((comp['p'] - comp['ultimo']).abs() <= 0.0005).mean():.1%}; "
        f"igual al medio entre la última compra y la última venta: "
        f"{((comp['p'] - medio).abs() <= 0.0005).mean():.1%}"
    )

    # 2. Liquidez: USDC tomado por minuto y lado.
    ventana = ventana.assign(k=(ventana["ts"] - ventana["w0"]) // 60)
    flujo = ventana.groupby(["market_id", "k", "lado"])["usdc"].sum().unstack(fill_value=0)
    todos = pd.MultiIndex.from_product([mercados["market_id"], range(60)], names=["market_id", "k"])
    flujo = flujo.reindex(todos, fill_value=0)
    for lado in ("BUY", "SELL"):
        print(
            f"Flujo {lado}: minutos con >= {ORDEN_USDC} USDC "
            f"{(flujo[lado] >= ORDEN_USDC).mean():.1%}; "
            f"mediana {flujo[lado].median():.0f} USDC por minuto"
        )

    # 3. Modelo frente a la ejecución real: todos los minutos y los que la regla de edge opera.
    grilla = mercados[["market_id", "w0", "spot_open"]].merge(
        pd.DataFrame({"k": range(5, 56)}), how="cross"
    )
    grilla["t"] = grilla["w0"] + 60 * grilla["k"]
    grilla = pd.merge_asof(
        grilla.assign(q=grilla["t"] + LATENCIA).sort_values("q"),
        puntos.rename(columns={"ts_event": "ts_next", "p": "p_next"}),
        left_on="q",
        right_on="ts_next",
        by="market_id",
        direction="forward",
        allow_exact_matches=False,
        tolerance=TOLERANCIA - LATENCIA,
    ).dropna(subset=["p_next"])
    por_lado = {clave: d for clave, d in ventana.groupby(["market_id", "lado"])}
    ambos = pd.concat([grilla.assign(lado="BUY"), grilla.assign(lado="SELL")])
    _comparar(ambos, por_lado, "Todos los minutos")

    spot = pd.read_parquet(DATASET / "spot_1m.parquet").sort_values("ts_available")
    spot["sigma"] = np.log(spot["close"]).diff().rolling(60).std()
    g = pd.merge_asof(
        grilla.sort_values("t"),
        puntos.rename(columns={"ts_event": "ts_cur", "p": "p_cur"}),
        left_on="t",
        right_on="ts_cur",
        by="market_id",
        direction="backward",
    )
    g = pd.merge_asof(
        g.sort_values("t"),
        spot[["ts_available", "close", "sigma"]],
        left_on="t",
        right_on="ts_available",
        direction="backward",
    )
    z = (np.log(g["close"] / g["spot_open"]) / (g["sigma"] * np.sqrt(60 - g["k"]))).clip(-5, 5)
    g["edge"] = 0.5 * (1 + z.map(lambda v: math.erf(v / math.sqrt(2)))) - g["p_cur"]
    g = g[g["edge"].abs() > 0.05]
    _comparar(g.assign(lado=np.where(g["edge"] > 0, "BUY", "SELL")), por_lado, "Con |edge| > 0,05")


if __name__ == "__main__":
    accion, carpeta = sys.argv[1], Path(sys.argv[2])
    {"descargar": descargar, "analizar": analizar}[accion](carpeta)
