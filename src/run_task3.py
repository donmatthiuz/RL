
from __future__ import annotations

from .td_control import evaluate_greedy, train_q_learning, train_sarsa
from .warehouse_env import WarehouseEnv


def print_result(name: str, result: object) -> None:
    print(f"{name} (evaluación greedy, 100 episodios)")
    print(f"  recompensa promedio: {result.mean_reward:.2f}")
    print(f"  pasos promedio: {result.mean_steps:.2f}")
    print(f"  visitas promedio a congestión: {result.mean_congestion_visits:.2f}")
    print(f"  tasa de éxito: {result.success_rate:.1%}")


