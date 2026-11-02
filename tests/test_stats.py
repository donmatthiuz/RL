"""Tests de la prueba estadística del protocolo (EVA-04)."""

import numpy as np
import pandas as pd
import pytest

from polym4v.evaluation import stats


def _days(n_days: int, per_day: int = 24) -> np.ndarray:
    return np.repeat(np.arange(n_days), per_day)


def test_constantes_del_protocolo() -> None:
    assert stats.FAMILY_CONFIDENCE == pytest.approx(0.9875)
    assert stats.DELTA_MIN == 0.01


def test_indices_estacionarios_con_bloque_uno_y_bloque_largo() -> None:
    rng = np.random.default_rng(0)
    indices = stats.stationary_indices(50, 1.0, 200, rng)
    assert indices.shape == (200, 50)
    assert indices.min() >= 0 and indices.max() < 50
    long_blocks = stats.stationary_indices(50, 1e9, 20, rng)
    assert ((np.diff(long_blocks, axis=1) % 50) == 1).all()


def test_largo_medio_de_bloque_del_estacionario() -> None:
    rng = np.random.default_rng(1)
    indices = stats.stationary_indices(1000, 7.0, 200, rng)
    starts = (np.diff(indices, axis=1) % 1000) != 1
    assert 1 / starts.mean() == pytest.approx(7.0, rel=0.05)


def test_bloque_de_politis_white_crece_con_la_dependencia() -> None:
    rng = np.random.default_rng(2)
    noise = rng.normal(size=2000)
    ar = np.zeros(2000)
    for t in range(1, 2000):
        ar[t] = 0.8 * ar[t - 1] + noise[t]
    assert stats.politis_white_block(ar) > 5 * stats.politis_white_block(noise)
    assert stats.politis_white_block(np.zeros(100)) == 1.0


@pytest.mark.parametrize(
    ("seed", "n", "phi", "expected"),
    [
        (0, 73, 0.0, 1.716308),
        (1, 73, 0.3, 1.895338),
        (2, 73, 0.6, 2.61648),
        (3, 500, 0.5, 10.761686),
        (4, 2000, 0.8, 28.895312),
        (5, 73, 0.8, 10.233281),
    ],
)
def test_bloque_coincide_con_arch(seed: int, n: int, phi: float, expected: float) -> None:
    """Valores de referencia de `arch.bootstrap.optimal_block_length`, la que cita el protocolo."""
    noise = np.random.default_rng(seed).normal(size=n)
    series = np.zeros(n)
    for t in range(1, n):
        series[t] = phi * series[t - 1] + noise[t]
    assert stats.politis_white_block(series) == pytest.approx(expected, abs=1e-5)


def test_el_intervalo_contiene_la_media_verdadera() -> None:
    """Criterio de aceptación de EVA-04: cobertura de cerca de 95 % con datos simulados."""
    rng = np.random.default_rng(3)
    true_mean = 0.02
    runs = 300
    hits = 0
    for run in range(runs):
        # Las semillas juegan los mismos mercados: comparten su ruido y difieren en un efecto fijo.
        market = rng.normal(0.0, 1.0, size=(30 * 4, 1))
        data = true_mean + market + rng.normal(0.0, 0.03, size=(1, 5))
        _, lower, upper = stats.bootstrap_ci(
            data, _days(30, 4), mean_block=1.0, confidence=0.95, replicas=1000, seed=run
        )
        hits += lower <= true_mean <= upper
    assert 0.90 <= hits / runs <= 0.99


def test_media_cuenta_mercados_con_dias_incompletos() -> None:
    differences = np.array([[1.0], [1.0], [4.0]])
    mean, _, _ = stats.bootstrap_ci(differences, np.array([0, 0, 1]), mean_block=1.0, replicas=200)
    assert mean == pytest.approx(2.0)


