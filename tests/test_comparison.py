"""Tests de la comparación de agentes con el baseline de referencia (EVA-04)."""

import numpy as np
import pandas as pd
import pytest

from polym4v.evaluation import comparison
from polym4v.evaluation.backtest import STEP_KEYS
from polym4v.evaluation.report import build_report
from polym4v.evaluation.stats import politis_white_block

CASH, STAKE = 1000.0, 20.0
N_DAYS, PER_DAY = 40, 4
DAY = 86_400


def frame(returns: np.ndarray, policy: str = "p") -> pd.DataFrame:
    """Trayectoria mínima: un paso por mercado, con el retorno sobre el monto pedido."""
    n = len(returns)
    return pd.DataFrame(
        {
            "policy": policy,
            "market_id": [f"m{i:04d}" for i in range(n)],
            "ts": [DAY * (i // PER_DAY) for i in range(n)],
            "portfolio_value": CASH + STAKE * returns,
            "fees_paid": 0.0,
            "order_status": "espera",
            "exec_verified": None,
            "done": True,
        }
    )


def noise(mean: float, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).normal(mean, 0.05, N_DAYS * PER_DAY)


ZEROS = np.zeros(N_DAYS * PER_DAY)


def agents(mean: float, group: str = "ppo_pnl", seeds: int = 3) -> dict:
    return {
        (f"20261101-000000_{group}_s{seed}", False): frame(noise(mean, 100 + seed))
        for seed in range(seeds)
    }


def test_agrupa_semillas_por_agente_y_recompensa() -> None:
    frames = {
        **agents(0.1, "ppo_pnl_risk", seeds=2),
        **agents(0.1, "cql_pnl", seeds=1),
        (comparison.NO_TRADE, False): frame(ZEROS),
    }
    groups = comparison.agent_groups(frames, strict=False)
    assert {g: len(s) for g, s in groups.items()} == {"cql_pnl": 1, "ppo_pnl_risk": 2}


def test_semilla_repetida_es_un_error() -> None:
    frames = {
        ("20261101-000000_ppo_pnl_s0", False): frame(ZEROS),
        ("20261102-000000_ppo_pnl_s0", False): frame(ZEROS),
    }
    with pytest.raises(ValueError, match="semilla 0"):
        comparison.agent_groups(frames, strict=False)


def test_notrade_es_la_referencia_si_ninguna_heuristica_le_gana() -> None:
    frames = {
        (comparison.NO_TRADE, False): frame(ZEROS),
        ("favorite", False): frame(noise(-0.05, 1)),
        ("momentum", False): frame(noise(0.0, 2)),
    }
    assert comparison.select_baseline(frames, CASH, STAKE) == comparison.NO_TRADE


def test_heuristica_que_gana_con_ic_positivo_es_la_referencia() -> None:
    frames = {
        (comparison.NO_TRADE, False): frame(ZEROS),
        ("favorite", False): frame(noise(0.02, 1)),
        ("momentum", False): frame(noise(0.05, 2)),
        # Un agente con media mayor no compite por ser baseline.
        ("20261101-000000_ppo_pnl_s0", False): frame(noise(0.5, 3)),
    }
    assert comparison.select_baseline(frames, CASH, STAKE) == "momentum"


def test_parametros_se_fijan_con_la_serie_diaria_de_d() -> None:
    frames = {**agents(0.1), (comparison.NO_TRADE, False): frame(ZEROS)}
    params = comparison.freeze_params(frames, CASH, STAKE)
    assert params is not None
    assert params["baseline"] == comparison.NO_TRADE
    daily = np.column_stack([noise(0.1, 100 + s) for s in range(3)]).mean(axis=1)
    daily = daily.reshape(N_DAYS, PER_DAY).mean(axis=1)
    assert params["mean_block"]["ppo_pnl"] == pytest.approx(politis_white_block(daily))
    assert params["mde"]["ppo_pnl"] > 0


def test_sin_agentes_o_sin_notrade_no_hay_comparacion() -> None:
    assert comparison.freeze_params({("no_trade", False): frame(ZEROS)}, CASH, STAKE) is None
    assert comparison.freeze_params(agents(0.1), CASH, STAKE) is None


def test_clasifica_y_agrega_la_secundaria_contra_notrade() -> None:
    frames = {
        **agents(0.2),
        (comparison.NO_TRADE, False): frame(ZEROS),
        ("momentum", False): frame(noise(0.05, 2)),
    }
    params = comparison.freeze_params(frames, CASH, STAKE)
    assert params is not None and params["baseline"] == "momentum"
    table = comparison.compare_agents(frames, params, CASH, STAKE)
    assert table[["role", "baseline"]].values.tolist() == [
        ["principal", "momentum"],
        ["secundaria", "no_trade"],
    ]
    assert (table["classification"] == "supera").all()
    assert (table["seeds"] == 3).all()


def test_cambio_entre_modos_marca_dependencia_de_liquidez() -> None:
    strict = {(f"20261101-000000_ppo_pnl_s{s}", True): frame(ZEROS) for s in range(3)}
    frames = {**agents(0.2), **strict, (comparison.NO_TRADE, False): frame(ZEROS)}
    params = comparison.freeze_params(frames, CASH, STAKE)
    assert params is not None
    table = comparison.compare_agents(frames, params, CASH, STAKE)
    assert table.set_index("strict")["classification"].to_dict() == {
        False: "supera",
        True: "equivalente",
    }
    assert table["depends_on_liquidity"].all()


def test_mismo_resultado_en_ambos_modos_no_marca_dependencia() -> None:
    strict = {(label, True): data for (label, _), data in agents(0.2).items()}
    frames = {**agents(0.2), **strict, (comparison.NO_TRADE, False): frame(ZEROS)}
    params = comparison.freeze_params(frames, CASH, STAKE)
    assert params is not None
    table = comparison.compare_agents(frames, params, CASH, STAKE)
    assert len(table) == 2
    assert not table["depends_on_liquidity"].any()


def test_agente_que_no_estaba_en_val_es_un_error() -> None:
    frames = {**agents(0.1), (comparison.NO_TRADE, False): frame(ZEROS)}
    params = {"baseline": comparison.NO_TRADE, "mean_block": {}, "mde": {}}
    with pytest.raises(ValueError, match="no estaba en val"):
        comparison.compare_agents(frames, params, CASH, STAKE)


def _params(mde: float) -> dict:
    return {
        "baseline": comparison.NO_TRADE,
        "mean_block": {"ppo_pnl": 1.0},
        "mde": {"ppo_pnl": mde},
    }


def test_avisa_si_la_mde_es_mayor_que_delta_min() -> None:
    frames = {**agents(0.2), (comparison.NO_TRADE, False): frame(ZEROS)}
    table = comparison.compare_agents(frames, _params(0.03), CASH, STAKE)
    assert table["mde"].tolist() == [0.03]
    text = comparison.comparison_markdown(table, "val")
    assert text.count("no puede detectar") == 1
    assert "ppo_pnl: la MDE (0.0300)" in text


def test_no_avisa_si_la_mde_es_menor_que_delta_min() -> None:
    frames = {**agents(0.2), (comparison.NO_TRADE, False): frame(ZEROS)}
    table = comparison.compare_agents(frames, _params(0.005), CASH, STAKE)
    assert "no puede detectar" not in comparison.comparison_markdown(table, "val")


def _write(folder, split: str, frames: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for (label, strict), data in frames.items():
        mode = "_estricto" if strict else ""
        full = data.copy()
        for key in STEP_KEYS:
            if key not in full.columns:
                full[key] = 0
        full.to_parquet(folder / f"{label}_{split}{mode}.parquet")


def test_el_reporte_de_test_exige_y_reutiliza_lo_fijado_en_val(tmp_path) -> None:
    frames = {**agents(0.2), (comparison.NO_TRADE, False): frame(ZEROS)}
    reports = tmp_path / "reports"
    trajectories = tmp_path / "trajectories"
    _write(trajectories, "val", frames)
    _write(trajectories, "test", frames)

    with pytest.raises(FileNotFoundError, match="reporte de val"):
        build_report("test", trajectories, tmp_path, reports / "test", CASH, STAKE)

    val = build_report("val", trajectories, tmp_path, reports / "val", CASH, STAKE)
    assert {"comparison.csv", "comparison.md"} <= set(val["files"])
    frozen = (reports / "val" / comparison.PARAMS_FILE).read_text(encoding="utf-8")

    test = build_report("test", trajectories, tmp_path, reports / "test", CASH, STAKE)
    assert {"comparison.csv", "comparison.md"} <= set(test["files"])
    assert (reports / "val" / comparison.PARAMS_FILE).read_text(encoding="utf-8") == frozen
    assert not (reports / "test" / comparison.PARAMS_FILE).exists()
    table = pd.read_csv(reports / "test" / "comparison.csv")
    assert table["classification"].tolist() == ["supera"]
    assert "Prueba del protocolo en test" in (reports / "test" / "comparison.md").read_text(
        encoding="utf-8"
    )
