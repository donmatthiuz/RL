from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

from tarea2_td_qlearning.models import ExperimentResult


class ResultsPlotter:
    def __init__(self, smoothing_window: int = 20) -> None:
        self.smoothing_window = smoothing_window

    def plot_all(
        self, result: ExperimentResult, output_dir: Path, show: bool = True
    ) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = [
            self._plot_learning_curves(result, output_dir),
            self._plot_weight_norm(result, output_dir),
            self._plot_mse(result, output_dir),
        ]
        if show:
            plt.show()
        else:
            plt.close("all")
        result.figure_paths = paths
        return paths

    def _plot_learning_curves(
        self, result: ExperimentResult, output_dir: Path
    ) -> Path:
        td_rewards = np.asarray(result.td_history.rewards)
        q_rewards = np.asarray(result.q_history.rewards)
        episodes = np.arange(1, len(td_rewards) + 1)
        fig, ax = plt.subplots(figsize=(10, 5.5))
        ax.plot(episodes, td_rewards, color="#2878B5", alpha=0.16)
        ax.plot(episodes, q_rewards, color="#D95319", alpha=0.16)
        ax.plot(
            episodes,
            self._moving_average(td_rewards),
            label="Semi-gradiente TD(0) lineal",
            color="#2878B5",
            linewidth=2.2,
        )
        ax.plot(
            episodes,
            self._moving_average(q_rewards),
            label="Q-Learning tabular (5 niveles)",
            color="#D95319",
            linewidth=2.2,
        )
        ax.set(
            title="Curvas de aprendizaje",
            xlabel="Episodio",
            ylabel="Recompensa acumulada",
        )
        ax.grid(alpha=0.25)
        ax.legend()
        fig.tight_layout()
        path = output_dir / "01_curvas_aprendizaje.png"
        fig.savefig(path, dpi=160)
        return path

    def _plot_weight_norm(self, result: ExperimentResult, output_dir: Path) -> Path:
        norms = np.asarray(result.td_history.weight_norms)
        episodes = np.arange(1, len(norms) + 1)
        fig, ax = plt.subplots(figsize=(10, 5.5))
        ax.plot(episodes, norms, color="#2CA02C", linewidth=2.0)
        ax.set(
            title="Evolucion de la norma del vector de pesos",
            xlabel="Episodio",
            ylabel=r"$\|w\|_2$",
        )
        ax.grid(alpha=0.25)
        fig.tight_layout()
        path = output_dir / "02_norma_pesos.png"
        fig.savefig(path, dpi=160)
        return path

    def _plot_mse(self, result: ExperimentResult, output_dir: Path) -> Path:
        mse_values = np.asarray(result.td_history.mse_values)
        episodes = np.arange(1, len(mse_values) + 1)
        fig, ax = plt.subplots(figsize=(10, 5.5))
        ax.plot(episodes, mse_values, color="#9467BD", alpha=0.20)
        ax.plot(
            episodes,
            self._moving_average(mse_values),
            color="#9467BD",
            linewidth=2.2,
        )
        ax.set(
            title=r"ECM entre $\hat{V}(s;w)$ y $V_{tabular}(s)$",
            xlabel="Episodio",
            ylabel="Error cuadratico medio (100 estados fijos)",
        )
        ax.grid(alpha=0.25)
        fig.tight_layout()
        path = output_dir / "03_error_cuadratico_medio.png"
        fig.savefig(path, dpi=160)
        return path

    def _moving_average(self, values: NDArray[np.float64]) -> NDArray[np.float64]:
        if len(values) < self.smoothing_window or self.smoothing_window <= 1:
            return values.copy()
        kernel = np.ones(self.smoothing_window) / self.smoothing_window
        valid = np.convolve(values, kernel, mode="valid")
        prefix = np.full(self.smoothing_window - 1, np.nan)
        return np.concatenate((prefix, valid))
