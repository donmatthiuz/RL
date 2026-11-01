"""Las APIs reales siguen entregando lo que leen el crudo y el dataset (INF-08).

Corren en el nightly (`make nightly`), no en cada push. Si uno falla, la API cambió de forma o dejó
de responder (riesgo R1 de docs/07): R2 lo revisa y lo anota en el tablero. Usan el mercado más
antiguo de la serie de `configs/data.yaml`, que ya está cerrado y no cambia.
"""

from datetime import timedelta

import httpx
import pytest
from polymarket import PublicClient

from polym4v.data.binance import capture_klines
from polym4v.data.build_dataset import _read, _ticks, load_klines, parse_market
from polym4v.data.capture import RawStore, capture_series
from polym4v.data.trades import TRADE_FIELDS, capture_trades
from polym4v.utils.config import DataConfig, load_config

pytestmark = pytest.mark.network

CONFIG = load_config("configs/data.yaml", DataConfig)


@pytest.fixture(scope="module")
def market(tmp_path_factory):
    """El primer evento cerrado de la serie, capturado y leído como lo hace el dataset."""
    store = RawStore(tmp_path_factory.mktemp("raw"))
    with PublicClient() as gamma, httpx.Client(timeout=30) as http:
        summary = capture_series(CONFIG.series_id, store, gamma=gamma, http=http, limit=1)
    assert summary["errors"] == [] and summary["events"] == 1
    [path] = (store.root / "gamma" / "events").rglob("*.json.gz")
    parsed = parse_market(_read(path), CONFIG.window_minutes * 60)
    assert isinstance(parsed, dict), parsed
    return store, parsed


def test_gamma_event_parses_into_a_resolved_market(market):
    _, parsed = market
    assert parsed["market_id"].startswith("0x") and parsed["outcome"] in (0, 1)
    assert parsed["w1"] - parsed["w0"] == CONFIG.window_minutes * 60


def test_clob_history_has_points_inside_the_window(market):
    store, parsed = market
    ticks = _ticks(store, parsed, parsed["w0"] - CONFIG.context_minutes * 60, 0)
    assert isinstance(ticks, list), ticks
    inside = [t for t in ticks if parsed["w0"] <= t["ts_event"] < parsed["w1"]]
    assert {t["side"] for t in inside} == {"yes", "no"}


def test_data_api_trades_have_the_fields_we_keep(market, tmp_path):
    _, parsed = market
    store = RawStore(tmp_path)
    with PublicClient() as client:
        summary = capture_trades([(parsed["market_id"], parsed["w0"])], store, client=client)
    assert summary["errors"] == [] and summary["trades"] > 0
    trades = _read(store.trades_path(parsed["market_id"]))["body"]
    assert set(TRADE_FIELDS) <= set(trades[0])


def test_binance_gives_one_kline_per_hour(tmp_path):
    store = RawStore(tmp_path)
    day = CONFIG.date_from
    with httpx.Client(timeout=30) as http:
        summary = capture_klines("BTCUSDT", "1h", day, day + timedelta(days=1), store, http=http)
    assert summary["errors"] == [] and summary["downloaded"] >= 1
    assert len(load_klines(store, "BTCUSDT", "1h")) == 24
