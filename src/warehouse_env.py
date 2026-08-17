
from __future__ import annotations

from typing import Any

import gymnasium as gym
from gymnasium import spaces


class WarehouseEnv(gym.Env[int, int]):

    metadata = {"render_modes": ["human", "ansi"], "render_fps": 4}

    GRID_SIZE = 8
    MAX_STEPS = 200
    PICKUP = (1, 1)
    DELIVERY = (4, 7)
    CONGESTION = frozenset({(4, 3), (4, 4), (4, 5)})
    OBSTACLES = frozenset({(2, 2), (2, 3), (6, 2), (6, 3)})
    START = (0, 0)

    # arriba, derecha, abajo, izquierda
    ACTION_DELTAS = ((-1, 0), (0, 1), (1, 0), (0, -1))

    def __init__(self, render_mode: str | None = None, max_steps: int = MAX_STEPS):
        super().__init__()
        if render_mode not in (None, *self.metadata["render_modes"]):
            raise ValueError(f"render_mode no soportado: {render_mode}")
        if max_steps <= 0:
            raise ValueError("max_steps debe ser positivo")

        self.render_mode = render_mode
        self.max_steps = max_steps
        self.action_space = spaces.Discrete(4)
        self.observation_space = spaces.Discrete(self.GRID_SIZE * self.GRID_SIZE * 2)
        self.position = self.START
        self.carrying = False
        self.steps = 0

    def encode_state(self) -> int:
        row, col = self.position
        return ((row * self.GRID_SIZE) + col) * 2 + int(self.carrying)

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[int, dict[str, Any]]:
        super().reset(seed=seed)
        start = (options or {}).get("start_position", self.START)
        if not self._is_valid_cell(start):
            raise ValueError("start_position debe estar dentro del mapa y fuera de obstáculos")

        self.position = start
        self.carrying = bool((options or {}).get("carrying", False))
        self.steps = 0
        observation = self.encode_state()
        info = {"congestion": False, "carrying": self.carrying, "position": self.position}
        if self.render_mode == "human":
            self.render()
        return observation, info

    def step(self, action: int) -> tuple[int, float, bool, bool, dict[str, Any]]:
        if not self.action_space.contains(action):
            raise ValueError(f"Acción inválida: {action}")

        row, col = self.position
        d_row, d_col = self.ACTION_DELTAS[action]
        candidate = (row + d_row, col + d_col)
        hit_wall_or_obstacle = not self._is_valid_cell(candidate)
        if not hit_wall_or_obstacle:
            self.position = candidate

        self.steps += 1
        entered_congestion = self.position in self.CONGESTION and not hit_wall_or_obstacle
        reward = -1.0  # coste de cada acción, incluso si choca con un borde u obstáculo
        if entered_congestion:
            reward -= 10.0

        if self.position == self.PICKUP:
            self.carrying = True

        terminated = self.position == self.DELIVERY and self.carrying
        if terminated:
            reward += 100.0
        truncated = self.steps >= self.max_steps and not terminated

        observation = self.encode_state()
        info = {
            "congestion": entered_congestion,
            "carrying": self.carrying,
            "position": self.position,
            "hit_wall_or_obstacle": hit_wall_or_obstacle,
        }
        if self.render_mode == "human":
            self.render()
        return observation, reward, terminated, truncated, info

    def render(self) -> str | None:
        symbols = {
            self.PICKUP: "R",
            self.DELIVERY: "E",
            **{cell: "C" for cell in self.CONGESTION},
            **{cell: "#" for cell in self.OBSTACLES},
        }
        symbols[self.position] = "A"
        drawing = "\n".join(
            " ".join(symbols.get((row, col), "-") for col in range(self.GRID_SIZE))
            for row in range(self.GRID_SIZE)
        )
        if self.render_mode == "ansi":
            return drawing
        if self.render_mode == "human":
            print(drawing)
        return None

    def _is_valid_cell(self, cell: tuple[int, int]) -> bool:
        row, col = cell
        return 0 <= row < self.GRID_SIZE and 0 <= col < self.GRID_SIZE and cell not in self.OBSTACLES
