"""Construcción del dataset procesado desde el crudo (DAT-04 y DAT-05, sin `steps`).

Solo lee `data/raw/`: no llama a la red. Escribe `markets`, `prices_raw` y `spot_1m`, validados con
los contratos de `schemas.py`, y un manifest con el hash de cada archivo y los mercados
descartados con su motivo. `steps.parquet` se agrega cuando se decidan S3 y S4.
"""

import gzip
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

import pandas as pd

from ..utils.config import DataConfig
from .capture import RawStore, parse_window_start
from .schemas import KLINE_SECONDS, Market, PriceTick, SpotKline
from .splits import SplitExclusions, assign_splits

KLINE_COLUMNS = ["ts_event", "open", "high", "low", "close", "volume"]


def _read(path: Path) -> Any:
    return json.loads(gzip.decompress(path.read_bytes()))


def _utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def parse_market(event: dict[str, Any], window_s: int) -> dict[str, Any] | str:
    """Datos del mercado que vienen de Gamma, o el motivo para descartarlo."""
    if not event.get("markets"):
        return "sin mercados"
    market = event["markets"][0]
    w0 = parse_window_start(event["title"], _utc(market["state"]["end_date"]))
    if w0 is None:
        return "ventana ilegible"
    yes, no = market["outcomes"]["yes"], market["outcomes"]["no"]
    prices = (float(yes["price"]), float(no["price"]))
    if prices not in ((1.0, 0.0), (0.0, 1.0)):
        return "resultado sin resolver"
    trading = market["trading"]
    schedule = trading.get("fee_schedule") or {}
    return {
        "market_id": market["condition_id"],
        "slug": market["slug"],
        "question": market["question"],
        "yes_token_id": str(yes["token_id"]),
        "no_token_id": str(no["token_id"]),
        "w0": w0,
        "w1": w0 + window_s,
        "outcome": int(prices[0] == 1.0),
        "fees_enabled": bool(trading.get("fees_enabled")),
        "fee_rate": float(schedule.get("rate", 0)),
        "fee_exponent": float(schedule.get("exponent", 0)),
    }


def window_quality(times: list[int], w0: int, w1: int) -> tuple[int, int]:
    """Puntos dentro de `[w0, w1)` y el mayor tiempo sin un punto nuevo en la ventana."""
    inside = sorted(t for t in times if w0 <= t < w1)
    edges = [w0, *inside, w1]
    return len(inside), max(b - a for a, b in pairwise(edges))


def load_klines(raw: RawStore, symbol: str, interval: str) -> pd.DataFrame:
    """Klines del crudo como `ts_event` (open_time en segundos) y OHLCV, sin repetidos."""
    rows: list[list[Any]] = []
    for path in sorted((raw.root / "binance" / "klines" / symbol / interval).glob("*.json.gz")):
        rows.extend(row[:6] for row in _read(path)["body"])
    frame = pd.DataFrame(rows, columns=KLINE_COLUMNS)
    frame["ts_event"] = frame["ts_event"].astype("int64") // 1000
    for column in KLINE_COLUMNS[1:]:
        frame[column] = frame[column].astype("float64")
    return frame.drop_duplicates("ts_event").sort_values("ts_event").reset_index(drop=True)


