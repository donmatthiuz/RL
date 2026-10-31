from __future__ import annotations

import json
import os
from decimal import Decimal
from unittest.mock import MagicMock

import httpx
import pytest
from polymarket import Market, SecureClient, UserInputError

from polym4v import (
    ConfigurationError,
    PolymarketClient,
    PolymarketSettings,
    get_asset_id,
)
from polym4v.cli import main


@pytest.fixture(autouse=True)
def mock_http(monkeypatch, tmp_path):
    # No prueba puede leer .env ni conectarse a servicios reales.
    monkeypatch.chdir(tmp_path)
    for name in tuple(os.environ):
        if name.startswith("POLYMARKET_"):
            monkeypatch.delenv(name)

    def block_network(request):
        raise AssertionError(f"Petición HTTP no simulada: {request.url}")

    handler = block_network
    clients = []
    requests = []
    real_init = httpx.Client.__init__

    def handle(request):
        requests.append(request)
        return handler(request)

    def mock_init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handle)
        real_init(self, *args, **kwargs)
        clients.append(self)

    monkeypatch.setattr(httpx.Client, "__init__", mock_init)

    def install(responder):
        # Se conserva el SDK real y se simula únicamente su transporte HTTP.
        nonlocal handler
        handler = responder
        return requests, clients

    return install


@pytest.fixture
def raw_market():
    return {
        "id": "1",
        "slug": "example-market",
        "question": "Will the example happen?",
        "conditionId": "0x" + "1" * 64,
        "version": "v1",
        "outcomes": '["Yes", "No"]',
        "clobTokenIds": '["123", "456"]',
        "outcomePrices": '["0.42", "0.58"]',
        "active": True,
        "closed": False,
    }


def test_env_file_priority_and_no_global_mutation(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "POLYMARKET_PRIVATE_KEY=from-file\n"
        "POLYMARKET_WALLET_ADDRESS=wallet-from-file\n"
        "POLYMARKET_API_SECRET=  \n",
        encoding="utf-8",
    )
    monkeypatch.setenv("POLYMARKET_PRIVATE_KEY", "from-process")
    settings = PolymarketSettings.from_env(env_file)
    assert settings.private_key == "from-process"
    assert settings.wallet_address == "wallet-from-file"
    assert settings.api_secret is None
    assert "POLYMARKET_WALLET_ADDRESS" not in os.environ


def test_settings_repr_hides_all_secrets():
    settings = PolymarketSettings(
        private_key="private-value", api_key="key-value",
        api_secret="secret-value", api_passphrase="passphrase-value",
    )
    assert "value" not in repr(settings)


@pytest.mark.parametrize(
    ("kwargs", "missing"),
    [
        ({}, "POLYMARKET_PRIVATE_KEY"),
        ({"private_key": "private"}, "POLYMARKET_WALLET_ADDRESS"),
        ({"private_key": "private", "wallet_address": "wallet", "api_key": "partial"},
         "POLYMARKET_API_SECRET"),
    ],
)
def test_invalid_authentication_fails_before_requests(kwargs, missing):
    with pytest.raises(ConfigurationError, match=missing):
        PolymarketClient(PolymarketSettings(**kwargs), authenticated=True)


def test_authenticated_connection_forwards_credentials_and_closes(monkeypatch):
    sdk = MagicMock(spec=SecureClient)
    sdk.wallet = "0xaccount"
    sdk.wallet_type = "GNOSIS_SAFE"
    factory = MagicMock(return_value=sdk)
    monkeypatch.setattr(SecureClient, "create", factory)
    settings = PolymarketSettings(
        private_key="private", wallet_address="0xaccount", api_key="key",
        api_secret="secret", api_passphrase="passphrase",
    )
    with PolymarketClient(settings, authenticated=True) as client:
        assert client.get_account() == {"wallet": "0xaccount", "wallet_type": "GNOSIS_SAFE"}
        client.list_open_orders()
    passed = factory.call_args.kwargs
    assert passed["private_key"] == "private"
    assert passed["wallet"] == "0xaccount"
    assert passed["credentials"].secret == "secret"
    sdk.list_open_orders.assert_called_once_with()
    sdk.close.assert_called_once_with()


def test_authenticated_connection_can_derive_credentials(monkeypatch):
    factory = MagicMock(return_value=MagicMock(spec=SecureClient))
    monkeypatch.setattr(SecureClient, "create", factory)
    settings = PolymarketSettings(private_key="private", wallet_address="wallet")
    with PolymarketClient(settings, authenticated=True):
        pass
    assert factory.call_args.kwargs["credentials"] is None


