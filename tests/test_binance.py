import gzip
import json
from datetime import UTC, date, datetime

import httpx

from polym4v.data.binance import capture_klines, kline_blocks, spot_range
from polym4v.data.capture import RawStore

DAY = int(datetime(2026, 10, 30, tzinfo=UTC).timestamp())


def kline(open_ms):
    return [open_ms, "1", "2", "0.5", "1.5", "10", open_ms + 59_999, "15", 3, "5", "7", "0"]


def binance(handler=None):
    requests = []

    def record(request):
        requests.append(request)
        if handler is not None:
            return handler(request)
        start = int(request.url.params["startTime"])
        return httpx.Response(200, json=[kline(start)])

    return httpx.Client(transport=httpx.MockTransport(record)), requests


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def test_blocks_fit_in_one_request_and_cover_whole_days():
    minutes = list(kline_blocks("1m", date(2026, 10, 30), date(2026, 10, 31)))
    hours = list(kline_blocks("1h", date(2026, 10, 30), date(2026, 11, 1)))

    assert minutes == [
        ("2026-10-30T00", DAY, DAY + 12 * 3600),
        ("2026-10-30T12", DAY + 12 * 3600, DAY + 24 * 3600),
    ]
    assert [label for label, _, _ in hours] == ["2026-10-30T00", "2026-10-31T00"]
    assert all((b1 - b0) // 60 <= 1000 for _, b0, b1 in minutes)


def test_spot_range_covers_new_york_windows():
    assert spot_range(date(2025, 5, 28), date(2026, 10, 30)) == (
        date(2025, 5, 27),
        date(2026, 11, 1),
    )


def test_capture_stores_raw_klines_with_request(tmp_path):
    http, requests = binance()
    store = RawStore(tmp_path)

    summary = capture_klines(
        "BTCUSDT",
        "1m",
        date(2026, 10, 30),
        date(2026, 10, 31),
        store,
        http=http,
        sleep=lambda s: None,
        now=DAY + 10 * 86400,
    )

    assert summary["downloaded"] == 2 and not summary["errors"]
    saved = read(store.kline_path("BTCUSDT", "1m", "2026-10-30T12"))
    assert saved["request"]["params"] == {
        "symbol": "BTCUSDT",
        "interval": "1m",
        "startTime": (DAY + 12 * 3600) * 1000,
        "endTime": (DAY + 24 * 3600) * 1000 - 1,
        "limit": 1000,
    }
    assert saved["body"] == [kline((DAY + 12 * 3600) * 1000)]
    assert len(requests) == 2


def test_second_run_makes_no_network_calls(tmp_path):
    http, requests = binance()
    store = RawStore(tmp_path)
    args = ("BTCUSDT", "1h", date(2026, 10, 30), date(2026, 10, 31), store)
    capture_klines(*args, http=http, sleep=lambda s: None, now=DAY + 86400)
    first = len(requests)

    summary = capture_klines(*args, http=http, sleep=lambda s: None, now=DAY + 86400)

    assert len(requests) == first == 1
    assert summary["cached"] == 1 and summary["downloaded"] == 0


def test_blocks_still_open_are_not_saved(tmp_path):
    http, requests = binance()
    store = RawStore(tmp_path)

    summary = capture_klines(
        "BTCUSDT",
        "1m",
        date(2026, 10, 30),
        date(2026, 10, 31),
        store,
        http=http,
        sleep=lambda s: None,
        now=DAY + 18 * 3600,
    )

    assert summary["downloaded"] == 1 and summary["pending"] == 1
    assert not store.kline_path("BTCUSDT", "1m", "2026-10-30T12").exists()


def test_rejected_requests_are_reported_and_not_cached(tmp_path):
    http, requests = binance(lambda request: httpx.Response(400, json={"msg": "Invalid symbol."}))
    store = RawStore(tmp_path)

    summary = capture_klines(
        "XXXUSDT",
        "1h",
        date(2026, 10, 30),
        date(2026, 10, 31),
        store,
        http=http,
        sleep=lambda s: None,
        now=DAY + 86400,
    )

    assert summary["errors"][0]["status"] == 400
    assert len(requests) == 1
    assert not store.files()


def test_cli_capture_spot_uses_config(tmp_path, monkeypatch, capsys):
    from polym4v import cli

    text = (
        "dataset_id: prueba\nseries_id: 10114\nasset: ETH\n"
        "date_from: 2025-05-28\ndate_to: 2025-05-29\n"
        "step_seconds: 60\nwindow_minutes: 60\ncontext_minutes: 60\n"
        "quality: {min_points_in_window: 45, max_gap_seconds: 600}\n"
        "split: {train: 0.7, val: 0.15, test: 0.15}\n"
        "test_exclusions: configs/test_exclusions.json\n"
    )
    config = tmp_path / "data.yaml"
    config.write_text(text, encoding="utf-8")
    http, requests = binance()
    monkeypatch.setattr(cli.httpx, "Client", lambda timeout: http)
    monkeypatch.setattr("polym4v.data.binance.time.sleep", lambda s: None)

    args = ["capture-spot", "--config", str(config), "--out", str(tmp_path / "raw"), "--pause", "0"]
    assert cli.main(args) == 0

    result = json.loads(capsys.readouterr().out)
    # Del 27/05 al 31/05 (sin incluirlo): 4 días, 8 bloques de 1m y 4 de 1h.
    assert [k["downloaded"] for k in result["klines"]] == [8, 4]
    assert {r.url.params["symbol"] for r in requests} == {"ETHUSDT"}
    assert result["files"] == 12
