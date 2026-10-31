import gzip
import hashlib
import json
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

from polym4v.data.capture import RawStore, capture_series, parse_window_start, write_manifest

UTC = UTC


def ts(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=UTC).timestamp())


@pytest.mark.parametrize(
    ("title", "end_date", "expected"),
    [
        # Formato de 2025, con horario de verano (EDT, UTC-4).
        (
            "Bitcoin Up or Down – May 28 (1 AM ET Candle)",
            "2025-05-28T12:00:00",
            "2025-05-28T05:00:00",
        ),
        # Formato de 2026, todavía en EDT.
        ("Bitcoin Up or Down - October 30, 8PM ET", "2026-10-31T01:00:00", "2026-10-31T00:00:00"),
        # Horario estándar (EST, UTC-5).
        ("Bitcoin Up or Down - February 23, 12PM ET", "2026-02-23T18:00:00", "2026-02-23T17:00:00"),
        # La vela cae en el año anterior al de end_date.
        ("Bitcoin Up or Down - December 31, 11PM ET", "2026-01-01T05:00:00", "2026-01-01T04:00:00"),
    ],
)
def test_window_start_from_title(title, end_date, expected):
    end = datetime.fromisoformat(end_date).replace(tzinfo=UTC)
    assert parse_window_start(title, end) == ts(expected)


def test_window_start_unknown_title_is_none():
    end = datetime(2026, 1, 1, tzinfo=UTC)
    assert parse_window_start("Will BTC reach $100k?", end) is None


def make_event(event_id, title, end_date, yes, no):
    market = SimpleNamespace(
        outcomes=SimpleNamespace(
            yes=SimpleNamespace(token_id=yes), no=SimpleNamespace(token_id=no)
        ),
        state=SimpleNamespace(
            end_date=datetime.fromisoformat(end_date).replace(tzinfo=UTC), closed_time=None
        ),
    )
    event = SimpleNamespace(id=event_id, title=title, markets=[market])
    event.model_dump = lambda mode="json": {"id": event_id, "title": title}
    return event


class FakeGamma:
    def __init__(self, events):
        self.events = events
        self.calls = 0

    def list_events(self, **kwargs):
        self.calls += 1
        assert kwargs["series_ids"] == 10114 and kwargs["closed"] is True
        return SimpleNamespace(iter_items=lambda: iter(self.events))


@pytest.fixture
def events():
    return [
        make_event(
            "1", "Bitcoin Up or Down - October 30, 8PM ET", "2026-10-31T01:00:00", "111", "222"
        )
    ]


def clob(handler):
    requests = []

    def record(request):
        requests.append(request)
        return handler(request)

    return httpx.Client(transport=httpx.MockTransport(record)), requests


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def test_capture_stores_raw_responses_with_request(tmp_path, events):
    body = {"history": [{"t": 1793404800, "p": 0.51}]}
    http, requests = clob(lambda request: httpx.Response(200, json=body))
    store = RawStore(tmp_path)

    summary = capture_series(10114, store, gamma=FakeGamma(events), http=http, sleep=lambda s: None)

    assert summary["events"] == 1 and summary["downloaded"] == 2 and not summary["errors"]
    w0 = ts("2026-10-31T00:00:00")
    for token in ("111", "222"):
        saved = read(store.price_path(token))
        assert saved["body"] == body
        assert saved["status"] == 200
        assert saved["request"]["params"] == {
            "market": token,
            "startTs": w0 - 6 * 3600,
            "endTs": w0 + 2 * 3600,
            "fidelity": 1,
        }
    assert {r.url.params["market"] for r in requests} == {"111", "222"}
    assert read(store.event_path(10114, "1"))["title"].endswith("8PM ET")


def test_second_run_makes_no_network_calls(tmp_path, events):
    http, requests = clob(lambda request: httpx.Response(200, json={"history": []}))
    store = RawStore(tmp_path)
    capture_series(10114, store, gamma=FakeGamma(events), http=http, sleep=lambda s: None)
    first = len(requests)

    summary = capture_series(10114, store, gamma=FakeGamma(events), http=http, sleep=lambda s: None)

    assert len(requests) == first
    assert summary["downloaded"] == 0 and summary["cached"] == 2


def test_rate_limit_is_retried(tmp_path, events):
    answers = iter([httpx.Response(429), httpx.Response(200, json={"history": []})] * 2)
    http, requests = clob(lambda request: next(answers))
    waits = []

    summary = capture_series(
        10114, RawStore(tmp_path), gamma=FakeGamma(events), http=http, sleep=waits.append
    )

    assert summary["downloaded"] == 2 and not summary["errors"]
    assert len(requests) == 4 and waits


def test_failures_are_reported_and_not_cached(tmp_path, events):
    http, _ = clob(lambda request: httpx.Response(500, json={"error": "down"}))
    store = RawStore(tmp_path)

    summary = capture_series(10114, store, gamma=FakeGamma(events), http=http, sleep=lambda s: None)

    assert summary["downloaded"] == 0
    assert {e["token_id"] for e in summary["errors"]} == {"111", "222"}
    assert not store.price_path("111").exists()


def test_manifest_lists_every_file_with_its_hash(tmp_path, events):
    http, _ = clob(lambda request: httpx.Response(200, json={"history": []}))
    store = RawStore(tmp_path)
    capture_series(10114, store, gamma=FakeGamma(events), http=http, sleep=lambda s: None)

    manifest = write_manifest(store)

    files = {f["path"]: f for f in manifest["files"]}
    assert len(files) == 3
    for path, entry in files.items():
        assert hashlib.sha256((tmp_path / path).read_bytes()).hexdigest() == entry["sha256"]
    assert json.loads((tmp_path / "manifest.json").read_text())["files"] == manifest["files"]


def test_cli_capture_writes_manifest(tmp_path, monkeypatch, capsys, events):
    from polym4v import cli

    class FakePublic(FakeGamma):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return None

    fake_http, _ = clob(lambda request: httpx.Response(200, json={"history": []}))
    monkeypatch.setattr(cli, "PublicClient", lambda: FakePublic(events))
    monkeypatch.setattr(cli.httpx, "Client", lambda timeout: fake_http)
    monkeypatch.setattr("polym4v.data.capture.time.sleep", lambda s: None)

    assert cli.main(["capture", "--series", "10114", "--out", str(tmp_path), "--pause", "0"]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["files"] == 3
    assert result["series"][0]["downloaded"] == 2
    assert (tmp_path / "manifest.json").exists()


def test_cli_manifest_rebuilds_hashes(tmp_path, capsys):
    from polym4v import cli

    RawStore(tmp_path).write(RawStore(tmp_path).price_path("111"), {"body": {"history": []}})

    assert cli.main(["manifest", "--out", str(tmp_path)]) == 0

    assert json.loads(capsys.readouterr().out) == {"files": 1}
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["files"][0]["path"] == "clob/prices-history/111.json.gz"
