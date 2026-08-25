import numpy as np
from numpy.typing import NDArray

from tarea2_td_qlearning.state_discretizer import StateDiscretizer


class TabularQLearningAgent:
    def __init__(
        self,
        discretizer: StateDiscretizer,
        alpha: float = 0.12,
        gamma: float = 0.95,
        epsilon: float = 1.0,
        epsilon_min: float = 0.03,
        epsilon_decay: float = 0.992,
        seed: int = 42,
    ) -> None:
        self.discretizer = discretizer
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.rng = np.random.default_rng(seed)
        self.q_table = np.zeros((*self.discretizer.state_shape, 2), dtype=np.float64)

    def select_action(self, state: NDArray[np.floating]) -> int:
        if self.rng.random() < self.epsilon:
            return int(self.rng.integers(2))
        values = self.q_table[self.discretizer.transform(state)]
        best_actions = np.flatnonzero(values == values.max())
        return int(self.rng.choice(best_actions))

    def update(self, state, action: int, reward: float, next_state, done: bool) -> float:
        state_index = self.discretizer.transform(state)
        next_index = self.discretizer.transform(next_state)
        current_q = self.q_table[state_index + (action,)]
        next_q = 0.0 if done else float(np.max(self.q_table[next_index]))
        td_error = reward + self.gamma * next_q - current_q
        self.q_table[state_index + (action,)] += self.alpha * td_error
        return float(td_error)

    def end_episode(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def state_value(self, state: NDArray[np.floating]) -> float:
        return float(np.max(self.q_table[self.discretizer.transform(state)]))

    def state_values(self, states: NDArray[np.floating]) -> NDArray[np.float64]:
        return np.array([self.state_value(state) for state in states])
