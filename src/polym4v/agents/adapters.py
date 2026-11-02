"""Adaptadores de modelos entrenados a `Policy` (AGT-02).

PPO y DQN (stable-baselines3) y CQL y BC (d3rlpy) se evalúan con el mismo backtest que los
baselines a través de esta interfaz. La acción es siempre la codiciosa (determinista): la evaluación
no explora. Estos modelos no guardan estado entre pasos (redes MLP), así que `reset` no hace nada.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

SB3_ALGOS = ("ppo", "dqn")


class SB3Policy:
    """Envuelve un modelo de stable-baselines3 (PPO o DQN)."""

    def __init__(self, model: Any, name: str) -> None:
        self.model, self.name = model, name

    @classmethod
    def load(cls, path: str | Path, algo: str, name: str | None = None) -> "SB3Policy":
        """Carga un modelo guardado con `model.save`; `algo` es `ppo` o `dqn`."""
        from stable_baselines3 import DQN, PPO
        from stable_baselines3.common.base_class import BaseAlgorithm

        classes: dict[str, type[BaseAlgorithm]] = {"ppo": PPO, "dqn": DQN}
        if algo not in classes:
            raise ValueError(f"algoritmo desconocido: {algo}. Disponibles: {', '.join(SB3_ALGOS)}")
        return cls(classes[algo].load(str(path), device="cpu"), name or algo)

    def act(self, obs: np.ndarray, info: Mapping[str, Any] | None = None) -> int:
        action, _ = self.model.predict(obs, deterministic=True)
        return int(action)

    def reset(self) -> None:
        pass


class D3rlpyPolicy:
    """Envuelve un algoritmo discreto de d3rlpy (DiscreteCQL o DiscreteBC)."""

    def __init__(self, algo: Any, name: str) -> None:
        self.algo, self.name = algo, name

    @classmethod
    def load(cls, path: str | Path, name: str | None = None) -> "D3rlpyPolicy":
        """Carga un archivo `.d3` guardado con `algo.save`."""
        import d3rlpy

        algo = d3rlpy.load_learnable(str(path), device=False)
        return cls(algo, name or type(algo).__name__.lower())

    def act(self, obs: np.ndarray, info: Mapping[str, Any] | None = None) -> int:
        # d3rlpy predice por lotes: se agrega la dimensión del lote y se toma la única acción.
        return int(self.algo.predict(np.asarray(obs, dtype=np.float32)[None, :])[0])

    def reset(self) -> None:
        pass
