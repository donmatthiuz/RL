"""Comparación de cada agente con el baseline de referencia (secciones 4, 6 y 7 de EVA-01).

Agrupa las semillas de cada agente por su `run_id` y aplica la prueba de `stats.py`. El baseline de
referencia y el largo de bloque se fijan en val y se guardan: en test se leen, no se recalculan.
"""

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import stats

NO_TRADE = "no_trade"
PARAMS_FILE = "protocol_params.json"
BASELINE_CONFIDENCE = 0.95  # Sección 4: una heurística tiene que ganarle a NoTrade con este IC.
TEST_DAYS = 73  # Sección 2: días de test, para la diferencia mínima detectable.
# `run_id` = <fecha>_<agente>_<recompensa>_s<semilla> (docs/02, sección 5).
AGENT_LABEL = re.compile(r"^\d{8}-\d{6}_(?P<group>[a-z0-9]+_[a-z0-9_]+)_s(?P<seed>\d+)$")

Frames = Mapping[tuple[str, bool], pd.DataFrame]

COLUMNS = {
    "group": "Agente",
    "strict": "Estricto",
    "role": "Comparación",
    "baseline": "Baseline",
    "seeds": "Semillas",
    "mean": "Media de D",
    "lower": "IC inferior",
    "upper": "IC superior",
    "classification": "Clasificación",
    "nonzero_markets": "Mercados con D ≠ 0",
    "nonzero_days": "Días con D ≠ 0",
    "trade_share": "P(D ≠ 0)",
    "mean_when_trading": "E[D | D ≠ 0]",
    "reliable": "IC confiable",
    "mde": "MDE",
    "depends_on_liquidity": "Depende de liquidez",
}


def agent_groups(frames: Frames, strict: bool) -> dict[str, list[pd.DataFrame]]:
    """Semillas por agente y recompensa en un modo, en orden; una semilla repetida es un error."""
    seeds: dict[str, dict[int, pd.DataFrame]] = {}
    for (label, is_strict), frame in frames.items():
        match = AGENT_LABEL.match(label)
        if match is None or is_strict != strict:
            continue
        group, seed = match["group"], int(match["seed"])
        if seed in seeds.setdefault(group, {}):
            raise ValueError(f"{group} tiene más de una corrida con la semilla {seed}")
        seeds[group][seed] = frame
    return {g: [by_seed[s] for s in sorted(by_seed)] for g, by_seed in sorted(seeds.items())}


def _baseline_returns(
    frames: Frames, name: str, strict: bool, initial_cash: float, stake: float
) -> np.ndarray | None:
    """Retorno del baseline por mercado; NoTrade es igual en los dos modos, porque no opera."""
    frame = frames.get((name, strict))
    if frame is None and name == NO_TRADE:
        frame = frames.get((name, False))
    if frame is None:
        return None
    return stats.returns_by_seed([frame], initial_cash, stake)[:, 0]


def select_baseline(frames: Frames, initial_cash: float, stake: float) -> str:
    """Sección 4: NoTrade, salvo que una heurística le gane con el IC 95 % por encima de cero."""
    no_trade = frames[(NO_TRADE, False)]
    days = stats.market_days(no_trade)
    reference = stats.returns_by_seed([no_trade], initial_cash, stake)
    best, best_mean = NO_TRADE, 0.0
    for (label, strict), frame in sorted(frames.items()):
        if strict or label == NO_TRADE or AGENT_LABEL.match(label):
            continue
        differences = stats.returns_by_seed([frame], initial_cash, stake) - reference
        block = stats.politis_white_block(stats.daily_means(differences, days))
        mean, lower, _ = stats.bootstrap_ci(
            differences, days, mean_block=block, confidence=BASELINE_CONFIDENCE
        )
        if lower > 0 and mean > best_mean:
            best, best_mean = label, mean
    return best


def freeze_params(frames: Frames, initial_cash: float, stake: float) -> dict[str, Any] | None:
    """Baseline, largo de bloque y MDE por agente; None si no hay agentes o falta NoTrade."""
    groups = agent_groups(frames, strict=False)
    if not groups or (NO_TRADE, False) not in frames:
        return None
    baseline = select_baseline(frames, initial_cash, stake)
    returns = _baseline_returns(frames, baseline, False, initial_cash, stake)
    assert returns is not None
    blocks, effects = {}, {}
    for group, seeds in groups.items():
        days = stats.market_days(seeds[0])
        differences = stats.returns_by_seed(seeds, initial_cash, stake) - returns[:, np.newaxis]
        blocks[group] = stats.politis_white_block(stats.daily_means(differences, days))
        effects[group] = stats.minimum_detectable_effect(differences, days, test_days=TEST_DAYS)
    return {"baseline": baseline, "mean_block": blocks, "mde": effects}


