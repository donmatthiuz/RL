"""Prueba estadística del protocolo de evaluación (EVA-04, secciones 6 y 7 de EVA-01).

Compara un agente con un baseline por la diferencia pareada por mercado, `D_i = R_i(agente) -
R_i(baseline)`. El intervalo de confianza es un bootstrap de dos niveles: remuestrea los días con un
bootstrap estacionario y, en cada réplica, las semillas del agente, para que hable del algoritmo y
no de estas redes. Todas las funciones son puras: la aleatoriedad entra por `seed`.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
import pandas as pd

from .backtest import episode_results

REPLICAS = 10_000
# Bonferroni sobre las 4 comparaciones principales: unilateral α = 0,025 / 4 (sección 6).
FAMILY_CONFIDENCE = 1 - 2 * 0.025 / 4
DELTA_MIN = 0.01  # E1: el 1 % del monto por mercado.
POWER = 0.80
MIN_NONZERO_MARKETS = 30  # Con menos, el informe dice que el IC no es confiable.
SECONDS_PER_DAY = 86_400

_NORMAL = NormalDist()


@dataclass(frozen=True)
class Comparison:
    """Resultado de comparar un agente con un baseline."""

    mean: float
    lower: float
    upper: float
    confidence: float
    classification: str
    nonzero_markets: int
    nonzero_days: int
    trade_share: float
    mean_when_trading: float
    reliable: bool


def market_days(trajectories: pd.DataFrame) -> np.ndarray:
    """Día UTC en que empieza cada mercado, en el orden de las trayectorias."""
    first = trajectories.groupby("market_id", sort=False)["ts"].first()
    return first.to_numpy(dtype=np.int64) // SECONDS_PER_DAY


def returns_by_seed(
    frames: Sequence[pd.DataFrame], initial_cash: float, stake: float
) -> np.ndarray:
    """Matriz `R_i` de mercados × semillas; exige los mismos mercados y en el mismo orden."""
    columns = [episode_results(frame, initial_cash, stake)["return_on_stake"] for frame in frames]
    if any(not column.index.equals(columns[0].index) for column in columns):
        raise ValueError("Las semillas no cubren los mismos mercados en el mismo orden")
    return np.column_stack([column.to_numpy(dtype=float) for column in columns])


def stationary_indices(
    n: int, mean_block: float, replicas: int, rng: np.random.Generator
) -> np.ndarray:
    """Índices del bootstrap estacionario: bloques circulares de largo geométrico."""
    positions = np.arange(n)
    new_block = rng.random((replicas, n)) < 1.0 / mean_block
    new_block[:, 0] = True
    block_start = np.maximum.accumulate(np.where(new_block, positions, 0), axis=1)
    starts = rng.integers(n, size=(replicas, n))
    origin = np.take_along_axis(starts, block_start, axis=1)
    return (origin + positions - block_start) % n


def politis_white_block(series: np.ndarray) -> float:
    """Largo medio de bloque óptimo del bootstrap estacionario (Politis y White, con Patton).

    Da lo mismo que `arch.bootstrap.optimal_block_length`, la referencia del protocolo, salvo que
    nunca baja de 1, porque es el largo medio de un bloque.
    """
    x = np.asarray(series, dtype=float)
    n = len(x)
    x = x - x.mean()
    if float(x @ x) == 0:
        return 1.0
    k_n = max(5, int(math.log10(max(n, 1))))
    m_max = math.ceil(math.sqrt(n)) + k_n
    if n <= m_max + 1:  # Sin días suficientes para estimar las autocorrelaciones.
        return 1.0
    b_max = math.ceil(min(3 * math.sqrt(n), n / 3))
    threshold = 2 * math.sqrt(math.log10(n) / n)
    autocov = np.zeros(m_max + 1)
    correlation = np.zeros(m_max + 1)
    m_hat = m_max
    found = False
    for lag in range(m_max + 1):
        cross = float(x[lag:] @ x[: n - lag])
        autocov[lag] = cross / n
        tail, head = x[lag + 1 :], x[: -(lag + 1)]
        correlation[lag] = abs(cross) / math.sqrt(float(tail @ tail) * float(head @ head))
        if not found and lag >= k_n and (correlation[lag - k_n : lag] < threshold).all():
            m_hat, found = lag - k_n, True
    bandwidth = min(2 * max(m_hat, 1), m_max) if found else m_max

    long_run = autocov[0]
    weighted = 0.0
    for k in range(1, bandwidth + 1):
        ratio = k / bandwidth
        weight = 1.0 if ratio <= 0.5 else 2 * (1 - ratio)
        long_run += 2 * weight * autocov[k]
        weighted += 2 * weight * k * autocov[k]
    if long_run <= 0:
        return 1.0
    block = (2 * weighted**2 / (2 * long_run**2)) ** (1 / 3) * n ** (1 / 3)
    return float(min(max(block, 1.0), b_max))


def _daily(differences: np.ndarray, days: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Suma de `D` por día y semilla, y mercados por día."""
    _, day_index, counts = np.unique(days, return_inverse=True, return_counts=True)
    totals = np.zeros((len(counts), differences.shape[1]))
    np.add.at(totals, day_index, differences)
    return totals, counts


def daily_means(differences: np.ndarray, days: np.ndarray) -> np.ndarray:
    """Media diaria de `D`, promediando las semillas; es la serie que usa Politis y White."""
    totals, counts = _daily(differences, days)
    return totals.mean(axis=1) / counts


