from typing import Protocol

import numpy as np
from numpy.typing import NDArray


class Policy(Protocol):
    def select_action(self, state: NDArray[np.floating]) -> int: ...


class TrafficHeuristicPolicy:
    def __init__(self, change_probability: float = 0.65, seed: int = 42) -> None:
        if not 0.0 <= change_probability <= 1.0:
            raise ValueError("change_probability debe estar entre 0 y 1.")
        self.change_probability = change_probability
        self.rng = np.random.default_rng(seed)

    def select_action(self, state: NDArray[np.floating]) -> int:
        del state
        return int(self.rng.random() < self.change_probability)
