"""Búsqueda acotada de hiperparámetros (AGT-09), aprobada el 02/11/2026.

La grilla vive aquí, versionada, para que quede registro de cuántas configuraciones se probaron
(sección 5 del protocolo de EVA-01). Cada punto se escribe como una config completa a partir de la
config base del algoritmo, con las semillas de la búsqueda; la elección se hace en val con
`polym4v hparams`.
"""

from itertools import product
from pathlib import Path
from typing import Any

from ..utils.config import ExperimentConfig, load_config, save_resolved

SEEDS = [0, 1]
FINAL_SEEDS = [0, 1, 2, 3, 4]  # AGT-10 y sección 5 del protocolo
# Algoritmo → parámetro → valores. `params.x` es un parámetro propio de SB3 o de d3rlpy.
GRID: dict[str, dict[str, list[Any]]] = {
    "ppo": {
        "learning_rate": [1e-4, 3e-4],
        "params.ent_coef": [0.0, 0.01],
        "net_arch": [[64, 64], [128, 128]],
    },
    "dqn": {
        "learning_rate": [1e-4, 3e-4],
        "params.exploration_fraction": [0.1, 0.3],
        "params.target_update_interval": [2000, 10000],
    },
    "cql": {"params.alpha": [0.5, 1.0, 4.0], "learning_rate": [3e-5, 1e-4]},
    "bc": {"learning_rate": [3e-4, 1e-3, 3e-3]},
}
SHORT = {
    "learning_rate": "lr",
    "net_arch": "net",
    "params.ent_coef": "ent",
    "params.exploration_fraction": "expl",
    "params.target_update_interval": "tgt",
    "params.alpha": "alpha",
}


def _value(value: Any) -> str:
    if isinstance(value, list):
        return "x".join(str(v) for v in value)
    return f"{value:g}" if isinstance(value, float) else str(value)


def point_id(point: dict[str, Any]) -> str:
    return "_".join(f"{SHORT[key]}{_value(value)}" for key, value in point.items())


def points(algo: str) -> list[dict[str, Any]]:
    grid = GRID[algo]
    return [dict(zip(grid, values, strict=True)) for values in product(*grid.values())]


def apply(config: ExperimentConfig, point: dict[str, Any]) -> ExperimentConfig:
    """La config base con los valores del punto y las semillas de la búsqueda."""
    agent = config.agent.model_dump()
    for key, value in point.items():
        if key.startswith("params."):
            agent["params"][key.removeprefix("params.")] = value
        else:
            agent[key] = value
    data = config.model_dump() | {"agent": agent, "seeds": SEEDS}
    return ExperimentConfig.model_validate(data)


def write_grid(configs: Path, out: Path) -> list[Path]:
    """Escribe `out/<algo>/<punto>.yaml` para cada punto de la grilla."""
    written = []
    for algo in GRID:
        base = load_config(configs / f"{algo}.yaml", ExperimentConfig)
        for point in points(algo):
            written.append(
                save_resolved(apply(base, point), out / algo / f"{point_id(point)}.yaml")
            )
    return written


def write_final(grid_dir: Path, best_by_algo: dict[str, str], out: Path) -> list[Path]:
    """`out/<algo>.yaml`: el mejor punto de cada algoritmo, con las 5 semillas de AGT-10.

    `best_by_algo` es la salida de `polym4v hparams` (`<algo>/<punto>`).
    """
    written = []
    for algo, variant in best_by_algo.items():
        point = variant.split("/", 1)[1]
        config = load_config(grid_dir / algo / f"{point}.yaml", ExperimentConfig)
        final = config.model_copy(update={"seeds": FINAL_SEEDS})
        written.append(save_resolved(final, out / f"{algo}.yaml"))
    return written
