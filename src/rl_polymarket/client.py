"""Adaptador síncrono sobre el SDK oficial polymarket-client."""

from __future__ import annotations

from decimal import Decimal
from types import TracebackType
from typing import Literal, Self

from polymarket import (
    Market,
    OpenOrder,
    OrderBook,
    PriceHistoryInterval,
    PriceHistoryPoint,
    PublicClient,
    SecureClient,
    UserInputError,
)
from polymarket.pagination import Page

from .config import ConfigurationError, PolymarketSettings


def get_asset_id(market: Market, outcome: Literal["yes", "no"] = "yes") -> str:
    """Selecciona el token CTF (v1) o la posición (v2) de un resultado."""
    if outcome not in ("yes", "no"):
        raise UserInputError("El resultado debe ser 'yes' o 'no'.")
    selected = getattr(market.outcomes, outcome)
    asset_id = (
        selected.position_id if market.version == "v2" else selected.token_id
    )
    if asset_id is None:
        raise UserInputError("El resultado no tiene un identificador negociable.")
    return str(asset_id)


class PolymarketClient:
    """Consultas públicas por defecto y acceso autenticado bajo petición.

    Usar como context manager cierra las conexiones HTTP al terminar.
    Los métodos de listas devuelven una página y conservan su cursor.
    """

    def __init__(
        self,
        settings: PolymarketSettings | None = None,
        *,
        authenticated: bool = False,
    ) -> None:
        self._client: PublicClient | SecureClient
        if authenticated:
            settings = settings or PolymarketSettings.from_env()
            credentials = settings.get_credentials()
            assert settings.private_key is not None
            self._client = SecureClient.create(
                private_key=settings.private_key,
                wallet=settings.wallet_address,
                credentials=credentials,
            )
        else:
            self._client = PublicClient()

    def list_markets(
        self,
        *,
        limit: int = 10,
        closed: bool = False,
        cursor: str | None = None,
    ) -> Page[Market]:
        """Consulta mercados por páginas de entre 1 y 100 elementos."""
        if not 1 <= limit <= 100:
            raise UserInputError("El límite de mercados debe estar entre 1 y 100.")
        pages = self._client.list_markets(closed=closed, page_size=limit)
        if cursor is not None:
            pages = pages.from_cursor(cursor)
        return pages.first_page()

    def get_market(self, *, slug: str) -> Market:
        """Consulta el slug de un mercado individual, que puede diferir del evento."""
        return self._client.get_market(slug=slug)

    def get_order_book(self, asset_id: str) -> OrderBook:
        return self._client.get_order_book(asset_id=asset_id)

    def get_price(
        self, asset_id: str, *, side: Literal["BUY", "SELL"] = "BUY"
    ) -> Decimal:
        """Devuelve un Decimal para conservar la precisión del precio."""
        return self._client.get_price(asset_id=asset_id, side=side)

    def get_midpoint(self, asset_id: str) -> Decimal:
        return self._client.get_midpoint(asset_id=asset_id)

    def get_price_history(
        self,
        asset_id: str,
        *,
        interval: PriceHistoryInterval = "1d",
        bucket_seconds: int = 3600,
        limit: int = 100,
        cursor: str | None = None,
    ) -> Page[PriceHistoryPoint]:
        """Lee una página de observaciones históricas, de la más antigua a la nueva."""
        if not 1 <= limit <= 10000:
            raise UserInputError("El límite del historial debe estar entre 1 y 10000.")
        if bucket_seconds < 1:
            raise UserInputError("bucket_seconds debe ser positivo.")
        pages = self._client.list_price_history(
            asset_id=asset_id,
            interval=interval,
            bucket_seconds=bucket_seconds,
            page_size=limit,
        )
        if cursor is not None:
            pages = pages.from_cursor(cursor)
        return pages.first_page()

    def get_account(self) -> dict[str, str]:
        client = self._require_authenticated()
        return {"wallet": str(client.wallet), "wallet_type": client.wallet_type}

    def list_open_orders(self, *, cursor: str | None = None) -> Page[OpenOrder]:
        """Lee una página de órdenes existentes; no crea ni cancela órdenes."""
        pages = self._require_authenticated().list_open_orders()
        if cursor is not None:
            pages = pages.from_cursor(cursor)
        return pages.first_page()

    def _require_authenticated(self) -> SecureClient:
        if not isinstance(self._client, SecureClient):
            raise ConfigurationError("Esta consulta requiere authenticated=True.")
        return self._client

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
