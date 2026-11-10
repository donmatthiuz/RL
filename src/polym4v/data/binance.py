"""Captura de klines de Binance al crudo (DAT-03).

Igual que la captura de Polymarket: una respuesta por archivo, con la petición que la produjo, y
si el archivo existe no se vuelve a pedir. Solo se piden bloques ya cerrados, para no guardar una
vela a medio formar.
"""

import time
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from .capture import HOUR, RawStore, get_with_retries

BINANCE_KLINES = "https://data-api.binance.vision/api/v3/klines"
# Cada bloque cabe en una petición (máximo 1000 filas): 720 klines de 1m o 24 de 1h.
BLOCK_SECONDS = {"1m": 12 * HOUR, "1h": 24 * HOUR}


def kline_blocks(interval: str, start: date, end: date) -> Iterator[tuple[str, int, int]]:
    """Bloques `[inicio, fin)` alineados a la medianoche UTC que cubren de `start` a `end`."""
    step = BLOCK_SECONDS[interval]
    first = datetime(start.year, start.month, start.day, tzinfo=UTC)
    last = int(datetime(end.year, end.month, end.day, tzinfo=UTC).timestamp())
    b0 = int(first.timestamp())
    while b0 < last:
        label = datetime.fromtimestamp(b0, UTC).strftime("%Y-%m-%dT%H")
        yield label, b0, b0 + step
        b0 += step


def capture_klines(
    symbol: str,
    interval: str,
    start: date,
    end: date,
    store: RawStore,
    *,
    http: httpx.Client,
    sleep: Callable[[float], None] = time.sleep,
    pause: float = 0.1,
    now: float | None = None,
) -> dict[str, Any]:
    """Descarga las klines de `symbol` entre `start` y `end` (sin incluirlo)."""
    now = time.time() if now is None else now
    summary: dict[str, Any] = {
        "symbol": symbol,
        "interval": interval,
        "downloaded": 0,
        "cached": 0,
        "pending": 0,
        "errors": [],
    }
    for label, b0, b1 in kline_blocks(interval, start, end):
        path = store.kline_path(symbol, interval, label)
        if path.exists():
            summary["cached"] += 1
            continue
        if b1 > now:
            summary["pending"] += 1
            continue
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": b0 * 1000,
            "endTime": b1 * 1000 - 1,
            "limit": 1000,
        }
        status, body = get_with_retries(http, BINANCE_KLINES, params, sleep)
        if status != 200:
            summary["errors"].append({"block": label, "status": status, "detail": body})
            continue
        store.write(
            path,
            {
                "request": {"url": BINANCE_KLINES, "params": params},
                "fetched_at": datetime.now(UTC).isoformat(),
                "status": status,
                "body": body,
            },
        )
        summary["downloaded"] += 1
        sleep(pause)
    return summary


def spot_range(date_from: date, date_to: date) -> tuple[date, date]:
    """Días UTC que cubren las ventanas de la config y su contexto previo.

    Las ventanas se fechan en hora de Nueva York, así que la primera puede necesitar el día UTC
    anterior y la última termina al día UTC siguiente.
    """
    return date_from - timedelta(days=1), date_to + timedelta(days=2)
