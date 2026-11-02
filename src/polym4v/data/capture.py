"""Captura del historial crudo de precios de una serie de mercados (DAT-10, ADR-013).

Cada respuesta se guarda tal cual, comprimida y con la petición que la produjo. Si el
archivo ya existe no se vuelve a pedir, así que repetir la captura no usa la red.
"""

import gzip
import hashlib
import json
import os
import re
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import httpx
from polymarket import TransportError

CLOB_PRICES_HISTORY = "https://clob.polymarket.com/prices-history"
HOUR = 3600
# Contexto previo a la vela y margen posterior al cierre (ventana amplia, ADR-013).
BEFORE_S = 6 * HOUR
AFTER_S = 2 * HOUR

_ET = ZoneInfo("America/New_York")
_MONTHS = {
    name: number
    for number, name in enumerate(
        (
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ),
        start=1,
    )
}
_DAY = re.compile(r"(" + "|".join(_MONTHS) + r")\s+(\d{1,2})")
_HOUR = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([ap])m\s*et")


class EventSource(Protocol):
    def list_events(
        self,
        *,
        series_ids: int,
        closed: bool,
        order: str,
        ascending: bool,
        page_size: int,
    ) -> Any: ...


def parse_window_start(title: str, end_date: datetime) -> int | None:
    """Inicio de la vela en segundos unix, leído del título en hora de Nueva York.

    El título no trae el año; se toma el de end_date, que en mercados antiguos no marca
    el fin de la ventana pero sí cae a menos de dos días de ella.
    """
    text = title.lower()
    day, hour = _DAY.search(text), _HOUR.search(text)
    if day is None or hour is None:
        return None
    clock = int(hour.group(1)) % 12 + (12 if hour.group(3) == "p" else 0)
    start = datetime(
        end_date.year,
        _MONTHS[day.group(1)],
        int(day.group(2)),
        clock,
        int(hour.group(2) or 0),
        tzinfo=_ET,
    )
    if start > end_date + timedelta(days=2):
        start = start.replace(year=end_date.year - 1)
    return int(start.timestamp())


class RawStore:
    """Archivos crudos bajo una raíz, uno por evento y uno por token."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def price_path(self, token_id: str) -> Path:
        return self.root / "clob" / "prices-history" / f"{token_id}.json.gz"

    def event_path(self, series_id: int, event_id: str) -> Path:
        return self.root / "gamma" / "events" / str(series_id) / f"{event_id}.json.gz"

    def kline_path(self, symbol: str, interval: str, label: str) -> Path:
        return self.root / "binance" / "klines" / symbol / interval / f"{label}.json.gz"

    def write(self, path: Path, payload: dict[str, Any]) -> None:
        """Escribe de forma atómica; mtime=0 deja bytes estables para el hash."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = gzip.compress(json.dumps(payload, ensure_ascii=False).encode(), mtime=0)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)

    def files(self) -> list[Path]:
        return sorted(self.root.rglob("*.json.gz"))


def get_with_retries(
    http: httpx.Client,
    url: str,
    params: dict[str, Any],
    sleep: Callable[[float], None],
    retries: int = 4,
) -> tuple[int, Any]:
    """Reintenta ante 429, errores 5xx y fallas de red, con espera exponencial."""
    status, body = 0, None
    for attempt in range(retries):
        try:
            response = http.get(url, params=params)
        except httpx.TransportError as exc:
            status, body = 0, type(exc).__name__
        else:
            status = response.status_code
            if status == 200:
                return status, response.json()
            body = response.text[:200]
            if status != 429 and status < 500:
                break
        sleep(2.0**attempt)
    return status, body


def _iter_events(
    paginator: Any, sleep: Callable[[float], None], summary: dict[str, Any], retries: int = 4
) -> Iterator[Any]:
    """Recorre las páginas de Gamma; ante una falla de red repite la misma página.

    El SDK solo reintenta los 429, así que sin esto una caída de red a mitad del listado
    corta toda la captura.
    """
    cursor = None
    while True:
        for attempt in range(retries):
            try:
                page = (
                    paginator.from_cursor(cursor).first_page() if cursor else paginator.first_page()
                )
                break
            except TransportError:
                if attempt == retries - 1:
                    raise
                sleep(2.0**attempt)
        yield from page.items
        if page.limit_reached:
            summary["limit_reached"] = True
        if page.limit_reached or not page.has_more:
            return
        cursor = page.next_cursor


def capture_series(
    series_id: int,
    store: RawStore,
    *,
    gamma: EventSource,
    http: httpx.Client,
    sleep: Callable[[float], None] = time.sleep,
    pause: float = 0.2,
    limit: int | None = None,
    on_event: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """Descarga el historial de los tokens YES y NO de cada mercado cerrado de la serie."""
    summary: dict[str, Any] = {
        "series_id": series_id,
        "events": 0,
        "downloaded": 0,
        "cached": 0,
        "errors": [],
        "limit_reached": False,
    }
    paginator = gamma.list_events(
        series_ids=series_id,
        closed=True,
        order="endDate",
        ascending=True,
        page_size=50,
    )
    events = _iter_events(paginator, sleep, summary)
    for event in events:
        if limit is not None and summary["events"] >= limit:
            break
        summary["events"] += 1
        event_id = str(event.id)
        event_file = store.event_path(series_id, event_id)
        if not event_file.exists():
            store.write(event_file, event.model_dump(mode="json"))
        if not event.markets:
            summary["errors"].append({"event_id": event_id, "error": "sin mercados"})
            continue
        market = event.markets[0]
        end = market.state.end_date
        w0 = parse_window_start(event.title, end)
        if w0 is not None:
            window, source = (w0 - BEFORE_S, w0 + AFTER_S), "titulo"
        else:
            last = market.state.closed_time or end
            window = (int(end.timestamp()) - 48 * HOUR, int(last.timestamp()) + HOUR)
            source = "respaldo"
        for outcome in (market.outcomes.yes, market.outcomes.no):
            token = outcome.token_id
            if token is None:
                continue
            path = store.price_path(str(token))
            if path.exists():
                summary["cached"] += 1
                continue
            params = {"market": str(token), "startTs": window[0], "endTs": window[1], "fidelity": 1}
            status, body = get_with_retries(http, CLOB_PRICES_HISTORY, params, sleep)
            if status != 200:
                summary["errors"].append(
                    {"event_id": event_id, "token_id": str(token), "status": status, "detail": body}
                )
                continue
            store.write(
                path,
                {
                    "request": {"url": CLOB_PRICES_HISTORY, "params": params},
                    "fetched_at": datetime.now(UTC).isoformat(),
                    "status": status,
                    "event_id": event_id,
                    "window_source": source,
                    "body": body,
                },
            )
            summary["downloaded"] += 1
            sleep(pause)
        if on_event is not None:
            on_event(summary["events"])
    return summary


def write_manifest(store: RawStore) -> dict[str, Any]:
    """Lista cada archivo crudo con su tamaño y hash SHA-256."""
    files = []
    for path in store.files():
        data = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(store.root).as_posix(),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "n_files": len(files),
        "files": files,
    }
    (store.root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
