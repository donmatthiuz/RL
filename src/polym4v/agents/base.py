"""Interfaz común de agentes y baselines (INF-06, AGT-02).

Heurísticas, PPO, DQN, CQL y BC se evalúan con el mismo entorno y el mismo backtest a través de
esta interfaz. Así todos reciben la misma información y siguen las mismas reglas de ejecución, y la
comparación con los baselines es justa.
"""

from collections.abc import Mapping
from enum import IntEnum
from typing import Any, Protocol, runtime_checkable

import numpy as np


class Action(IntEnum):
    """Espacio de acción `Discrete(4)` del entorno (docs/02, sección 2.3)."""

    WAIT = 0
    BUY_YES = 1
    BUY_NO = 2
    SELL = 3


@runtime_checkable
class Policy(Protocol):
    """Decide una acción con la observación del paso actual.

    `info` es el diccionario que devuelve el entorno en el paso anterior; sus claves las define
    R3 junto con este contrato. Las políticas con estado interno lo limpian en `reset`, que se
    llama al empezar cada episodio (un mercado).
    """

    name: str

    def act(self, obs: np.ndarray, info: Mapping[str, Any] | None = None) -> int: ...

    def reset(self) -> None: ...
