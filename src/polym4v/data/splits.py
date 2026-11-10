"""Split temporal por mercado (DAT-06) con las exclusiones de test de S11.

Los mercados se ordenan por el inicio de su ventana: los más antiguos van a train, los siguientes
a val y los más recientes a test. Después se sacan de test los mercados que se usaron en los
análisis previos al diseño (S11), porque con ellos se fijaron umbrales y latencias.
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ConfigDict

from ..utils.config import SplitConfig


class _Range(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    desde: datetime
    hasta: datetime
    motivo: str


class SplitExclusions(BaseModel):
    """Contenido de `configs/test_exclusions.json`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    descripcion: str
    slugs: frozenset[str]
    rangos_end_date_utc: tuple[_Range, ...]


def load_exclusions(path: str | Path) -> SplitExclusions:
    return SplitExclusions.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def _excluded(markets: pd.DataFrame, exclusions: SplitExclusions) -> pd.Series:
    """Mercados de las muestras previas. Los rangos se aplican sobre `w1`, que en los mercados
    recientes coincide con el `end_date` de Gamma."""
    hit = markets["slug"].isin(exclusions.slugs)
    for span in exclusions.rangos_end_date_utc:
        hit |= markets["w1"].between(int(span.desde.timestamp()), int(span.hasta.timestamp()))
    return hit


def assign_splits(
    markets: pd.DataFrame, split: SplitConfig, exclusions: SplitExclusions
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve los mercados con su columna `split` y los que se sacaron de test, con el motivo."""
    ordered = markets.sort_values(["w0", "market_id"], kind="stable").reset_index(drop=True)
    n = len(ordered)
    train_end = round(n * split.train)
    val_end = round(n * (split.train + split.val))
    names = ["train"] * train_end + ["val"] * (val_end - train_end) + ["test"] * (n - val_end)
    ordered["split"] = pd.Series(names, dtype="str")

    dropped = (ordered["split"] == "test") & _excluded(ordered, exclusions)
    removed = ordered.loc[dropped, ["market_id"]].assign(motivo="excluido de test (S11)")
    return ordered.loc[~dropped].reset_index(drop=True), removed.reset_index(drop=True)