def _ticks(raw: RawStore, market: dict[str, Any], lo: int, latency_s: int) -> list[dict] | str:
    ticks = []
    for side in ("yes", "no"):
        path = raw.price_path(market[f"{side}_token_id"])
        if not path.exists():
            return "sin historial"
        points = {}
        for point in _read(path)["body"]["history"]:
            # Lo posterior a w1 es post-resolución y se descarta.
            if lo <= point["t"] < market["w1"]:
                points[int(point["t"])] = float(point["p"])
        if any(not 0 <= p <= 1 for p in points.values()):
            return "precio fuera de rango"
        ticks += [
            {
                "market_id": market["market_id"],
                "side": side,
                "ts_event": t,
                "ts_available": t + latency_s,
                "p": p,
            }
            for t, p in sorted(points.items())
        ]
    return ticks


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_dataset(
    config: DataConfig,
    raw: RawStore,
    exclusions: SplitExclusions,
    out: str | Path,
    *,
    latency_s: int = 0,
) -> dict[str, Any]:
    """Construye el dataset en `out` y devuelve su manifest.

    `latency_s` es la latencia del feed de precios; la fija S4 y, mientras tanto, vale 0.
    """
    out = Path(out)
    window_s, context_s = config.window_minutes * 60, config.context_minutes * 60
    symbol = f"{config.asset}USDT"
    hourly = load_klines(raw, symbol, "1h").set_index("ts_event")
    rows: list[dict[str, Any]] = []
    ticks: list[dict[str, Any]] = []
    discarded: list[dict[str, Any]] = []

    events = sorted(
        (raw.root / "gamma" / "events" / str(config.series_id)).glob("*.json.gz"),
        key=lambda path: int(path.name.split(".")[0]),
    )
    events_of: dict[str, str] = {}
    for path in events:
        event = _read(path)
        origin = {"event_id": event["id"], "slug": event["slug"]}
        market = parse_market(event, window_s)
        if isinstance(market, str):
            discarded.append(origin | {"motivo": market})
            continue
        day = datetime.fromtimestamp(market["w0"], UTC).date()
        if not config.date_from <= day <= config.date_to:
            continue
        reason = _add_market(market, raw, hourly, config, context_s, latency_s, rows, ticks)
        if reason is not None:
            discarded.append(origin | {"motivo": reason})
        else:
            events_of[market["market_id"]] = event["id"]
    if not rows:
        raise ValueError("Ningún mercado del crudo pasó los filtros; revisa la config y data/raw")

    markets, removed = assign_splits(pd.DataFrame(rows), config.split, exclusions)
    slugs = {row["market_id"]: row["slug"] for row in rows}
    for record in removed.to_dict("records"):
        market_id = record["market_id"]
        discarded.append(
            {"event_id": events_of[market_id], "slug": slugs[market_id], "motivo": record["motivo"]}
        )

    prices = pd.DataFrame(ticks)
    prices = prices[prices["market_id"].isin(markets["market_id"])]
    prices = prices.sort_values(["market_id", "side", "ts_event"]).reset_index(drop=True)

    spot = load_klines(raw, symbol, "1m")
    spot.insert(1, "ts_available", spot["ts_event"] + KLINE_SECONDS)
    lo, hi = markets["w0"].min() - context_s, markets["w1"].max()
    spot = spot[(spot["ts_event"] >= lo) & (spot["ts_event"] < hi)].reset_index(drop=True)

    tables: dict[str, pd.DataFrame] = {
        "markets": Market.validate(markets[list(Market.to_schema().columns)]),
        "prices_raw": PriceTick.validate(prices),
        "spot_1m": SpotKline.validate(spot),
    }
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, frame in tables.items():
        target = out / f"{name}.parquet"
        frame.to_parquet(target, index=False)
        files[target.name] = {"rows": len(frame), "sha256": _sha256(target)}

    manifest = {
        "dataset_id": config.dataset_id,
        "built_at": datetime.now(UTC).isoformat(),
        "config": config.model_dump(mode="json"),
        "feed_latency_s": latency_s,
        "markets_per_split": markets["split"].value_counts().to_dict(),
        "discarded_by_reason": dict(Counter(d["motivo"] for d in discarded)),
        "discarded": discarded,
        "files": files,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def _add_market(
    market: dict[str, Any],
    raw: RawStore,
    hourly: pd.DataFrame,
    config: DataConfig,
    context_s: int,
    latency_s: int,
    rows: list[dict[str, Any]],
    ticks: list[dict[str, Any]],
) -> str | None:
    """Completa el mercado con precios, calidad y spot; devuelve el motivo si se descarta."""
    market_ticks = _ticks(raw, market, market["w0"] - context_s, latency_s)
    if isinstance(market_ticks, str):
        return market_ticks
    yes_times = [t["ts_event"] for t in market_ticks if t["side"] == "yes"]
    n_points, max_gap = window_quality(yes_times, market["w0"], market["w1"])
    if n_points < config.quality.min_points_in_window:
        return "pocos puntos en la ventana"
    if max_gap > config.quality.max_gap_seconds:
        return "hueco largo en la ventana"
    if market["w0"] not in hourly.index:
        return "sin vela 1h de Binance"
    candle = hourly.loc[market["w0"]]
    if int(candle["close"] >= candle["open"]) != market["outcome"]:
        return "el resultado no coincide con Binance"
    rows.append(
        market
        | {
            "spot_open": float(candle["open"]),
            "spot_close": float(candle["close"]),
            "n_points_window": n_points,
            "max_gap_s": max_gap,
        }
    )
    ticks.extend(market_ticks)
    return None
