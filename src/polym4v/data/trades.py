"""Captura de los trades taker públicos de un conjunto de mercados (DAT-11, S4b, ADR-017).

Sirven para validar cada ejecución simulada en val y test (EVA-11): no entran en la observación
ni en el entrenamiento. Cada mercado se guarda en un archivo, con la petición que lo produjo, y si
el archivo ya existe no se vuelve a pedir.

De cada trade se guardan solo los campos del mercado y de la operación. Los datos de la cuenta
(billetera, nombre, seudónimo, biografía e imágenes) no hacen falta y no se guardan; el hash de la
transacción alcanza para rastrear cada trade.
"""

import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Any, Protocol

from polymarket import PolymarketError

from .capture import AFTER_S, BEFORE_S, RawStore, iter_pages

DATA_TRADES = "/v2/trades"
PAGE_SIZE = 1000
TRADE_FIELDS = (
    "condition_id",
    "asset_id",
    "outcome",
    "outcome_index",
    "side",
    "price",
    "size",
    "timestamp",
    "transaction_hash",
)


class TradeSource(Protocol):
    def list_trades(
        self,
        *,
        condition_id: str,
        taker_only: bool,
        start: int,
        end: int,
        page_size: int,
    ) -> Any: ...


def _fields(trade: Any) -> dict[str, Any]:
    data = trade.model_dump(mode="json")
    return {key: data[key] for key in TRADE_FIELDS}


def capture_trades(
    markets: Iterable[tuple[str, int]],
    store: RawStore,
    *,
    client: TradeSource,
    sleep: Callable[[float], None] = time.sleep,
    pause: float = 0.2,
    on_market: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """Descarga los trades taker de cada `(market_id, w0)` en la misma ventana que los precios.

    La ventana amplia (`w0 - 6 h` a `w0 + 2 h`) es la de DAT-10 y cubre el 99,6 % de los trades
    de una muestra de train; el 96 % cae dentro de la vela.
    """
    summary: dict[str, Any] = {
        "markets": 0,
        "downloaded": 0,
        "cached": 0,
        "trades": 0,
        "errors": [],
        "limit_reached": [],
    }
    for market_id, w0 in markets:
        summary["markets"] += 1
        path = store.trades_path(market_id)
        if path.exists():
            summary["cached"] += 1
        else:
            start, end = int(w0) - BEFORE_S, int(w0) + AFTER_S
            params = {"condition_id": market_id, "taker_only": True, "start": start, "end": end}
            pages: dict[str, Any] = {"limit_reached": False}
            try:
                paginator = client.list_trades(
                    condition_id=market_id,
                    taker_only=True,
                    start=start,
                    end=end,
                    page_size=PAGE_SIZE,
                )
                trades = [_fields(trade) for trade in iter_pages(paginator, sleep, pages)]
            except PolymarketError as exc:
                summary["errors"].append({"market_id": market_id, "error": type(exc).__name__})
                continue
            if pages["limit_reached"]:
                summary["limit_reached"].append(market_id)
            store.write(
                path,
                {
                    "request": {"service": "data", "path": DATA_TRADES, "params": params},
                    "fetched_at": datetime.now(UTC).isoformat(),
                    "limit_reached": pages["limit_reached"],
                    "body": trades,
                },
            )
            summary["downloaded"] += 1
            summary["trades"] += len(trades)
            sleep(pause)
        if on_market is not None:
            on_market(summary["markets"])
    return summary