def test_market_pagination_round_trip_and_public_mode(mock_http, raw_market, monkeypatch):
    factory = MagicMock(side_effect=AssertionError("No autenticar una consulta pública"))
    monkeypatch.setattr(SecureClient, "create", factory)
    monkeypatch.setenv("POLYMARKET_PRIVATE_KEY", "ignored-in-public-mode")

    def handler(request):
        assert request.url.host == "gamma-api.polymarket.com"
        assert request.url.path == "/markets/keyset"
        assert request.url.params["closed"] == "false"
        assert request.url.params["limit"] == "1"
        assert not any(name.lower().startswith("poly_") for name in request.headers)
        if "after_cursor" in request.url.params:
            assert request.url.params["after_cursor"] == "server-cursor"
            return httpx.Response(200, json={"markets": [], "next_cursor": None})
        return httpx.Response(200, json={"markets": [raw_market], "next_cursor": "server-cursor"})

    requests, clients = mock_http(handler)
    with PolymarketClient() as client:
        page = client.list_markets(limit=1)
        assert page.items[0].question == raw_market["question"]
        assert page.items[0].outcomes.yes.price == Decimal("0.42")
        assert page.has_more
        second = client.list_markets(limit=1, cursor=page.next_cursor)
        assert not second.has_more
        assert not second.items
    assert len(requests) == 2
    assert all(client.is_closed for client in clients)
    factory.assert_not_called()


@pytest.mark.parametrize(("version", "expected"), [("v1", "123"), ("v2", "789")])
def test_asset_id_selects_protocol_and_outcome(raw_market, version, expected):
    raw_market.update(version=version, positionIds=["789", "790"])
    market = Market.model_validate(raw_market)
    assert get_asset_id(market) == expected
    assert get_asset_id(market, outcome="no") == ("790" if version == "v2" else "456")


def test_asset_id_missing_is_explicit(raw_market):
    raw_market["clobTokenIds"] = '[]'
    market = Market.model_validate(raw_market)
    with pytest.raises(UserInputError, match="identificador"):
        get_asset_id(market)


@pytest.mark.parametrize(
    ("command", "path", "payload", "expected"),
    [
        (["price", "123", "--side", "SELL"], "/price", {"price": "0.123456789012345678"},
         {"asset_id": "123", "side": "SELL", "price": "0.123456789012345678"}),
        (["midpoint", "123"], "/midpoint", {"mid": "0.425"},
         {"asset_id": "123", "midpoint": "0.425"}),
    ],
)
def test_clob_commands_preserve_decimal_precision(mock_http, capsys, command, path, payload, expected):
    def handler(request):
        assert request.url.host == "clob.polymarket.com"
        assert request.url.path == path
        assert request.url.params["token_id"] == "123"
        if path == "/price":
            assert request.url.params["side"] == "SELL"
        return httpx.Response(200, json=payload)

    mock_http(handler)
    assert main(command) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == expected
    assert not captured.err


def test_history_uses_data_v2_and_serializes_timestamps(mock_http, capsys):
    def handler(request):
        assert request.url.host == "data-api.polymarket.com"
        assert request.url.path == "/v2/prices-history"
        assert request.url.params["token_id"] == "123"
        assert request.url.params["interval"] == "1d"
        assert request.url.params["bucket_seconds"] == "3600"
        assert request.url.params["limit"] == "100"
        return httpx.Response(200, json={
            "data": [{"timestamp": 1792713600, "price": "0.42", "resolution_seconds": 3600}],
            "pagination": {"has_more": False, "next_cursor": None},
        })

    mock_http(handler)
    assert main(["history", "123"]) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["items"][0]["price"] == "0.42"
    assert result["items"][0]["timestamp"].startswith("2026-10-")
    assert not result["has_more"]


@pytest.mark.parametrize("limit", [0, -1, 101])
def test_invalid_market_limit_never_sends_http(limit):
    with PolymarketClient() as client:
        with pytest.raises(UserInputError, match="límite"):
            client.list_markets(limit=limit)


def test_private_methods_require_explicit_authentication():
    with PolymarketClient() as client:
        with pytest.raises(ConfigurationError, match="authenticated=True"):
            client.list_open_orders()


@pytest.mark.parametrize(("status", "expected"), [(401, "HTTP 401"), (429, "limitó")])
def test_cli_http_errors_never_print_response_secrets(mock_http, capsys, status, expected):
    mock_http(lambda request: httpx.Response(status, json={"error": "secret-never-print"}))
    assert main(["price", "123"]) == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert expected in captured.err
    assert "secret-never-print" not in captured.err


def test_cli_missing_config_is_actionable(capsys):
    assert main(["account"]) == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert "POLYMARKET_PRIVATE_KEY" in captured.err


def test_close_on_http_failure(mock_http):
    def timeout(request):
        raise httpx.ReadTimeout("test", request=request)

    _, clients = mock_http(timeout)
    assert main(["price", "123"]) == 1
    assert all(client.is_closed for client in clients)
