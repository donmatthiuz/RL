import numpy as np
from numpy.typing import NDArray


class StateDiscretizer:
    def __init__(self, levels: int = 5) -> None:
        if levels < 2:
            raise ValueError("La discretizacion requiere al menos dos niveles.")
        self.levels = levels

    @property
    def state_shape(self) -> tuple[int, int, int]:
        return (self.levels, self.levels, self.levels)

    def transform(self, state: NDArray[np.floating]) -> tuple[int, int, int]:
        clipped = np.clip(np.asarray(state, dtype=np.float64), 0.0, 1.0)
        indices = np.minimum((clipped * self.levels).astype(int), self.levels - 1)
        return tuple(int(index) for index in indices)
