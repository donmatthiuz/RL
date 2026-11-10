import json

import pandas as pd
import pytest

from polym4v import cli
from polym4v.agents.baselines import FavoritePolicy, NoTradePolicy, RandomPolicy
from polym4v.env.market_env import PolymarketEnv
from polym4v.env.synthetic import synthetic_data
from polym4v.evaluation.backtest import run_backtest
from polym4v.evaluation.metrics import summarize
from polym4v.evaluation.report import build_report, parse_name, to_markdown
from polym4v.utils.config import CostConfig, EnvConfig, RewardConfig

COSTS = CostConfig(
    half_spread=0.01, fee_rate=0.07, fee_exponent=1, fee_decimals=5, min_fee=0.00001, tick=0.001
)
ENV = EnvConfig(
    initial_cash=1000.0,
    stake_fraction=0.02,
    latency_s=2,
    tolerance_s=60,
    no_open_last_minutes=2,
    costs=COSTS,
)
PNG = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(scope="module")
def frames():
    env = PolymarketEnv(synthetic_data(6, seed=3), ENV, RewardConfig(name="pnl"))
    return {
        policy.name: run_backtest(policy, env)
        for policy in (NoTradePolicy(), FavoritePolicy(), RandomPolicy(seed=1))
    }


@pytest.fixture
def folder(tmp_path, frames):
    """Trayectorias como las deja `backtest`: tres de train, una estricta y una de val."""
    out = tmp_path / "trajectories"
    out.mkdir()
    for name, frame in frames.items():
        frame.to_parquet(out / f"{name}_train.parquet")
    frames["favorite"].to_parquet(out / "favorite_train_estricto.parquet")
    frames["random"].to_parquet(out / "random_val.parquet")
    return out


def write_run(models, run_id, split, values):
    folder = models / "ppo" / run_id
    folder.mkdir(parents=True)
    checkpoints = [
        {"timesteps": 100 * (i + 1), "path": f"step_{100 * (i + 1)}.zip", "mean_return": v}
        for i, v in enumerate(values)
    ]
    best = max(checkpoints, key=lambda c: c["mean_return"])
    metrics = {"run_id": run_id, "eval_split": split, "best": best, "checkpoints": checkpoints}
    (folder / "metrics.json").write_text(json.dumps(metrics))


@pytest.mark.parametrize(
    ("name", "split", "expected"),
    [
        ("no_trade_train.parquet", "train", ("no_trade", False)),
        (
            "20261101-000000_ppo_pnl_s0_val_estricto.parquet",
            "val",
            ("20261101-000000_ppo_pnl_s0", True),
        ),
        ("no_trade_val.parquet", "train", None),
        ("_train.parquet", "train", None),
    ],
)
def test_file_names_give_label_and_mode(tmp_path, name, split, expected):
    assert parse_name(tmp_path / name, split) == expected


def test_report_has_one_row_per_file_of_the_split(tmp_path, folder, frames):
    out = tmp_path / "reports" / "train"
    summary = build_report("train", folder, tmp_path / "models", out, 1000.0, 20.0)

    assert summary["policies"] == ["favorite", "favorite (estricto)", "no_trade", "random"]
    assert summary["markets"] == 6 and summary["runs"] == []
    assert summary["files"] == ["summary.csv", "summary.md", "capital.png", "returns.png"]
    for name in summary["files"]:
        assert (out / name).exists()
    for name in ("capital.png", "returns.png"):
        assert (out / name).read_bytes().startswith(PNG)

    table = pd.read_csv(out / "summary.csv")
    assert len(table) == 4
    assert table["mean_return"].is_monotonic_decreasing
    no_trade = table[table["label"] == "no_trade"].iloc[0]
    expected = summarize(frames["no_trade"], 1000.0, 20.0)
    assert no_trade["mean_return"] == 0.0 and no_trade["markets"] == expected["markets"]
    random = table[table["label"] == "random"].iloc[0]
    assert random["mean_return"] == pytest.approx(
        summarize(frames["random"], 1000.0, 20.0)["mean_return"]
    )


def test_markdown_table_has_a_header_and_one_line_per_row(tmp_path, folder):
    out = tmp_path / "train"
    build_report("train", folder, tmp_path / "models", out, 1000.0, 20.0)
    text = (out / "summary.md").read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.startswith("|")]
    assert lines[0].startswith("| Política | Estricto | Mercados | Retorno medio |")
    assert len(lines) == 2 + 4
    # Una métrica sin definir (el Sharpe de NoTrade no tiene varianza) se muestra como raya.
    assert "| no_trade | no | 6 | 0.0000 | 0.0000 | — |" in text


def test_to_markdown_formats_booleans_and_missing_values():
    table = pd.DataFrame([{"label": "a", "strict": True, "markets": 2, "sharpe": float("nan")}])
    text = to_markdown(table, "val")
    assert text.startswith("## Comparación en val")
    assert "| a | sí | 2 | — |" in text


def test_learning_curves_only_use_runs_evaluated_in_the_split(tmp_path, folder):
    models = tmp_path / "models"
    write_run(models, "r1_ppo_pnl_s0", "train", [-0.2, 0.1, 0.05])
    write_run(models, "r2_ppo_pnl_s1", "train", [-0.1, -0.05, 0.0])
    write_run(models, "r3_ppo_pnl_s2", "val", [0.3, 0.4, 0.5])
    out = tmp_path / "train"
    summary = build_report("train", folder, models, out, 1000.0, 20.0)

    assert summary["runs"] == ["r1_ppo_pnl_s0", "r2_ppo_pnl_s1"]
    assert (out / "learning.png").read_bytes().startswith(PNG)


def test_policies_must_cover_the_same_markets(tmp_path, folder, frames):
    first = frames["no_trade"]["market_id"].iloc[0]
    frame = frames["random"]
    frame[frame["market_id"] != first].to_parquet(folder / "random_train.parquet")
    with pytest.raises(ValueError, match="mismos mercados"):
        build_report("train", folder, tmp_path / "models", tmp_path / "out", 1000.0, 20.0)


def test_old_trajectories_without_every_info_key_are_rejected(tmp_path, folder, frames):
    frames["random"].drop(columns="exec_verified").to_parquet(folder / "random_train.parquet")
    with pytest.raises(ValueError, match="random_train.parquet no tiene exec_verified"):
        build_report("train", folder, tmp_path / "models", tmp_path / "out", 1000.0, 20.0)


def test_report_without_trajectories_fails(tmp_path, folder):
    with pytest.raises(FileNotFoundError, match="backtest o evaluate"):
        build_report("val", folder / "vacia", tmp_path / "models", tmp_path / "out", 1000.0, 20.0)


def test_cli_report_writes_the_split_and_refuses_test(tmp_path, folder, capsys):
    out = tmp_path / "reports" / "train"
    args = ["report", "--split", "train", "--trajectories", str(folder)]
    args += ["--models", str(tmp_path / "models"), "--out", str(out)]

    assert cli.main(args) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["markets"] == 6 and summary["out"] == str(out)
    assert (out / "summary.md").exists()

    assert cli.main(["report", "--split", "test", "--trajectories", str(folder)]) == 1
    assert "una sola vez" in capsys.readouterr().err

    assert cli.main(["report", "--split", "val", "--trajectories", str(tmp_path / "nada")]) == 1
    assert "No hay trayectorias de val" in capsys.readouterr().err