def _bca_limits(
    replicas: np.ndarray, estimate: float, jackknife: np.ndarray, confidence: float
) -> tuple[float, float]:
    """Límites BCa; si todas las réplicas son iguales, el intervalo es ese punto."""
    if np.ptp(replicas) == 0:
        return float(replicas[0]), float(replicas[0])
    size = len(replicas)
    below = float((replicas < estimate).mean() + 0.5 * (replicas == estimate).mean())
    bias = _NORMAL.inv_cdf(min(max(below, 1 / (size + 1)), size / (size + 1)))
    distance = jackknife.mean() - jackknife
    scale = float((distance**2).sum())
    acceleration = float((distance**3).sum()) / (6 * scale**1.5) if scale > 0 else 0.0

    tail = (1 - confidence) / 2
    limits = []
    for probability in (tail, 1 - tail):
        z = bias + _NORMAL.inv_cdf(probability)
        limits.append(_NORMAL.cdf(bias + z / (1 - acceleration * z)))
    lower, upper = np.quantile(replicas, limits)
    return float(lower), float(upper)


def bootstrap_ci(
    differences: np.ndarray,
    days: np.ndarray,
    *,
    mean_block: float,
    confidence: float = FAMILY_CONFIDENCE,
    replicas: int = REPLICAS,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Media e IC BCa de `D` (mercados × semillas) con el bootstrap de dos niveles.

    La media de cada réplica es la suma de `D_i` entre el número de mercados, por si hay días
    incompletos. La aceleración de BCa sale de un jackknife por día, promediando las semillas.

    Si cada semilla tuviera ruido independiente en cada mercado, ese ruido se contaría dos veces
    (por día y por semilla) y el intervalo saldría más ancho de lo necesario: es conservador.
    """
    rng = np.random.default_rng(seed)
    totals, counts = _daily(differences, days)
    n_days, n_seeds = totals.shape
    day_draws = stationary_indices(n_days, mean_block, replicas, rng)
    seed_draws = rng.integers(n_seeds, size=(replicas, n_seeds))
    by_seed = totals[day_draws].sum(axis=1)
    chosen = np.take_along_axis(by_seed, seed_draws, axis=1).mean(axis=1)
    samples = chosen / counts[day_draws].sum(axis=1)

    estimate = float(totals.mean(axis=1).sum() / counts.sum())
    mean_totals = totals.mean(axis=1)
    jackknife = (mean_totals.sum() - mean_totals) / np.maximum(counts.sum() - counts, 1)
    lower, upper = _bca_limits(samples, estimate, jackknife, confidence)
    return estimate, lower, upper


def classify(mean: float, lower: float, upper: float, delta_min: float = DELTA_MIN) -> str:
    """Clasificación de la sección 6, evaluando sus condiciones en el orden de la tabla."""
    if lower > 0:
        return "supera" if mean >= delta_min else "mejor, pero no relevante"
    if -delta_min < lower and upper < delta_min:
        return "equivalente"
    if upper < 0:
        return "inferior"
    return "inconcluso"


def compare(
    agent: np.ndarray,
    baseline: np.ndarray,
    days: np.ndarray,
    *,
    mean_block: float,
    confidence: float = FAMILY_CONFIDENCE,
    delta_min: float = DELTA_MIN,
    replicas: int = REPLICAS,
    seed: int = 0,
) -> Comparison:
    """Compara `agent` (mercados × semillas) con `baseline` (un retorno por mercado)."""
    differences = agent - baseline[:, np.newaxis]
    mean, lower, upper = bootstrap_ci(
        differences,
        days,
        mean_block=mean_block,
        confidence=confidence,
        replicas=replicas,
        seed=seed,
    )
    nonzero = differences != 0
    active = nonzero.any(axis=1)
    return Comparison(
        mean=mean,
        lower=lower,
        upper=upper,
        confidence=confidence,
        classification=classify(mean, lower, upper, delta_min),
        nonzero_markets=int(active.sum()),
        nonzero_days=len(np.unique(days[active])),
        trade_share=float(nonzero.mean()),
        mean_when_trading=float(differences[nonzero].mean()) if nonzero.any() else 0.0,
        reliable=bool(active.sum() >= MIN_NONZERO_MARKETS),
    )


def minimum_detectable_effect(
    differences: np.ndarray, days: np.ndarray, *, test_days: int, max_lag: int = 3
) -> float:
    """Diferencia mínima detectable en test, estimada sobre val (sección 7, Newey-West)."""
    daily = daily_means(differences, days)
    centered = daily - daily.mean()
    n = len(centered)
    long_run = float(centered @ centered) / n
    for lag in range(1, max_lag + 1):
        weight = 1 - lag / (max_lag + 1)
        long_run += 2 * weight * float(centered[lag:] @ centered[:-lag]) / n
    n_seeds = differences.shape[1]
    between_seeds = float(differences.mean(axis=0).var(ddof=1)) if n_seeds > 1 else 0.0
    error = math.sqrt(max(long_run, 0.0) / test_days + between_seeds / n_seeds)
    alpha = (1 - FAMILY_CONFIDENCE) / 2
    return (_NORMAL.inv_cdf(1 - alpha) + _NORMAL.inv_cdf(POWER)) * error
