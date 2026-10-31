import json
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from polym4v.data.build_dataset import build_dataset, window_quality
from polym4v.data.capture import RawStore
from polym4v.data.splits import SplitExclusions
from polym4v.utils.config import DataConfig

ET = ZoneInfo("America/New_York")
W0 = int(datetime(2026, 10, 30, tzinfo=UTC).timestamp())
NONE = SplitExclusions(descripcion="", slugs=frozenset(), rangos_end_date_utc=())
CONFIG = DataConfig.model_validate(
    {
        "dataset_id": "prueba",
        "series_id": 10114,
        "asset": "BTC",
        "date_from": "2026-10-29",
        "date_to": "2026-10-31",
        "step_seconds": 60,
        "window_minutes": 60,
        "context_minutes": 60,
        "quality": {"min_points_in_window": 45, "max_gap_seconds": 600},
        "split": {"train": 0.7, "val": 0.15, "test": 0.15},
        "test_exclusions": "no-se-usa.json",
    }
)


def title(w0):
    et = datetime.fromtimestamp(w0, ET)
    return f"Bitcoin Up or Down - {et:%B} {et.day}, {et.hour % 12 or 12}{et:%p} ET"


def iso(ts):
    return datetime.fromtimestamp(ts, UTC).isoformat().replace("+00:00", "Z")


def event(i, w0, outcome):
    return {
        "id": str(100 + i),
        "slug": f"btc-{i}",
        "title": title(w0),
        "markets": [
            {
                "condition_id": f"0x{i:02d}",
                "slug": f"btc-{i}",
                "question": title(w0),
                "state": {"end_date": iso(w0 + 3600)},
                "outcomes": {
                    "yes": {"token_id": f"{i}1", "price": str(outcome)},
                    "no": {"token_id": f"{i}2", "price": str(1 - outcome)},
                },
                "trading": {
                    "fees_enabled": True,
                    "fee_schedule": {"rate": "0.07", "exponent": 1},
                },
            }
        ],
    }


def kline(ts, open_, close):
    return [ts * 1000, str(open_), str(max(open_, close)), str(min(open_, close)), str(close), "1"]


def write_raw(root, n=10, broken=None):
    """Mercados horarios consecutivos desde W0. `broken` daña algunos para probar los filtros."""
    broken = broken or {}
    store = RawStore(root)
    hourly, minutes = [], []
    for i in range(n):
        w0 = W0 + 3600 * i
        outcome = i % 2
        store.write(store.event_path(10114, str(100 + i)), event(i, w0, outcome))
        history = [{"t": t, "p": 0.5} for t in range(w0 - 6 * 3600, w0 + 2 * 3600, 60)]
        if broken.get(i) == "pocos puntos":
            history = [h for h in history if not w0 + 600 <= h["t"] < w0 + 3600]
        if broken.get(i) == "precio fuera de rango":
            history[400]["p"] = 5000.49
        for side in (1, 2):
            if broken.get(i) != "sin historial":
                store.write(store.price_path(f"{i}{side}"), {"body": {"history": history}})
        close = 101 if outcome else 99
        if broken.get(i) == "no coincide":
            close = 99 if outcome else 101
        hourly.append(kline(w0, 100, close))
    for t in range(W0 - 2 * 3600, W0 + 3600 * (n + 1), 60):
        minutes.append(kline(t, 100, 100.5))
    store.write(store.kline_path("BTCUSDT", "1h", "todo"), {"body": hourly})
    store.write(store.kline_path("BTCUSDT", "1m", "todo"), {"body": minutes})
    return store


def test_window_quality_counts_points_and_longest_silence():
    assert window_quality([0, 60, 120, 900], 0, 3600) == (4, 2700)
    assert window_quality([-60], 0, 3600) == (0, 3600)


def test_builds_validated_tables_and_manifest(tmp_path):
    raw = write_raw(tmp_path / "raw")

    manifest = build_dataset(CONFIG, raw, NONE, tmp_path / "out")

    markets = pd.read_parquet(tmp_path / "out" / "markets.parquet")
    assert len(markets) == 10 and list(markets["w0"]) == [W0 + 3600 * i for i in range(10)]
    assert manifest["markets_per_split"] == {"train": 7, "val": 1, "test": 2}
    assert markets.loc[1, "outcome"] == 1 and markets.loc[1, "spot_close"] == 101
    assert markets.loc[0, "fee_rate"] == 0.07 and markets.loc[0, "n_points_window"] == 60
    saved = json.loads((tmp_path / "out" / "manifest.json").read_text())
    assert saved["files"] == manifest["files"] and saved["feed_latency_s"] == 0


