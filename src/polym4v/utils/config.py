"""Configuración de experimentos en YAML, validada con pydantic.

Los parámetros que definen un experimento viven en configs/*.yaml y se versionan. Las rutas y
los secretos de cada máquina van en .env (ver paths.py); el entorno nunca cambia parámetros de
un experimento, para que el mismo YAML produzca siempre la misma corrida.
"""

from datetime import date
from pathlib import Path
from typing import Self, TypeVar

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


# Cada archivo configs/<nombre>.yaml se valida con el modelo de su nombre.
CONFIG_MODELS: dict[str, type[BaseModel]] = {"data": DataConfig, "costs": CostConfig}


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
