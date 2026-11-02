import gzip
import json
from types import SimpleNamespace

from polymarket import RequestRejectedError, TransportError

from polym4v.data.capture import AFTER_S, BEFORE_S, RawStore, write_manifest
from polym4v.data.trades import PAGE_SIZE, TRADE_FIELDS, capture_trades


def make_trade(price):
    data = dict.fromkeys(TRADE_FIELDS, "x") | {"price": price, "wallet": "0x1", "name": "alguien"}
    trade = SimpleNamespace()
    trade.model_dump = lambda mode="json": data
    return trade


class FakePaginator:
    """Páginas con cursor como el Paginator del SDK, con fallas de red opcionales."""

    def __init__(self, pages, failures=0, limit_reached=False):
        self.pages, self.failures, self.limit_reached = pages, failures, limit_reached

    def first_page(self, cursor=None):
        if self.failures:
            self.failures -= 1
            raise TransportError("conexión cortada")
        index = int(cursor or 0)
        last = len(self.pages) - 1
        return SimpleNamespace(
            items=tuple(self.pages[index]),
            has_more=index < last and not self.limit_reached,
            next_cursor=str(index + 1) if index < last else None,
            limit_reached=self.limit_reached,
        )

    def from_cursor(self, cursor):
        return SimpleNamespace(first_page=lambda: self.first_page(cursor))


class FakeClient:
    def __init__(self, by_market):
        self.by_market = by_market
        self.calls = []

    def list_trades(self, **kwargs):
        self.calls.append(kwargs)
        result = self.by_market[kwargs["condition_id"]]
        if isinstance(result, Exception):
            raise result
        return result


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def no_sleep(_):
    pass


def test_saves_every_page_with_its_request(tmp_path):
    store = RawStore(tmp_path)
    pages = [[make_trade(0.5), make_trade(0.51)], [make_trade(0.52)]]
    client = FakeClient({"0xa": FakePaginator(pages)})

    summary = capture_trades([("0xa", 1000)], store, client=client, sleep=no_sleep)

    assert summary["downloaded"] == 1 and summary["trades"] == 3 and not summary["errors"]
    assert client.calls == [
        {
            "condition_id": "0xa",
            "taker_only": True,
            "start": 1000 - BEFORE_S,
            "end": 1000 + AFTER_S,
            "page_size": PAGE_SIZE,
        }
    ]
    saved = read(store.trades_path("0xa"))
    assert [t["price"] for t in saved["body"]] == [0.5, 0.51, 0.52]
    # Sin datos de la cuenta que hizo el trade.
    assert set(saved["body"][0]) == set(TRADE_FIELDS)
    assert saved["request"]["params"]["taker_only"] is True
    assert saved["limit_reached"] is False


def test_second_run_uses_no_network(tmp_path):
    store = RawStore(tmp_path)
    capture_trades(
        [("0xa", 1000)],
        store,
        client=FakeClient({"0xa": FakePaginator([[make_trade(0.5)]])}),
        sleep=no_sleep,
    )
    client = FakeClient({})

    summary = capture_trades([("0xa", 1000)], store, client=client, sleep=no_sleep)

    assert client.calls == [] and summary["cached"] == 1 and summary["downloaded"] == 0
    assert write_manifest(store)["files"][0]["path"] == "data-api/trades/0xa.json.gz"


def test_network_failure_retries_the_same_page(tmp_path):
    store = RawStore(tmp_path)
    client = FakeClient({"0xa": FakePaginator([[make_trade(0.5)]], failures=2)})

    summary = capture_trades([("0xa", 1000)], store, client=client, sleep=no_sleep)

    assert summary["downloaded"] == 1 and not summary["errors"]


def test_failed_market_is_reported_and_not_saved(tmp_path):
    store = RawStore(tmp_path)
    client = FakeClient(
        {
            "0xa": RequestRejectedError("rechazada", status=400),
            "0xb": FakePaginator([[make_trade(0.5)]]),
        }
    )

    summary = capture_trades([("0xa", 1000), ("0xb", 2000)], store, client=client, sleep=no_sleep)

    assert summary["errors"] == [{"market_id": "0xa", "error": "RequestRejectedError"}]
    assert not store.trades_path("0xa").exists() and store.trades_path("0xb").exists()


def test_limit_reached_is_flagged(tmp_path):
    store = RawStore(tmp_path)
    pages = [[make_trade(0.5)], [make_trade(0.6)]]
    client = FakeClient({"0xa": FakePaginator(pages, limit_reached=True)})

    summary = capture_trades([("0xa", 1000)], store, client=client, sleep=no_sleep)

    assert summary["limit_reached"] == ["0xa"]
    assert read(store.trades_path("0xa"))["limit_reached"] is True
