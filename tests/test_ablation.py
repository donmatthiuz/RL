import json

import pytest

from polym4v.cli import main
from polym4v.evaluation.ablation import ablation_table, build_ablation, load_runs


def write_run(folder, reward, seed, best, curve, split="val"):
    run_id = f"20261102-0652{seed:02d}_ppo_{reward}_s{seed}"
    path = folder / "ppo" / run_id
    path.mkdir(parents=True)
    checkpoints = [
        {
            "timesteps": 100 * (i + 1),
            "mean_return": value,
            "trades_per_market": 1.0,
            "no_trade_share": 0.5,
        }
        for i, value in enumerate(curve)
    ]
    best_point = {
        "timesteps": 100,
        "mean_return": best,
        "trades_per_market": 2.0,
        "no_trade_share": 0.25,
    }
    metrics = {
        "run_id": run_id,
        "eval_split": split,
        "best": best_point,
        "checkpoints": checkpoints,
    }
    (path / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")


def test_tabla_por_variante_ordenada_y_con_ic(tmp_path):
    for seed, best in enumerate([0.01, 0.03]):
        write_run(tmp_path, "pnl", seed, best, [0.0, best])
    for seed, best in enumerate([-0.02, -0.04]):
        write_run(tmp_path, "pnl_mid", seed, best, [-0.1, best])
    write_run(tmp_path, "terminal", 0, 0.5, [0.5], split="train")  # Otro split: no entra.
    table = ablation_table(load_runs(tmp_path, "val"))
    assert table["variant"].tolist() == ["ppo_pnl", "ppo_pnl_mid"]
    top = table.iloc[0]
    assert top["seeds"] == 2
    assert top["best_mean"] == pytest.approx(0.02)
    # DE = √2 × 0,01; IC = media ± 12,706 × DE / √2.
    assert top["ci_upper"] - top["best_mean"] == pytest.approx(12.706 * 0.01)
    assert top["curve_mean"] == pytest.approx((0.0 + 0.01 + 0.0 + 0.03) / 4)
    assert top["trades_per_market"] == 2.0 and top["no_trade_share"] == 0.25


def test_semilla_repetida_es_un_error(tmp_path):
    write_run(tmp_path, "pnl", 0, 0.01, [0.01])
    other = tmp_path / "otra"
    write_run(other, "pnl", 0, 0.02, [0.02])
    for path in (other / "ppo").iterdir():
        path.rename(tmp_path / "ppo" / (path.name.replace("065200", "065259")))
    with pytest.raises(ValueError, match="semilla 0"):
        load_runs(tmp_path, "val")


def test_comando_escribe_tabla_y_figura(tmp_path, capsys):
    write_run(tmp_path / "models", "terminal", 0, 0.01, [0.0, 0.01])
    out = tmp_path / "reporte"
    assert main(["ablation", "--models", str(tmp_path / "models"), "--out", str(out)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["best"] == "ppo_terminal"
    assert {p.name for p in out.iterdir()} == {"ablation.csv", "ablation.md", "ablation.png"}
    assert "| ppo_terminal | 1 |" in (out / "ablation.md").read_text(encoding="utf-8")


def test_sin_corridas_falla_con_un_mensaje_claro(tmp_path):
    with pytest.raises(FileNotFoundError, match="No hay corridas"):
        build_ablation(tmp_path, "val", tmp_path / "out")