def save_params(params: dict[str, Any], folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / PARAMS_FILE).write_text(json.dumps(params, indent=2), encoding="utf-8")


def load_params(folder: Path) -> dict[str, Any]:
    """Lo que se fijó en val; sin eso no se puede evaluar test (secciones 2 y 4)."""
    path = folder / PARAMS_FILE
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}: corre antes el reporte de val")
    return json.loads(path.read_text(encoding="utf-8"))


def _row(
    group: str,
    seeds: list[pd.DataFrame],
    baseline: str,
    role: str,
    strict: bool,
    returns: np.ndarray,
    block: float,
    initial_cash: float,
    stake: float,
) -> dict[str, Any]:
    result = stats.compare(
        stats.returns_by_seed(seeds, initial_cash, stake),
        returns,
        stats.market_days(seeds[0]),
        mean_block=block,
    )
    return {
        "group": group,
        "strict": strict,
        "role": role,
        "baseline": baseline,
        "seeds": len(seeds),
        "mean": result.mean,
        "lower": result.lower,
        "upper": result.upper,
        "classification": result.classification,
        "nonzero_markets": result.nonzero_markets,
        "nonzero_days": result.nonzero_days,
        "trade_share": result.trade_share,
        "mean_when_trading": result.mean_when_trading,
        "reliable": result.reliable,
    }


def compare_agents(
    frames: Frames, params: Mapping[str, Any], initial_cash: float, stake: float
) -> pd.DataFrame:
    """Una fila por agente, modo y comparación, con lo que pide la sección 6 del protocolo."""
    baseline = params["baseline"]
    rows = []
    for strict in (False, True):
        for group, seeds in agent_groups(frames, strict).items():
            if group not in params["mean_block"]:
                raise ValueError(f"{group} no estaba en val: no tiene largo de bloque fijado")
            block = params["mean_block"][group]
            targets = [(baseline, "principal")]
            if baseline != NO_TRADE:
                targets.append((NO_TRADE, "secundaria"))
            for name, role in targets:
                returns = _baseline_returns(frames, name, strict, initial_cash, stake)
                if returns is not None:
                    rows.append(
                        _row(group, seeds, name, role, strict, returns, block, initial_cash, stake)
                    )
    table = pd.DataFrame(rows)
    if table.empty:
        return table
    # Sección 6: si la clasificación cambia entre modos, depende de liquidez no verificable.
    principal = table[table["role"] == "principal"]
    classes = principal.groupby("group")["classification"].nunique()
    table["depends_on_liquidity"] = table["group"].map(classes.gt(1)).fillna(False).astype(bool)
    # Sección 7: la MDE se fija en val, antes de abrir test, y se reporta con cada comparación.
    table["mde"] = table["group"].map(params["mde"])
    return table


def _cell(value: Any) -> str:
    if isinstance(value, bool | np.bool_):
        return "sí" if value else "no"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def comparison_markdown(table: pd.DataFrame, split: str) -> str:
    """Tabla de la prueba en Markdown, con el aviso de los IC poco confiables."""
    lines = [
        f"## Prueba del protocolo en {split}",
        "",
        "| " + " | ".join(COLUMNS.values()) + " |",
        "| " + " | ".join("---" for _ in COLUMNS) + " |",
    ]
    for _, row in table.iterrows():
        lines.append("| " + " | ".join(_cell(row[c]) for c in COLUMNS) + " |")
    undetectable = table[table["mde"] > stats.DELTA_MIN]
    for group, mde in undetectable.drop_duplicates("group")[["group", "mde"]].itertuples(
        index=False
    ):
        lines += [
            "",
            f"{group}: la MDE ({mde:.4f}) es mayor que Δ_min ({stats.DELTA_MIN:.4f}), así que test "
            "no puede detectar diferencias de ese tamaño.",
        ]
    if not table["reliable"].all():
        lines += [
            "",
            f"Con menos de {stats.MIN_NONZERO_MARKETS} mercados con D ≠ 0, el IC no es confiable.",
        ]
    return "\n".join(lines) + "\n"
