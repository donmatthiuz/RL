"""Arma la muestra de test de la demo publicada (EVA-09 y EVA-13), con `make demo-muestra`.

Copia a `app/trayectorias/` las trayectorias de test de PPO s0 (la semilla mediana del mejor
agente), `NoTrade` y `fair_value`, y escribe `mercados_test.parquet`: la pregunta, la apertura, el
cierre, el precio de BTC minuto a minuto y el resultado de cada mercado de test. No evalúa nada: lee
las trayectorias que dejó EVA-06 y el dataset.
"""

import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from polym4v.utils.config import DataConfig, load_config  # noqa: E402
from polym4v.utils.paths import get_paths  # noqa: E402

SAMPLE = Path(__file__).resolve().parent / "trayectorias"
RUNS = ("20261102-152322_ppo_pnl_risk_s0", "no_trade", "fair_value")
MARKET_COLUMNS = ["market_id", "question", "w0", "w1", "spot_open", "spot_close", "outcome"]


def market_table(dataset: Path, split: str) -> pd.DataFrame:
    """Un renglón por minuto de cada mercado del split, con los datos del mercado repetidos."""
    markets = pd.read_parquet(dataset / "markets.parquet")
    markets = markets.loc[markets["split"] == split, MARKET_COLUMNS]
    steps = pd.read_parquet(dataset / "steps.parquet", columns=["market_id", "k", "ts", "spot"])
    table = steps.merge(markets, on="market_id", how="inner")
    return table.sort_values(["w0", "k"]).reset_index(drop=True)


def main() -> None:
    paths = get_paths()
    config = load_config(paths.configs / "data.yaml", DataConfig)
    SAMPLE.mkdir(exist_ok=True)
    for run in RUNS:
        shutil.copy(paths.reports / "trajectories" / f"{run}_test.parquet", SAMPLE)
    table = market_table(paths.processed / config.dataset_id, "test")
    # zstd al máximo: el hook de pre-commit no deja subir archivos de más de 1 MB.
    table.to_parquet(
        SAMPLE / "mercados_test.parquet", index=False, compression="zstd", compression_level=19
    )
    print(f"{table['market_id'].nunique()} mercados y {len(table)} minutos en {SAMPLE}")


if __name__ == "__main__":
    main()
