"""Validación de cada ejecución simulada con los trades reales (EVA-11, S4a y ADR-017).

Una ejecución es **verificable** si, dentro de la misma ventana de S4, `(t + latencia,
t + tolerancia]`, algún taker real operó del mismo lado a ese precio o mejor, por al menos el monto
de la orden. Que no haya trade no prueba que faltara liquidez en el libro, pero tampoco la confirma.

Todo se compara en equivalente YES: comprar NO a `q` es vender YES a `1 - q`.
"""

import gzip
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from ..data.capture import RawStore

# Tolerancia para comparar precios en float.
_EPS = 1e-9


@dataclass(frozen=True)
class MarketTrades:
    """Trades taker de un mercado en equivalente YES, ordenados por fecha."""

    ts: np.ndarray
    yes_price: np.ndarray
    buy: np.ndarray
    usdc: np.ndarray

    @classmethod
    def from_raw(cls, body: list[dict]) -> "MarketTrades":
        """Desde los trades del crudo de DAT-11 (`price`, `size`, `side`, `outcome_index`)."""
        price = np.array([float(t["price"]) for t in body])
        size = np.array([float(t["size"]) for t in body])
        is_yes = np.array([int(t["outcome_index"]) == 0 for t in body], dtype=bool)
        bought = np.array([t["side"] == "BUY" for t in body], dtype=bool)
        ts = np.array(
            [int(datetime.fromisoformat(t["timestamp"]).timestamp()) for t in body], dtype=np.int64
        )
        order = np.argsort(ts, kind="stable")
        return cls(
            ts=ts[order],
            yes_price=np.where(is_yes, price, 1.0 - price)[order],
            buy=(bought == is_yes)[order],
            usdc=(price * size)[order],
        )


class TradeVerifier:
    """Responde si una ejecución simulada está respaldada por trades reales.

    Devuelve `None` si el mercado no tiene trades capturados: no se puede saber.
    """

    def __init__(
        self,
        trades: Mapping[str, MarketTrades],
        *,
        latency_s: int,
        tolerance_s: int,
        min_usdc: float,
    ) -> None:
        self.trades = trades
        self.latency_s, self.tolerance_s, self.min_usdc = latency_s, tolerance_s, min_usdc

    @classmethod
    def load(cls, store: RawStore, market_ids: Iterable[str], **window: float) -> "TradeVerifier":
        """Lee del crudo los trades de los mercados que los tengan."""
        trades = {}
        for market_id in market_ids:
            path = store.trades_path(market_id)
            if path.exists():
                body = json.loads(gzip.decompress(path.read_bytes()))["body"]
                trades[market_id] = MarketTrades.from_raw(body)
        return cls(trades, **window)  # type: ignore[arg-type]

    def __call__(self, market_id: str, t: int, *, buy: bool, yes_price: float) -> bool | None:
        """¿Un taker compró (o vendió) YES a `yes_price` o mejor, por `min_usdc` o más?"""
        trades = self.trades.get(market_id)
        if trades is None:
            return None
        lo = np.searchsorted(trades.ts, t + self.latency_s, side="right")
        hi = np.searchsorted(trades.ts, t + self.tolerance_s, side="right")
        price, side = trades.yes_price[lo:hi], trades.buy[lo:hi]
        better = price <= yes_price + _EPS if buy else price >= yes_price - _EPS
        return bool(trades.usdc[lo:hi][(side == buy) & better].sum() >= self.min_usdc)
