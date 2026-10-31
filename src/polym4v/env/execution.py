"""Modelo de costos del simulador (ENV-03, S5 y ADR-009).

Funciones puras: el agente compra a `p + medio spread` y vende a `p - medio spread`, y paga la
comisión taker de Polymarket en USDC. Los precios son del lado que se opera: para comprar NO se
pasa el precio de NO. Liquidar al final de la vela no es una operación y no paga comisión.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ..utils.config import CostConfig


@dataclass(frozen=True)
class Fill:
    """Resultado de una operación. `cash` es el cambio de caja: negativo al comprar."""

    shares: float
    price: float
    fee: float
    cash: float


def ask(p: float, costs: CostConfig) -> float:
    """Precio de compra, sin pasar del último tick antes de 1."""
    return min(p + costs.half_spread, 1 - costs.tick)


def bid(p: float, costs: CostConfig) -> float:
    """Precio de venta, sin bajar del primer tick después de 0."""
    return max(p - costs.half_spread, costs.tick)


def _fee_per_share(price: float, costs: CostConfig) -> float:
    return costs.fee_rate * (price * (1 - price)) ** costs.fee_exponent


def taker_fee(shares: float, price: float, costs: CostConfig) -> float:
    """Comisión en USDC: `acciones × rate × (precio × (1 - precio))^exponent`, redondeada.

    El redondeo es al más cercano, con las mitades hacia arriba, y nunca baja de `min_fee` si
    hay comisión. Ambos detalles esperan la confirmación de la documentación oficial.
    """
    raw = shares * _fee_per_share(price, costs)
    if raw <= 0:
        return 0.0
    step = Decimal(1).scaleb(-costs.fee_decimals)
    fee = float(Decimal(repr(raw)).quantize(step, rounding=ROUND_HALF_UP))
    return max(fee, costs.min_fee)


def buy(stake: float, p: float, costs: CostConfig) -> Fill:
    """Compra con un monto en USDC que incluye la comisión, como hace el SDK oficial."""
    price = ask(p, costs)
    shares = stake / (price + _fee_per_share(price, costs))
    fee = taker_fee(shares, price, costs)
    return Fill(shares=shares, price=price, fee=fee, cash=-(shares * price + fee))


def sell(shares: float, p: float, costs: CostConfig) -> Fill:
    """Vende todas las acciones; la comisión se descuenta de lo que se recibe."""
    price = bid(p, costs)
    fee = taker_fee(shares, price, costs)
    return Fill(shares=shares, price=price, fee=fee, cash=shares * price - fee)
