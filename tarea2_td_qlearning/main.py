from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tarea2_td_qlearning.config import EnvironmentConfig
from tarea2_td_qlearning.experiment import ExperimentRunner
from tarea2_td_qlearning.feature_extractor import FeatureExtractor
from tarea2_td_qlearning.models import ExperimentResult
from tarea2_td_qlearning.plotter import ResultsPlotter
from tarea2_td_qlearning.policy import TrafficHeuristicPolicy
from tarea2_td_qlearning.q_learning_agent import TabularQLearningAgent
from tarea2_td_qlearning.state_discretizer import StateDiscretizer
from tarea2_td_qlearning.td_agent import SemiGradientTDAgent


def print_summary(result: ExperimentResult, last_n: int = 50) -> None:
    td_rewards = np.asarray(result.td_history.rewards)
    q_rewards = np.asarray(result.q_history.rewards)
    window = min(last_n, len(td_rewards))
    print("\nResumen del entrenamiento")
    print(f"  Episodios: {len(td_rewards)}")
    print(
        f"  Recompensa TD, promedio ultimos {window}: "
        f"{td_rewards[-window:].mean():.3f}"
    )
    print(
        f"  Recompensa Q-Learning, promedio ultimos {window}: "
        f"{q_rewards[-window:].mean():.3f}"
    )
    print(f"  Norma final de w: {result.td_history.weight_norms[-1]:.3f}")
    print(f"  ECM final sobre 100 estados: {result.td_history.mse_values[-1]:.3f}")
    print("  Graficas:")
    for path in result.figure_paths:
        print(f"    - {path.resolve()}")


def main(
    episodes: int = 500,
    seed: int = 42,
    show_plots: bool = True,
    output_dir: str | Path | None = None,
) -> ExperimentResult:
    env_config = EnvironmentConfig(max_steps=100)
    feature_extractor = FeatureExtractor(saturation_threshold=0.8)
    discretizer = StateDiscretizer(levels=5)
    td_agent = SemiGradientTDAgent(feature_extractor, alpha=0.015, gamma=0.95)
    td_policy = TrafficHeuristicPolicy(change_probability=0.65, seed=seed + 1)
    q_agent = TabularQLearningAgent(
        discretizer,
        alpha=0.12,
        gamma=0.95,
        epsilon=1.0,
        epsilon_min=0.03,
        epsilon_decay=0.992,
        seed=seed + 2,
    )
    runner = ExperimentRunner(
        env_config,
        td_agent,
        td_policy,
        q_agent,
        episodes=episodes,
        seed=seed,
    )
    result = runner.run()
    destination = (
        Path(output_dir)
        if output_dir is not None
        else Path(__file__).resolve().parent / "resultados"
    )
    plotter = ResultsPlotter(min(20, max(1, episodes // 5)))
    plotter.plot_all(result, destination, show_plots)
    print_summary(result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compara semi-gradiente TD lineal con Q-Learning tabular."
    )
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--no-show", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    main(
        episodes=arguments.episodes,
        seed=arguments.seed,
        show_plots=not arguments.no_show,
        output_dir=arguments.output_dir,
    )
