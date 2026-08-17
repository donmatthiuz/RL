
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .warehouse_env import WarehouseEnv


@dataclass
class TrainingHistory:

    rewards: list[float] = field(default_factory=list)
    steps: list[int] = field(default_factory=list)
    congestion_visits: list[int] = field(default_factory=list)
    successes: list[bool] = field(default_factory=list)


@dataclass(frozen=True)
class EvaluationResult:

    rewards: list[float]
    steps: list[int]
    congestion_visits: list[int]
    successes: list[bool]

    @property
    def mean_reward(self) -> float:
        return float(np.mean(self.rewards))

    @property
    def mean_steps(self) -> float:
        return float(np.mean(self.steps))

    @property
    def mean_congestion_visits(self) -> float:
        return float(np.mean(self.congestion_visits))

    @property
    def success_rate(self) -> float:
        return float(np.mean(self.successes))


def epsilon_greedy(
    q_table: np.ndarray, state: int, epsilon: float, rng: np.random.Generator
) -> int:
    """Elige una acción epsilon-greedy, desempatando de forma aleatoria."""
    if not 0.0 <= epsilon <= 1.0:
        raise ValueError("epsilon debe pertenecer a [0, 1]")
    if rng.random() < epsilon:
        return int(rng.integers(q_table.shape[1]))
    best_actions = np.flatnonzero(q_table[state] == q_table[state].max())
    return int(rng.choice(best_actions))


def train_sarsa(
    env: WarehouseEnv,
    episodes: int,
    alpha: float = 0.1,
    gamma: float = 0.95,
    epsilon: float = 0.1,
    epsilon_decay: float = 1.0,
    epsilon_min: float = 0.0,
    seed: int | None = None,
) -> tuple[np.ndarray, TrainingHistory]:
    """Entrena SARSA on-policy y devuelve la tabla Q y métricas por episodio."""
    _validate_hyperparameters(episodes, alpha, gamma, epsilon, epsilon_decay, epsilon_min)
    rng = np.random.default_rng(seed)
    q_table = np.zeros((env.observation_space.n, env.action_space.n), dtype=float)
    history = TrainingHistory()
    current_epsilon = epsilon

    for episode in range(episodes):
        state, _ = env.reset(seed=None if seed is None else seed + episode)
        action = epsilon_greedy(q_table, state, current_epsilon, rng)
        total_reward, congestion_visits, steps = 0.0, 0, 0
        terminated = truncated = False

        while not (terminated or truncated):
            next_state, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            steps += 1
            congestion_visits += int(info["congestion"])
            if terminated or truncated:
                target = reward
            else:
                next_action = epsilon_greedy(q_table, next_state, current_epsilon, rng)
                target = reward + gamma * q_table[next_state, next_action]
            q_table[state, action] += alpha * (target - q_table[state, action])
            if not (terminated or truncated):
                state, action = next_state, next_action

        _append_episode(history, total_reward, steps, congestion_visits, terminated)
        current_epsilon = max(epsilon_min, current_epsilon * epsilon_decay)
    return q_table, history


def train_q_learning(
    env: WarehouseEnv,
    episodes: int,
    alpha: float = 0.1,
    gamma: float = 0.95,
    epsilon: float = 0.1,
    epsilon_decay: float = 1.0,
    epsilon_min: float = 0.0,
    seed: int | None = None,
) -> tuple[np.ndarray, TrainingHistory]:
    _validate_hyperparameters(episodes, alpha, gamma, epsilon, epsilon_decay, epsilon_min)
    rng = np.random.default_rng(seed)
    q_table = np.zeros((env.observation_space.n, env.action_space.n), dtype=float)
    history = TrainingHistory()
    current_epsilon = epsilon

    for episode in range(episodes):
        state, _ = env.reset(seed=None if seed is None else seed + episode)
        total_reward, congestion_visits, steps = 0.0, 0, 0
        terminated = truncated = False

        while not (terminated or truncated):
            action = epsilon_greedy(q_table, state, current_epsilon, rng)
            next_state, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            steps += 1
            congestion_visits += int(info["congestion"])
            target = reward if (terminated or truncated) else reward + gamma * q_table[next_state].max()
            q_table[state, action] += alpha * (target - q_table[state, action])
            state = next_state

        _append_episode(history, total_reward, steps, congestion_visits, terminated)
        current_epsilon = max(epsilon_min, current_epsilon * epsilon_decay)
    return q_table, history


def evaluate_greedy(
    env: WarehouseEnv, q_table: np.ndarray, episodes: int = 100, seed: int | None = None
) -> EvaluationResult:
    if episodes <= 0:
        raise ValueError("episodes debe ser positivo")
    if q_table.shape != (env.observation_space.n, env.action_space.n):
        raise ValueError("La tabla Q no coincide con los espacios del entorno")

    rng = np.random.default_rng(seed)
    history = TrainingHistory()
    for episode in range(episodes):
        state, _ = env.reset(seed=None if seed is None else seed + episode)
        total_reward, congestion_visits, steps = 0.0, 0, 0
        terminated = truncated = False
        while not (terminated or truncated):
            action = epsilon_greedy(q_table, state, epsilon=0.0, rng=rng)
            state, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            steps += 1
            congestion_visits += int(info["congestion"])
        _append_episode(history, total_reward, steps, congestion_visits, terminated)

    return EvaluationResult(**history.__dict__)


def _append_episode(
    history: TrainingHistory, reward: float, steps: int, congestion_visits: int, success: bool
) -> None:
    history.rewards.append(reward)
    history.steps.append(steps)
    history.congestion_visits.append(congestion_visits)
    history.successes.append(success)


def _validate_hyperparameters(
    episodes: int, alpha: float, gamma: float, epsilon: float, epsilon_decay: float, epsilon_min: float
) -> None:
    if episodes <= 0:
        raise ValueError("episodes debe ser positivo")
    if not 0.0 < alpha <= 1.0:
        raise ValueError("alpha debe pertenecer a (0, 1]")
    if not 0.0 <= gamma <= 1.0:
        raise ValueError("gamma debe pertenecer a [0, 1]")
    if not 0.0 <= epsilon_min <= epsilon <= 1.0:
        raise ValueError("Se requiere 0 <= epsilon_min <= epsilon <= 1")
    if not 0.0 < epsilon_decay <= 1.0:
        raise ValueError("epsilon_decay debe pertenecer a (0, 1]")
