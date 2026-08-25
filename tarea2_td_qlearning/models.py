from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from tarea2_td_qlearning.q_learning_agent import TabularQLearningAgent
from tarea2_td_qlearning.td_agent import SemiGradientTDAgent


@dataclass
class TrainingHistory:
    rewards: list[float] = field(default_factory=list)
    weight_norms: list[float] = field(default_factory=list)
    mse_values: list[float] = field(default_factory=list)


@dataclass
class ExperimentResult:
    td_history: TrainingHistory
    q_history: TrainingHistory
    td_agent: SemiGradientTDAgent
    q_agent: TabularQLearningAgent
    evaluation_states: NDArray[np.float64]
    figure_paths: list[Path] = field(default_factory=list)
