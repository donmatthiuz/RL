import json

from polym4v.agents.baselines import SEARCH, baselines
from polym4v.env.market_env import PolymarketEnv
from polym4v.env.synthetic import synthetic_data
from polym4v.evaluation.tuning import grid, tune, write_tuning
from polym4v.utils.config import SimulatorConfig, load_config

SIM = load_config("configs/env.yaml", SimulatorConfig)


def test_la_grilla_es_pequena_y_ata_el_stop_loss():
    assert sum(len(grid(name)) for name in SEARCH) == 21
    assert all(p["stop_loss"] == p["take_profit"] for p in grid("momentum"))


def test_los_parametros_llegan_al_baseline():
    policy = baselines(SIM.env.costs, params={"favorite": {"entry_k": 45}})["favorite"]()
    assert policy.entry_k == 45
    assert baselines(SIM.env.costs)["favorite"]().entry_k == 30


def test_elige_el_mayor_retorno_de_cada_heuristica(tmp_path):
    env = PolymarketEnv(synthetic_data(4, seed=3), SIM.env, SIM.reward)
    table, chosen = tune(env)
    assert len(table) == 21 and set(chosen) == set(SEARCH)
    for name, params in chosen.items():
        rows = table[table["policy"] == name]
        best = rows.loc[rows["mean_return"].idxmax(), "params"]
        assert json.loads(best) == params
    files = write_tuning(table, chosen, tmp_path)
    assert json.loads((tmp_path / files[2]).read_text()) == chosen
    assert "(elegido)" in (tmp_path / "baselines_search.md").read_text(encoding="utf-8")
