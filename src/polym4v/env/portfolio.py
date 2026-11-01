"""Cartera del agente en un episodio (ENV-02, S9 en ADR-016).

Una sola posición a la vez, del lado YES o del lado NO. El precio de NO es `1 - p_yes` (ADR-003).
La posición abierta se valora con lo que se recibiría al venderla ya: `p - half_spread`, menos la
comisión de vender (S9). Al final de la vela paga 1 o 0 por acción, sin comisión.
"""

from dataclasses import dataclass

from ..utils.config import CostConfig
from .execution import Fill, bid, taker_fee

YES, FLAT, NO = 1, 0, -1


def side_price(p_yes: float, side: int) -> float:
    """Precio del token del lado `side`."""
    return p_yes if side == YES else 1.0 - p_yes


@dataclass
class Portfolio:
    cash: float
    side: int = FLAT
    shares: float = 0.0
    entry_price: float = 0.0
    cost: float = 0.0
    fees_paid: float = 0.0

    def open(self, side: int, fill: Fill) -> None:
        """Abre una posición con una compra ya calculada por `execution.buy`."""
        if self.side != FLAT:
            raise ValueError("ya hay una posición abierta")
        if side not in (YES, NO):
            raise ValueError(f"lado inválido: {side}")
        if -fill.cash > self.cash + 1e-9:
            raise ValueError("no alcanza el saldo")
        self.cash += fill.cash
        self.side, self.shares = side, fill.shares
        self.entry_price, self.cost = fill.price, -fill.cash
        self.fees_paid += fill.fee

    def close(self, fill: Fill) -> float:
        """Cierra la posición con una venta de `execution.sell`; devuelve el PnL realizado."""
        if self.side == FLAT:
            raise ValueError("no hay posición abierta")
        self.cash += fill.cash
        self.fees_paid += fill.fee
        pnl = fill.cash - self.cost
        self._flat()
        return pnl

    def settle(self, outcome: int) -> float:
        """Liquida al final de la vela: 1 por acción del lado ganador, sin comisión."""
        if self.side == FLAT:
            return 0.0
        won = (outcome == 1) == (self.side == YES)
        payout = self.shares if won else 0.0
        self.cash += payout
        pnl = payout - self.cost
        self._flat()
        return pnl

    def liquidation_value(self, p_yes: float, costs: CostConfig) -> float:
        """Lo que se recibiría al vender ya la posición (S9)."""
        if self.side == FLAT:
            return 0.0
        price = bid(side_price(p_yes, self.side), costs)
        return self.shares * price - taker_fee(self.shares, price, costs)

    def value(self, p_yes: float, costs: CostConfig) -> float:
        """Valor de la cartera: caja más el valor de liquidación de la posición."""
        return self.cash + self.liquidation_value(p_yes, costs)

    def _flat(self) -> None:
        self.side, self.shares, self.entry_price, self.cost = FLAT, 0.0, 0.0, 0.0
