import numpy as np

from tarea2_td_qlearning.config import EnvironmentConfig
from tarea2_td_qlearning.environment import SimplifiedIntersectionEnv
from tarea2_td_qlearning.models import ExperimentResult, TrainingHistory
from tarea2_td_qlearning.policy import Policy
from tarea2_td_qlearning.q_learning_agent import TabularQLearningAgent
from tarea2_td_qlearning.td_agent import SemiGradientTDAgent


class ExperimentRunner:
    def __init__(
        self,
        env_config: EnvironmentConfig,
        td_agent: SemiGradientTDAgent,
        td_policy: Policy,
        q_agent: TabularQLearningAgent,
        episodes: int = 500,
        seed: int = 42,
    ) -> None:
        if episodes <= 0:
            raise ValueError("El numero de episodios debe ser positivo.")
        self.td_env = SimplifiedIntersectionEnv(env_config)
        self.q_env = SimplifiedIntersectionEnv(env_config)
        self.td_agent = td_agent
        self.td_policy = td_policy
        self.q_agent = q_agent
        self.episodes = episodes
        self.seed = seed
        sample_rng = np.random.default_rng(seed + 10_000)
        self.evaluation_states = sample_rng.uniform(0.0, 1.0, size=(100, 3))

    def run(self) -> ExperimentResult:
        td_history = TrainingHistory()
        q_history = TrainingHistory()
        for episode in range(self.episodes):
            episode_seed = self.seed + episode
            td_reward = self._run_td_episode(episode_seed)
            q_reward = self._run_q_episode(episode_seed)
            td_history.rewards.append(td_reward)
            q_history.rewards.append(q_reward)
            td_history.weight_norms.append(self.td_agent.weight_norm)
            linear_values = self.td_agent.values(self.evaluation_states)
            tabular_values = self.q_agent.state_values(self.evaluation_states)
            mse = float(np.mean((linear_values - tabular_values) ** 2))
            td_history.mse_values.append(mse)
        return ExperimentResult(
            td_history=td_history,
            q_history=q_history,
            td_agent=self.td_agent,
            q_agent=self.q_agent,
            evaluation_states=self.evaluation_states,
        )

    def _run_td_episode(self, seed: int) -> float:
        state, _ = self.td_env.reset(seed=seed)
        total_reward = 0.0
        done = False
        while not done:
            action = self.td_policy.select_action(state)
            next_state, reward, terminated, truncated, _ = self.td_env.step(action)
            done = terminated or truncated
            self.td_agent.update(state, reward, next_state, done)
            total_reward += reward
            state = next_state
        return float(total_reward)

    def _run_q_episode(self, seed: int) -> float:
        state, _ = self.q_env.reset(seed=seed)
        total_reward = 0.0
        done = False
        while not done:
            action = self.q_agent.select_action(state)
            next_state, reward, terminated, truncated, _ = self.q_env.step(action)
            done = terminated or truncated
            self.q_agent.update(state, action, reward, next_state, done)
            total_reward += reward
            state = next_state
        self.q_agent.end_episode()
        return float(total_reward)
