import numpy as np
from numpy.typing import NDArray


class FeatureExtractor:
    dimension = 7

    def __init__(self, saturation_threshold: float = 0.8) -> None:
        self.saturation_threshold = saturation_threshold

    def transform(self, state: NDArray[np.floating]) -> NDArray[np.float64]:
        density, speed, waiting = np.asarray(state, dtype=np.float64)
        return np.array(
            [
                1.0,
                density,
                speed,
                waiting,
                density * (1.0 - speed),
                density * speed,
                float(density >= self.saturation_threshold),
            ],
            dtype=np.float64,
        )

    def transform_batch(self, states: NDArray[np.floating]) -> NDArray[np.float64]:
        return np.vstack([self.transform(state) for state in states])