def test_misma_semilla_mismo_intervalo() -> None:
    data = np.random.default_rng(4).normal(size=(240, 5))
    first = stats.bootstrap_ci(data, _days(10), mean_block=2.0, replicas=500, seed=7)
    assert first == stats.bootstrap_ci(data, _days(10), mean_block=2.0, replicas=500, seed=7)


@pytest.mark.parametrize(
    ("mean", "lower", "upper", "expected"),
    [
        (0.03, 0.01, 0.05, "supera"),
        (0.005, 0.002, 0.03, "mejor, pero no relevante"),
        (0.005, 0.002, 0.008, "mejor, pero no relevante"),
        (0.0, -0.005, 0.005, "equivalente"),
        (-0.005, -0.008, -0.002, "peor, pero no relevante"),
        (-0.005, -0.03, -0.002, "peor, pero no relevante"),
        (-0.03, -0.05, -0.01, "inferior"),
        (-0.01, -0.02, -0.001, "inferior"),
        (0.0, -0.05, 0.05, "inconcluso"),
        (0.0, -0.01, 0.005, "inconcluso"),
    ],
)
def test_clasificacion(mean: float, lower: float, upper: float, expected: str) -> None:
    assert stats.classify(mean, lower, upper, 0.01) == expected


def test_no_operar_contra_notrade_es_equivalente() -> None:
    n_markets = 240
    result = stats.compare(
        np.zeros((n_markets, 5)),
        np.zeros(n_markets),
        _days(10),
        mean_block=1.0,
        replicas=200,
    )
    assert (result.mean, result.lower, result.upper) == (0.0, 0.0, 0.0)
    assert result.classification == "equivalente"
    assert result.nonzero_markets == 0
    assert result.nonzero_days == 0
    assert result.trade_share == 0.0
    assert not result.reliable


def test_diferencia_grande_supera_y_se_descompone() -> None:
    rng = np.random.default_rng(5)
    n_markets = 1752
    agent = rng.normal(0.2, 0.1, size=(n_markets, 5))
    agent[::2] = 0.0  # La mitad de los mercados no opera.
    result = stats.compare(agent, np.zeros(n_markets), _days(73), mean_block=2.0, replicas=1000)
    assert result.classification == "supera"
    assert result.reliable
    assert result.nonzero_markets == n_markets // 2
    assert result.trade_share == pytest.approx(0.5)
    assert result.trade_share * result.mean_when_trading == pytest.approx(result.mean)


def test_mde_con_valores_calculados_a_mano() -> None:
    # Dos días con medias +1 y -1 y una semilla: γ0 = 1, γ1 = -0,5; con max_lag = 1,
    # σ²_LR = 1 + 2 × 0,5 × (-0,5) = 0,5, y SE = √(0,5 / 2).
    differences = np.array([[1.0], [-1.0]])
    mde = stats.minimum_detectable_effect(differences, np.array([0, 1]), test_days=2, max_lag=1)
    assert mde == pytest.approx(3.34 * np.sqrt(0.25), abs=0.005)


def test_returns_by_seed_exige_los_mismos_mercados() -> None:
    def frame(markets: list[str]) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "policy": "p",
                "market_id": markets,
                "portfolio_value": 1010.0,
                "fees_paid": 0.0,
                "order_status": "espera",
                "exec_verified": None,
                "done": True,
            }
        )

    matrix = stats.returns_by_seed([frame(["a", "b"]), frame(["a", "b"])], 1000.0, 20.0)
    assert matrix.shape == (2, 2)
    assert matrix[0, 0] == pytest.approx(0.5)
    with pytest.raises(ValueError, match="mismos mercados"):
        stats.returns_by_seed([frame(["a", "b"]), frame(["b", "a"])], 1000.0, 20.0)


def test_market_days_usa_el_primer_paso_de_cada_mercado() -> None:
    frame = pd.DataFrame({"market_id": ["a", "a", "b"], "ts": [86_399, 86_460, 86_400]})
    assert stats.market_days(frame).tolist() == [0, 1]
