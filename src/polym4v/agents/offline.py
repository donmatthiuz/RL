"""Offline RL: dataset de transiciones (AGT-07) y entrenamiento de CQL y BC con d3rlpy (AGT-08).

El dataset se recolecta con los baselines y ε-greedy sobre los mercados de train, con el mismo
entorno que todos los agentes. Guarda la acción **ejecutada**, no la pedida (S6): una acción
inválida queda como WAIT. CQL y BC nunca interactúan con el entorno al entrenar; sus checkpoints se
evalúan como los de PPO y DQN (sección 5 del protocolo de EVA-01).
"""

import hashlib
import json
import shutil
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import d3rlpy
import numpy as np

from ..env.market_data import MarketData
from ..env.market_env import PolymarketEnv
from ..evaluation.backtest import run_backtest
from ..evaluation.metrics import summarize
from ..utils.config import ExperimentConfig, OfflineDataConfig, save_resolved
from .adapters import D3rlpyPolicy, quiet_d3rlpy
from .base import Action, Policy
from .baselines import baselines
from .train_sb3 import git_commit

quiet_d3rlpy()


def offline_path(folder: Path, dataset_id: str, offline: OfflineDataConfig) -> Path:
    """Nombre del dataset offline: cambia si cambian el dataset, los baselines, ε o la semilla."""
    key = f"{','.join(offline.policies)}_eps{offline.epsilon}_s{offline.seed}"
    digest = hashlib.sha256(key.encode()).hexdigest()[:8]
    return folder / f"{dataset_id}_{digest}.h5"


def collect(
    env: PolymarketEnv,
    policies: Sequence[Policy],
    *,
    epsilon: float,
    seed: int,
    markets: Sequence[str] | None = None,
) -> dict[str, np.ndarray]:
    """Transiciones `(obs, acción ejecutada, recompensa, fin)` de cada baseline en cada mercado."""
    rng = np.random.default_rng(seed)
    observations, actions, requested, rewards, terminals = [], [], [], [], []
    for policy in policies:
        for market_id in env.data.market_ids if markets is None else markets:
            policy.reset()
            obs, info = env.reset(options={"market_id": market_id})
            done = False
            while not done:
                explore = rng.random() < epsilon
                action = int(rng.integers(len(Action))) if explore else policy.act(obs, info)
                next_obs, reward, done, _, info = env.step(action)
                observations.append(obs)
                actions.append(info["action_executed"])
                requested.append(action)
                rewards.append(reward)
                terminals.append(done)
                obs = next_obs
    return {
        "observations": np.array(observations, dtype=np.float32),
        "actions": np.array(actions, dtype=np.int64),
        "requested": np.array(requested, dtype=np.int64),
        "rewards": np.array(rewards, dtype=np.float32),
        "terminals": np.array(terminals, dtype=np.float32),
    }


def build_offline_dataset(config: ExperimentConfig, data: MarketData, out: Path) -> dict[str, Any]:
    """Recolecta y guarda el dataset en `out` (HDF5 de d3rlpy) con su manifest al lado."""
    if config.offline is None:
        raise ValueError("la config no tiene sección offline")
    makers = baselines(config.env.costs, seed=config.offline.seed)
    unknown = sorted(set(config.offline.policies) - set(makers))
    if unknown:
        raise ValueError(f"baselines desconocidos: {', '.join(unknown)}")
    env = PolymarketEnv(data, config.env, config.reward)
    policies = [makers[name]() for name in config.offline.policies]
    arrays = collect(env, policies, epsilon=config.offline.epsilon, seed=config.offline.seed)
    dataset = d3rlpy.dataset.MDPDataset(
        observations=arrays["observations"],
        actions=arrays["actions"],
        rewards=arrays["rewards"],
        terminals=arrays["terminals"],
        action_space=d3rlpy.ActionSpace.DISCRETE,
        action_size=len(Action),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w+b") as f:
        dataset.dump(f)
    manifest = {
        "dataset_id": config.dataset_id,
        "built_at": datetime.now(UTC).isoformat(),
        "offline": config.offline.model_dump(),
        "env": config.env.model_dump(mode="json"),
        "reward": config.reward.model_dump(mode="json"),
        "markets": len(data),
        "transitions": len(arrays["actions"]),
        "episodes": int(arrays["terminals"].sum()),
        "invalid_share": float((arrays["actions"] != arrays["requested"]).mean()),
        "actions": np.bincount(arrays["actions"], minlength=len(Action)).tolist(),
        "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    }
    out.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def load_offline_dataset(path: Path) -> Any:
    with path.open("rb") as f:
        return d3rlpy.dataset.ReplayBuffer.load(f, d3rlpy.dataset.InfiniteBuffer())


def make_algo(config: ExperimentConfig) -> Any:
    agent = config.agent
    encoder = d3rlpy.models.VectorEncoderFactory(hidden_units=agent.net_arch)
    common = {"learning_rate": agent.learning_rate, "encoder_factory": encoder} | agent.params
    if agent.algo == "cql":
        return d3rlpy.algos.DiscreteCQLConfig(gamma=agent.gamma, **common).create(device=False)
    if agent.algo == "bc":
        return d3rlpy.algos.DiscreteBCConfig(**common).create(device=False)
    raise ValueError(f"{agent.algo} no es un algoritmo offline")


def train_offline(
    config: ExperimentConfig,
    seed: int,
    dataset_path: Path,
    eval_data: MarketData,
    out: str | Path,
) -> dict[str, Any]:
    """Entrena CQL o BC sobre el dataset offline y elige el mejor de sus checkpoints."""
    out = Path(out)
    (out / "checkpoints").mkdir(parents=True, exist_ok=True)
    d3rlpy.seed(seed)
    agent = config.agent
    algo = make_algo(config)
    eval_env = PolymarketEnv(eval_data, config.env, config.reward)
    results = []
    every = max(agent.total_timesteps // agent.checkpoints, 1)
    fitter = algo.fitter(
        load_offline_dataset(dataset_path),
        n_steps=every * agent.checkpoints,
        n_steps_per_epoch=every,
        experiment_name=out.name,
        with_timestamp=False,
        logger_adapter=d3rlpy.logging.FileAdapterFactory(root_dir=str(out / "d3rlpy_logs")),
        show_progress=False,
        save_interval=agent.checkpoints + 1,
    )
    for epoch, _ in fitter:
        path = out / "checkpoints" / f"step_{epoch * every}.d3"
        algo.save(str(path))
        summary = summarize(
            run_backtest(D3rlpyPolicy(algo, agent.algo), eval_env),
            config.env.initial_cash,
            eval_env.stake,
        )
        results.append({"timesteps": epoch * every, "path": path.name, **summary})

    best = max(results, key=lambda r: (r["mean_return"], -r["timesteps"]))
    shutil.copyfile(out / "checkpoints" / best["path"], out / "best.d3")
    save_resolved(config, out / "config.yaml")
    metrics = {
        "run_id": out.name,
        "algo": agent.algo,
        "seed": seed,
        "dataset_id": config.dataset_id,
        "offline_dataset": dataset_path.name,
        "git_commit": git_commit(),
        "eval_split": config.eval_split,
        "eval_markets": len(eval_data),
        "best": best,
        "checkpoints": results,
    }
    (out / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False, default=float), encoding="utf-8"
    )
    return metrics
