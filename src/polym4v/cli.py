"""Comandos de consulta con salida JSON y errores sin secretos."""

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx
from polymarket import (
    PolymarketError,
    PublicClient,
    RateLimitError,
    RequestRejectedError,
    UserInputError,
)
from pydantic import BaseModel

from .client import PolymarketClient
from .config import ConfigurationError, PolymarketSettings
from .data.capture import RawStore, capture_series, write_manifest


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Tipo no serializable: {type(value).__name__}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Consulta la API de Polymarket.")
    parser.add_argument("--env-file", default=".env", help="Archivo de configuración")
    commands = parser.add_subparsers(dest="command", required=True)

    markets = commands.add_parser("markets", help="Lista una página de mercados")
    markets.add_argument("--limit", type=int, default=10)
    markets.add_argument("--closed", action="store_true", help="Consulta mercados cerrados")
    markets.add_argument("--cursor", help="next_cursor de la página anterior")

    market = commands.add_parser("market", help="Consulta un mercado por su slug")
    market.add_argument("slug")

    book = commands.add_parser("book", help="Consulta un libro de órdenes")
    book.add_argument("asset_id")

    price = commands.add_parser("price", help="Consulta el precio de compra o venta")
    price.add_argument("asset_id")
    price.add_argument("--side", choices=("BUY", "SELL"), default="BUY")

    midpoint = commands.add_parser("midpoint", help="Consulta el punto medio del precio")
    midpoint.add_argument("asset_id")

    history = commands.add_parser("history", help="Consulta una página de precios históricos")
    history.add_argument("asset_id")
    history.add_argument(
        "--interval", choices=("1h", "6h", "1d", "1w", "1m", "all", "max"), default="1d"
    )
    history.add_argument("--bucket-seconds", type=int, default=3600)
    history.add_argument("--limit", type=int, default=100)
    history.add_argument("--cursor")

    commands.add_parser("account", help="Verifica la conexión autenticada")
    orders = commands.add_parser("open-orders", help="Consulta órdenes de tu cuenta")
    orders.add_argument("--cursor")

    capture = commands.add_parser("capture", help="Archiva el historial crudo de una serie")
    capture.add_argument(
        "--series",
        type=int,
        action="append",
        required=True,
        help="ID de la serie en Gamma; se puede repetir",
    )
    capture.add_argument("--out", default="data/raw", help="Carpeta del crudo")
    capture.add_argument("--limit", type=int, help="Máximo de mercados por serie")
    capture.add_argument("--pause", type=float, default=0.2, help="Segundos entre descargas")

    manifest = commands.add_parser("manifest", help="Recalcula el hash de cada archivo crudo")
    manifest.add_argument("--out", default="data/raw", help="Carpeta del crudo")
    return parser


def _capture(args: argparse.Namespace) -> Any:
    store = RawStore(args.out)

    def progress(n: int) -> None:
        if n % 250 == 0:
            print(f"{n} mercados procesados", file=sys.stderr, flush=True)

    with PublicClient() as gamma, httpx.Client(timeout=30) as http:
        summaries = [
            capture_series(
                series,
                store,
                gamma=gamma,
                http=http,
                pause=args.pause,
                limit=args.limit,
                on_event=progress,
            )
            for series in args.series
        ]
    manifest = write_manifest(store)
    return {"series": summaries, "files": manifest["n_files"]}


def _run(args: argparse.Namespace) -> Any:
    if args.command == "capture":
        return _capture(args)
    if args.command == "manifest":
        manifest = write_manifest(RawStore(args.out))
        return {"files": manifest["n_files"]}
    authenticated = args.command in ("account", "open-orders")
    settings = PolymarketSettings.from_env(args.env_file) if authenticated else None
    with PolymarketClient(settings, authenticated=authenticated) as client:
        match args.command:
            case "markets":
                return client.list_markets(limit=args.limit, closed=args.closed, cursor=args.cursor)
            case "market":
                return client.get_market(slug=args.slug)
            case "book":
                return client.get_order_book(args.asset_id)
            case "price":
                return {
                    "asset_id": args.asset_id,
                    "side": args.side,
                    "price": client.get_price(args.asset_id, side=args.side),
                }
            case "midpoint":
                return {
                    "asset_id": args.asset_id,
                    "midpoint": client.get_midpoint(args.asset_id),
                }
            case "history":
                return client.get_price_history(
                    args.asset_id,
                    interval=args.interval,
                    bucket_seconds=args.bucket_seconds,
                    limit=args.limit,
                    cursor=args.cursor,
                )
            case "account":
                return client.get_account()
            case "open-orders":
                return client.list_open_orders(cursor=args.cursor)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = _run(args)
        print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))
    except ConfigurationError as exc:
        print(f"Error de configuración: {exc}", file=sys.stderr)
        return 1
    except RateLimitError:
        print("Polymarket limitó las peticiones. Espera antes de reintentar.", file=sys.stderr)
        return 1
    except UserInputError:
        print("Parámetros o credenciales inválidos. Revisa docs/polymarket.md.", file=sys.stderr)
        return 1
    except RequestRejectedError as exc:
        print(
            f"Polymarket rechazó la consulta (HTTP {exc.status}). Revisa docs/polymarket.md.",
            file=sys.stderr,
        )
        return 1
    except PolymarketError as exc:
        # Las excepciones del SDK pueden contener detalles de la petición.
        print(
            f"No se pudo consultar Polymarket ({type(exc).__name__}). Revisa docs/polymarket.md.",
            file=sys.stderr,
        )
        return 1
    return 0
