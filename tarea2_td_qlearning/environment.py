import gymnasium as gym
import numpy as np
from gymnasium import spaces
from numpy.typing import NDArray

from tarea2_td_qlearning.config import EnvironmentConfig


class SimplifiedIntersectionEnv(gym.Env[NDArray[np.float32], int]):
    metadata = {"render_modes": []}
    MAINTAIN = 0
    CHANGE = 1

    def __init__(self, config: EnvironmentConfig | None = None) -> None:
        super().__init__()
        self.config = config or EnvironmentConfig()
        self.observation_space = spaces.Box(0.0, 1.0, shape=(3,), dtype=np.float32)
        self.action_space = spaces.Discrete(2)
        self.state = np.zeros(3, dtype=np.float32)
        self.step_count = 0

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        del options
        density = self.np_random.uniform(0.25, 0.75)
        speed_center = 0.90 - 0.65 * density
        speed = np.clip(speed_center + self.np_random.normal(0.0, 0.07), 0.0, 1.0)
        waiting = self.np_random.uniform(0.05, 0.35)
        self.state = np.array([density, speed, waiting], dtype=np.float32)
        self.step_count = 0
        return self.state.copy(), self._info(0.0)

    def step(self, action: int):
        if not self.action_space.contains(action):
            raise ValueError(f"Accion invalida: {action}. Debe ser 0 o 1.")
        density, speed, waiting = self.state.astype(np.float64)
        periodic_demand = 0.018 * np.sin(2.0 * np.pi * self.step_count / 25.0)
        arrivals = np.clip(
            0.09 + periodic_demand + self.np_random.normal(0.0, 0.018),
            0.02,
            0.16,
        )
        if action == self.MAINTAIN:
            service = 0.07 + 0.16 * speed * (1.0 - 0.45 * density)
            target_speed = 0.88 - 0.58 * density
        else:
            congestion = density * (1.0 - speed)
            service = 0.045 + 0.28 * congestion + 0.06 * waiting
            target_speed = 0.67 + 0.18 * density - 0.12 * waiting
        next_density = np.clip(
            density + arrivals - service + self.np_random.normal(0.0, 0.012),
            0.0,
            1.0,
        )
        next_speed = np.clip(
            0.65 * speed + 0.35 * target_speed + self.np_random.normal(0.0, 0.025),
            0.0,
            1.0,
        )
        flow = float(np.clip(3.0 * min(density, service) * next_speed, 0.0, 1.0))
        wait_change = 0.13 * next_density * (1.0 - next_speed) - 0.10 * flow
        if action == self.CHANGE:
            wait_change -= 0.035 * density
        next_waiting = np.clip(
            waiting + wait_change + self.np_random.normal(0.0, 0.008), 0.0, 1.0
        )
        reward = -self.config.wait_penalty * next_waiting
        if flow > self.config.flow_threshold:
            reward += self.config.flow_bonus
        if action == self.CHANGE:
            reward -= self.config.switch_penalty
        self.state = np.array([next_density, next_speed, next_waiting], dtype=np.float32)
        self.step_count += 1
        terminated = False
        truncated = self.step_count >= self.config.max_steps
        return self.state.copy(), float(reward), terminated, truncated, self._info(flow)

    def _info(self, flow: float) -> dict[str, float]:
        return {
            "flow": float(flow),
            "density": float(self.state[0]),
            "speed": float(self.state[1]),
            "waiting_time": float(self.state[2]),
        }
