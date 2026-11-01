"""Baselines heurísticos (AGT-03, docs/02 sección 2.5 y docs/08 sección 4.3).

Leen la misma observación que los agentes de RL (S3) y operan con las mismas reglas del entorno,
así que la comparación es justa. Los umbrales sobre `dp_1` y `dp_5` están en unidades de z-score,
porque el entorno normaliza esas features con train.
"""

from collections.abc import Callable, Mapping
from typing import Any

import numpy as np

from ..env.execution import ask, taker_fee
from ..features.market import MARKET_FEATURES
from ..utils.config import CostConfig
from .base import Action, Policy

_I = {name: i for i, name in enumerate(MARKET_FEATURES)}
POS_SIDE = len(MARKET_FEATURES)
UPNL = POS_SIDE + 2
STEPS = 60


def _k(obs: np.ndarray) -> int:
    """Paso de la vela, desde `tau = (60 - k) / 60`."""
    return STEPS - round(float(obs[_I["tau"]]) * STEPS)


def _flat(obs: np.ndarray) -> bool:
    return bool(obs[POS_SIDE] == 0)


class NoTradePolicy:
    """Nunca opera. Su retorno es 0 y es la referencia de EVA-01 si ninguna heurística le gana."""

    name = "no_trade"

    def act(self, obs: np.ndarray, info: Mapping[str, Any] | None = None) -> int:
        return Action.WAIT

    def reset(self) -> None:
        pass


class RandomPolicy:
    """Elige una de las cuatro acciones al azar; las inválidas el entorno las ejecuta como WAIT."""

    name = "random"

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def act(self, obs: np.ndarray, info: Mapping[str, Any] | None = None) -> int:
        return int(self.rng.integers(len(Action)))

    def reset(self) -> None:
        pass


class FavoritePolicy:
    """En el paso `entry_k` compra el lado con precio mayor a 0,5 y mantiene hasta el final."""

    name = "favorite"

    def __init__(self, entry_k: int = 30) -> None:
        self.entry_k = entry_k

    def act(self, obs: np.ndarray, info: Mapping[str, Any] | None = None) -> int:
        if not _flat(obs) or _k(obs) != self.entry_k:
            return Action.WAIT
        p_yes = float(obs[_I["p_yes"]])
        if p_yes == 0.5:
            return Action.WAIT
        return Action.BUY_YES if p_yes > 0.5 else Action.BUY_NO

    def reset(self) -> None:
        pass


class MomentumPolicy:
    """Compra en la dirección del cambio reciente de `p_yes` y sale al ganar o perder lo fijado.

    Entra cuando `dp_5` pasa `threshold` desviaciones. Sale cuando `upnl` llega a `take_profit` o
    baja de `-stop_loss`; si no, mantiene hasta la resolución.
    """

    name = "momentum"
    direction = 1

    def __init__(
        self, threshold: float = 1.0, take_profit: float = 0.2, stop_loss: float = 0.2
    ) -> None:
        self.threshold, self.take_profit, self.stop_loss = threshold, take_profit, stop_loss

    def act(self, obs: np.ndarray, info: Mapping[str, Any] | None = None) -> int:
        if not _flat(obs):
            upnl = float(obs[UPNL])
            exit_now = upnl >= self.take_profit or upnl <= -self.stop_loss
            return Action.SELL if exit_now else Action.WAIT
        signal = self.direction * float(obs[_I["dp_5"]])
        if signal > self.threshold:
            return Action.BUY_YES
        if signal < -self.threshold:
            return Action.BUY_NO
        return Action.WAIT

    def reset(self) -> None:
        pass


class MeanReversionPolicy(MomentumPolicy):
    """Lo contrario de `MomentumPolicy`: apuesta a que el cambio reciente se revierte."""

    name = "mean_reversion"
    direction = -1


class FairValuePolicy:
    """Compra el lado cuya ventaja supera los costos de mantener hasta el final.

    Usa `edge_tp`, la ventaja en el instante del precio (S3b): `edge` mide sobre todo el atraso
    del feed, que la ejecución al precio siguiente no deja aprovechar. Comprar YES espera ganar
    `p_fair - ask - comisión` por acción; NO, lo mismo con `1 - p`. Entra si eso supera `margin`.
    """

    name = "fair_value"

    def __init__(self, costs: CostConfig, margin: float = 0.0) -> None:
        self.costs, self.margin = costs, margin

    def _gain(self, p_fair: float, p: float) -> float:
        price = ask(p, self.costs)
        return p_fair - price - taker_fee(1.0, price, self.costs)

    def act(self, obs: np.ndarray, info: Mapping[str, Any] | None = None) -> int:
        if not _flat(obs):
            return Action.WAIT
        p_yes = float(obs[_I["p_yes"]])
        p_fair = p_yes + float(obs[_I["edge_tp"]])
        if self._gain(p_fair, p_yes) > self.margin:
            return Action.BUY_YES
        if self._gain(1.0 - p_fair, 1.0 - p_yes) > self.margin:
            return Action.BUY_NO
        return Action.WAIT

    def reset(self) -> None:
        pass


def baselines(costs: CostConfig, seed: int = 0) -> dict[str, Callable[[], Policy]]:
    """Constructores de cada baseline por nombre, para el backtest y la config."""
    return {
        "no_trade": NoTradePolicy,
        "random": lambda: RandomPolicy(seed),
        "favorite": FavoritePolicy,
        "momentum": MomentumPolicy,
        "mean_reversion": MeanReversionPolicy,
        "fair_value": lambda: FairValuePolicy(costs),
    }
