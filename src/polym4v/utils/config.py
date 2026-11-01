"""Configuración de experimentos en YAML, validada con pydantic.

Los parámetros que definen un experimento viven en configs/*.yaml y se versionan. Las rutas y
los secretos de cada máquina van en .env (ver paths.py); el entorno nunca cambia parámetros de
un experimento, para que el mismo YAML produzca siempre la misma corrida.
"""

from datetime import date
from pathlib import Path
from typing import Any, Literal, Self, TypeVar

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..config import ConfigurationError

M = TypeVar("M", bound=BaseModel)


class StrictModel(BaseModel):
    """Rechaza claves desconocidas y no se modifica después de cargarse."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class QualityConfig(StrictModel):
    min_points_in_window: int = Field(gt=0)
    max_gap_seconds: int = Field(gt=0)


class SplitConfig(StrictModel):
    train: float = Field(gt=0, lt=1)
    val: float = Field(gt=0, lt=1)
    test: float = Field(gt=0, lt=1)

    @model_validator(mode="after")
    def _sums_to_one(self) -> Self:
        if abs(self.train + self.val + self.test - 1) > 1e-9:
            raise ValueError("train, val y test deben sumar 1")
        return self


class DataConfig(StrictModel):
    """Dataset de una serie de mercados (docs/08, ADR-008 y ADR-013)."""

    dataset_id: str
    series_id: int
    asset: str
    date_from: date
    date_to: date
    step_seconds: int = Field(gt=0)
    window_minutes: int = Field(gt=0)
    context_minutes: int = Field(ge=0)
    quality: QualityConfig
    split: SplitConfig
    test_exclusions: Path

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.date_from >= self.date_to:
            raise ValueError("date_from debe ser anterior a date_to")
        if (self.window_minutes * 60) % self.step_seconds:
            raise ValueError("step_seconds no divide la ventana en pasos enteros")
        return self


class CostConfig(StrictModel):
    """Costos del simulador, iguales para todos los splits (S5 y ADR-009)."""

    half_spread: float = Field(ge=0, lt=0.5)
    fee_rate: float = Field(ge=0)
    fee_exponent: float = Field(ge=0)
    fee_decimals: int = Field(ge=0)
    min_fee: float = Field(ge=0)
    tick: float = Field(gt=0, lt=0.5)


class EnvConfig(StrictModel):
    """Reglas del simulador (docs/09: S4 y S10 en ADR-017, S5 y S6 en ADR-013)."""

    initial_cash: float = Field(gt=0)
    stake_fraction: float = Field(gt=0, le=1)
    latency_s: int = Field(ge=0)
    tolerance_s: int = Field(gt=0)
    no_open_last_minutes: int = Field(ge=0)
    normalize: bool = True
    costs: CostConfig

    @model_validator(mode="after")
    def _execution_window(self) -> Self:
        if self.latency_s >= self.tolerance_s:
            raise ValueError("latency_s debe ser menor que tolerance_s")
        return self


RewardBase = Literal["pnl", "pnl_mid", "terminal"]


class RewardConfig(StrictModel):
    """Recompensa del entorno (docs/02, sección 2.4, S9 en ADR-016 y la lista de ENV-08).

    `pnl_risk` y `pnl_hold` suman su penalización a `base`, la ganadora de la etapa A.
    """

    name: Literal["pnl", "pnl_mid", "terminal", "pnl_risk", "pnl_hold", "utility"]
    base: RewardBase = "pnl"
    lambda_dd: float = Field(default=0.0, ge=0)
    lambda_hold: float = Field(default=0.0, ge=0)
    utility_a: float = Field(default=1.0, gt=0)
    lambda_invalid: float = Field(default=0.0, ge=0)
    scale: Literal["v0", "stake"] = "v0"

    @model_validator(mode="after")
    def _check_variant(self) -> Self:
        # Un parámetro que la variante no usa casi siempre es un error de la config de la ablación.
        if self.lambda_dd > 0 and self.name != "pnl_risk":
            raise ValueError("lambda_dd solo se usa con pnl_risk")
        if self.lambda_hold > 0 and self.name != "pnl_hold":
            raise ValueError("lambda_hold solo se usa con pnl_hold")
        if self.base != "pnl" and self.name not in ("pnl_risk", "pnl_hold"):
            raise ValueError("base solo se usa con pnl_risk y pnl_hold")
        return self


class SimulatorConfig(StrictModel):
    """`configs/env.yaml`: el dataset, las reglas del entorno y la recompensa."""

    dataset_id: str
    env: EnvConfig
    reward: RewardConfig


class AgentConfig(StrictModel):
    """Algoritmo e hiperparámetros de un agente (AGT-04, AGT-05 y AGT-08).

    `params` pasa tal cual al constructor del algoritmo los hiperparámetros propios de cada uno
    (por ejemplo `n_steps` en PPO, `buffer_size` en DQN o `alpha` en CQL); la librería los valida.
    En CQL y BC, `total_timesteps` son pasos de gradiente sobre el dataset offline y `n_envs` no
    se usa.
    """

    algo: Literal["ppo", "dqn", "cql", "bc"]
    policy: str = "MlpPolicy"
    net_arch: list[int] = Field(default_factory=lambda: [64, 64])
    learning_rate: float = Field(gt=0)
    gamma: float = Field(gt=0, le=1)
    total_timesteps: int = Field(gt=0)
    n_envs: int = Field(default=1, gt=0)
    checkpoints: int = Field(default=10, gt=0)
    params: dict[str, Any] = Field(default_factory=dict)


class OfflineDataConfig(StrictModel):
    """Cómo se recolecta el dataset offline (AGT-07): baselines con ε-greedy sobre train."""

    policies: list[str] = Field(min_length=1)
    epsilon: float = Field(ge=0, le=1)
    seed: int = 0


class ExperimentConfig(StrictModel):
    """`configs/ppo.yaml` y `configs/dqn.yaml`: dataset, simulador, agente y semillas (docs/02).

    Los checkpoints se evalúan en `eval_split` con la métrica principal de EVA-01; según el
    protocolo es val, que solo se abre después de aprobarlo.
    """

    dataset_id: str
    env: EnvConfig
    reward: RewardConfig
    agent: AgentConfig
    seeds: list[int] = Field(min_length=1)
    eval_split: Literal["train", "val"] = "val"
    offline: OfflineDataConfig | None = None

    @model_validator(mode="after")
    def _offline_needs_data(self) -> Self:
        if self.agent.algo in ("cql", "bc") and self.offline is None:
            raise ValueError("CQL y BC necesitan la sección offline con el dataset a recolectar")
        return self


# Cada archivo configs/<nombre>.yaml se valida con el modelo de su nombre.
CONFIG_MODELS: dict[str, type[BaseModel]] = {
    "data": DataConfig,
    "costs": CostConfig,
    "env": SimulatorConfig,
    "ppo": ExperimentConfig,
    "dqn": ExperimentConfig,
    "cql": ExperimentConfig,
    "bc": ExperimentConfig,
}


def load_config(path: str | Path, model: type[M]) -> M:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return model.model_validate(data)


def load_named(path: str | Path) -> BaseModel:
    """Elige el modelo por el nombre del archivo (data.yaml usa DataConfig)."""
    stem = Path(path).stem
    if stem not in CONFIG_MODELS:
        known = ", ".join(sorted(CONFIG_MODELS))
        raise ConfigurationError(f"No hay un modelo para '{stem}'. Conocidos: {known}.")
    return load_config(path, CONFIG_MODELS[stem])


def save_resolved(config: BaseModel, path: str | Path) -> Path:
    """Guarda la configuración resuelta junto a una corrida."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False, allow_unicode=True)
    target.write_text(text, encoding="utf-8")
    return target
