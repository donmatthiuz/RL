"""Entrenamiento de PPO y DQN con stable-baselines3 (AGT-04 y AGT-05).

Sigue la sección 5 del protocolo de EVA-01: cada semilla guarda un número fijo de checkpoints a
intervalos iguales (10 por defecto), cada uno se evalúa en el split de evaluación con la métrica
principal (retorno medio por mercado sobre el monto) y queda como `best.zip` el mejor. La
evaluación recorre todos los mercados del split una vez y en orden, con el mismo backtest que los
baselines.

Cada corrida guarda en `models/<algo>/<run_id>/` la config resuelta, el dataset, el commit, la
semilla, los checkpoints, `best.zip`, `metrics.json` y los registros de TensorBoard.
"""

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from stable_baselines3 import DQN, PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

from ..env.market_data import MarketData
from ..env.market_env import PolymarketEnv
from ..evaluation.backtest import run_backtest
from ..evaluation.metrics import summarize
from ..utils.config import ExperimentConfig, save_resolved
from ..utils.seeding import set_global_seed
from .adapters import SB3Policy

ALGOS: dict[str, type[PPO] | type[DQN]] = {"ppo": PPO, "dqn": DQN}


def run_id(config: ExperimentConfig, seed: int, now: datetime | None = None) -> str:
    """`<fecha>_<agente>_<recompensa>_s<semilla>` (docs/02, sección 5)."""
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}_{config.agent.algo}_{config.reward.name}_s{seed}"


def git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip()


class CheckpointEvaluation(BaseCallback):
    """Guarda y evalúa el modelo cada `every` pasos con la métrica principal de EVA-01."""

    def __init__(self, every: int, eval_env: PolymarketEnv, folder: Path, name: str) -> None:
        super().__init__()
        self.every, self.eval_env, self.folder, self.name = every, eval_env, folder, name
        self.next_at = every
        self.results: list[dict[str, Any]] = []

    def _on_step(self) -> bool:
        if self.num_timesteps >= self.next_at:
            self.next_at += self.every
            self.evaluate()
        return True

    def evaluate(self) -> None:
        path = self.folder / f"step_{self.num_timesteps}.zip"
        self.model.save(path)
        env = self.eval_env
        summary = summarize(
            run_backtest(SB3Policy(self.model, self.name), env),
            env.config.initial_cash,
            env.stake,
        )
        self.results.append({"timesteps": self.num_timesteps, "path": path.name, **summary})
        self.logger.record("eval/mean_return", summary["mean_return"])
        self.logger.record("eval/trades_per_market", summary["trades_per_market"])


def train(
    config: ExperimentConfig,
    seed: int,
    train_data: MarketData,
    eval_data: MarketData,
    out: str | Path,
) -> dict[str, Any]:
    """Entrena una semilla y devuelve `metrics.json`."""
    out = Path(out)
    (out / "checkpoints").mkdir(parents=True, exist_ok=True)
    set_global_seed(seed)
    agent = config.agent

    def make_env() -> Monitor:
        return Monitor(PolymarketEnv(train_data, config.env, config.reward))

    vec_env = DummyVecEnv([make_env for _ in range(agent.n_envs)])
    model = ALGOS[agent.algo](
        agent.policy,
        vec_env,
        learning_rate=agent.learning_rate,
        gamma=agent.gamma,
        policy_kwargs={"net_arch": agent.net_arch},
        seed=seed,
        device="cpu",
        tensorboard_log=str(out / "tensorboard"),
        verbose=0,
        **agent.params,
    )
    every = max(agent.total_timesteps // agent.checkpoints, 1)
    eval_env = PolymarketEnv(eval_data, config.env, config.reward)
    callback = CheckpointEvaluation(every, eval_env, out / "checkpoints", agent.algo)
    model.learn(total_timesteps=agent.total_timesteps, callback=callback, tb_log_name="run")
    if len(callback.results) < agent.checkpoints:
        # El último intervalo puede quedar corto por el tamaño de los rollouts.
        callback.evaluate()

    # En un empate gana el checkpoint más temprano.
    best = max(callback.results, key=lambda r: (r["mean_return"], -r["timesteps"]))
    shutil.copyfile(out / "checkpoints" / best["path"], out / "best.zip")
    save_resolved(config, out / "config.yaml")
    metrics = {
        "run_id": out.name,
        "algo": agent.algo,
        "seed": seed,
        "dataset_id": config.dataset_id,
        "git_commit": git_commit(),
        "eval_split": config.eval_split,
        "eval_markets": len(eval_data),
        "best": best,
        "checkpoints": callback.results,
    }
    (out / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False, default=float), encoding="utf-8"
    )
    return metrics