def test_prices_keep_context_and_drop_post_resolution(tmp_path):
    build_dataset(CONFIG, write_raw(tmp_path / "raw", n=1), NONE, tmp_path / "out")

    prices = pd.read_parquet(tmp_path / "out" / "prices_raw.parquet")
    assert prices["ts_event"].min() == W0 - 3600
    assert prices["ts_event"].max() == W0 + 3600 - 60
    assert (prices["ts_available"] == prices["ts_event"]).all()
    assert set(prices["side"]) == {"yes", "no"}


def test_feed_latency_shifts_availability(tmp_path):
    build_dataset(CONFIG, write_raw(tmp_path / "raw", n=1), NONE, tmp_path / "out", latency_s=15)

    prices = pd.read_parquet(tmp_path / "out" / "prices_raw.parquet")
    assert (prices["ts_available"] == prices["ts_event"] + 15).all()


def test_spot_is_known_one_minute_after_it_opens(tmp_path):
    build_dataset(CONFIG, write_raw(tmp_path / "raw", n=2), NONE, tmp_path / "out")

    spot = pd.read_parquet(tmp_path / "out" / "spot_1m.parquet")
    assert spot["ts_event"].min() == W0 - 3600
    assert spot["ts_event"].max() == W0 + 2 * 3600 - 60
    assert (spot["ts_available"] == spot["ts_event"] + 60).all()


def test_bad_markets_are_discarded_with_their_reason(tmp_path):
    broken = {
        2: "pocos puntos",
        3: "precio fuera de rango",
        4: "sin historial",
        5: "no coincide",
    }
    manifest = build_dataset(
        CONFIG, write_raw(tmp_path / "raw", broken=broken), NONE, tmp_path / "out"
    )

    assert manifest["discarded_by_reason"] == {
        "pocos puntos en la ventana": 1,
        "precio fuera de rango": 1,
        "sin historial": 1,
        "el resultado no coincide con Binance": 1,
    }
    markets = pd.read_parquet(tmp_path / "out" / "markets.parquet")
    assert set(markets["slug"]) == {f"btc-{i}" for i in (0, 1, 6, 7, 8, 9)}
    prices = pd.read_parquet(tmp_path / "out" / "prices_raw.parquet")
    assert set(prices["market_id"]) == set(markets["market_id"])


def test_test_exclusions_are_recorded(tmp_path):
    exclusions = NONE.model_copy(update={"slugs": frozenset({"btc-9"})})

    manifest = build_dataset(CONFIG, write_raw(tmp_path / "raw"), exclusions, tmp_path / "out")

    assert manifest["markets_per_split"] == {"train": 7, "val": 1, "test": 1}
    assert manifest["discarded"] == [
        {"event_id": "109", "slug": "btc-9", "motivo": "excluido de test (S11)"}
    ]


def test_building_twice_gives_the_same_files(tmp_path):
    raw = write_raw(tmp_path / "raw")

    first = build_dataset(CONFIG, raw, NONE, tmp_path / "a")
    second = build_dataset(CONFIG, raw, NONE, tmp_path / "b")

    assert first["files"] == second["files"]


def test_markets_outside_the_dates_are_skipped(tmp_path):
    config = CONFIG.model_copy(update={"date_from": CONFIG.date_from.replace(day=31)})
    with pytest.raises(ValueError, match="Ningún mercado"):
        build_dataset(config, write_raw(tmp_path / "raw"), NONE, tmp_path / "out")


def test_cli_build_dataset(tmp_path, capsys):
    from polym4v import cli

    write_raw(tmp_path / "raw")
    exclusions = tmp_path / "exclusiones.json"
    exclusions.write_text('{"descripcion": "", "slugs": [], "rangos_end_date_utc": []}')
    config = tmp_path / "data.yaml"
    config.write_text(
        json.dumps(CONFIG.model_dump(mode="json") | {"test_exclusions": str(exclusions)})
    )

    args = ["build-dataset", "--config", str(config), "--raw", str(tmp_path / "raw")]
    assert cli.main([*args, "--out", str(tmp_path / "out")]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["markets_per_split"] == {"train": 7, "val": 1, "test": 2}
    assert set(result["files"]) == {"markets.parquet", "prices_raw.parquet", "spot_1m.parquet"}
