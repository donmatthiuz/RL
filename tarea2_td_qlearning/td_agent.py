import numpy as np
from numpy.typing import NDArray

from tarea2_td_qlearning.feature_extractor import FeatureExtractor


class SemiGradientTDAgent:
    def __init__(
        self,
        feature_extractor: FeatureExtractor,
        alpha: float = 0.015,
        gamma: float = 0.95,
    ) -> None:
        self.features = feature_extractor
        self.alpha = alpha
        self.gamma = gamma
        self.weights = np.zeros(self.features.dimension, dtype=np.float64)

    def value(self, state: NDArray[np.floating]) -> float:
        return float(self.weights @ self.features.transform(state))

    def values(self, states: NDArray[np.floating]) -> NDArray[np.float64]:
        return self.features.transform_batch(states) @ self.weights

    def update(self, state, reward: float, next_state, done: bool) -> float:
        x_state = self.features.transform(state)
        current_value = float(self.weights @ x_state)
        next_value = 0.0 if done else self.value(next_state)
        td_error = reward + self.gamma * next_value - current_value
        self.weights += self.alpha * td_error * x_state
        return float(td_error)

    @property
    def weight_norm(self) -> float:
        return float(np.linalg.norm(self.weights))
