"""Episodios del entorno cargados desde el dataset procesado (ENV-04).

Cada episodio es un mercado: sus 60 instantes de decisión con las features de `steps.parquet`, y
los puntos de precio YES de `prices_raw.parquet` con que el entorno ejecuta las órdenes (S4).
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..features.market import MARKET_FEATURES, apply_zscore


@dataclass(frozen=True)
class Episode:
    market_id: str
    w0: int
    outcome: int
    ts: np.ndarray
    p_yes: np.ndarray
    features: np.ndarray
    price_ts: np.ndarray
    price_p: np.ndarray


class MarketData:
    """Episodios en orden cronológico, accesibles por posición o por `market_id`."""

    def __init__(self, episodes: list[Episode], step_s: int) -> None:
        if not episodes:
            raise ValueError("no hay episodios")
        self.episodes = episodes
        self.step_s = step_s
        self.n_steps = len(episodes[0].ts)
        self._index = {episode.market_id: i for i, episode in enumerate(episodes)}

    def __len__(self) -> int:
        return len(self.episodes)

    def __iter__(self) -> Iterator[Episode]:
        return iter(self.episodes)

    def __getitem__(self, market_id: str) -> Episode:
        return self.episodes[self._index[market_id]]

    @property
    def market_ids(self) -> list[str]:
        return [episode.market_id for episode in self.episodes]

    @classmethod
    def from_frames(
        cls,
        markets: pd.DataFrame,
        steps: pd.DataFrame,
        prices: pd.DataFrame,
        normalization: dict[str, dict[str, float]] | None = None,
        *,
        split: str | None = None,
        step_s: int = 60,
    ) -> "MarketData":
        """Arma los episodios; con `normalization`, aplica el z-score de train a las features."""
        if split is not None:
            markets = markets[markets["split"] == split]
        markets = markets.sort_values("w0").reset_index(drop=True)
        position = pd.Series(np.arange(len(markets)), index=markets["market_id"])
        steps = steps[steps["market_id"].isin(position.index)]
        if normalization is not None:
            steps = apply_zscore(steps, normalization)
        steps = steps.assign(_m=steps["market_id"].map(position)).sort_values(["_m", "k"])
        n_steps = steps.groupby("_m").size()
        if len(n_steps) != len(markets) or n_steps.nunique() != 1:
            raise ValueError("cada mercado tiene que tener la grilla completa en steps")
        shape = (len(markets), int(n_steps.iloc[0]))
        ts = steps["ts"].to_numpy("int64").reshape(shape)
        p_yes = steps["p_yes"].to_numpy("float64").reshape(shape)
        features = steps[list(MARKET_FEATURES)].to_numpy("float32").reshape((*shape, -1))

        yes = prices[(prices["side"] == "yes") & prices["market_id"].isin(position.index)]
        yes = yes.assign(_m=yes["market_id"].map(position)).sort_values(["_m", "ts_event"])
        bounds = np.searchsorted(yes["_m"].to_numpy(), np.arange(len(markets) + 1))
        price_ts, price_p = yes["ts_event"].to_numpy("int64"), yes["p"].to_numpy("float64")

        episodes = [
            Episode(
                market_id=str(row.market_id),
                w0=int(row.w0),
                outcome=int(row.outcome),
                ts=ts[i],
                p_yes=p_yes[i],
                features=features[i],
                price_ts=price_ts[bounds[i] : bounds[i + 1]],
                price_p=price_p[bounds[i] : bounds[i + 1]],
            )
            for i, row in enumerate(markets.itertuples())
        ]
        return cls(episodes, step_s)

    @classmethod
    def load(
        cls, path: str | Path, *, split: str | None = None, normalize: bool = True
    ) -> "MarketData":
        """Lee un dataset de `make dataset`; `split` elige train, val o test."""
        path = Path(path)
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        normalization = None
        if normalize:
            stats = json.loads((path / "normalization.json").read_text(encoding="utf-8"))
            normalization = stats["features"]
        return cls.from_frames(
            pd.read_parquet(path / "markets.parquet"),
            pd.read_parquet(path / "steps.parquet"),
            pd.read_parquet(
                path / "prices_raw.parquet", columns=["market_id", "side", "ts_event", "p"]
            ),
            normalization,
            split=split,
            step_s=manifest["config"]["step_seconds"],
        )
