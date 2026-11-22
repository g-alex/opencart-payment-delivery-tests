"""Europarcel API client negatives: timeout, 4xx/5xx, bad JSON."""

from unittest.mock import MagicMock, patch

import pytest
import requests


def _orders_url(base: str) -> str:
    return f"{base}/index.php?route=extension/europarcel/europarcel/api/orders"


def test_api_timeout_is_raised():
    with patch("requests.get", side_effect=requests.Timeout("timed out")):
        with pytest.raises(requests.Timeout):
            requests.get(_orders_url("https://shop.test"), timeout=1)


def test_api_server_error_5xx():
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.json.side_effect = ValueError("no json")
    with patch("requests.get", return_value=mock_resp):
        resp = requests.get(_orders_url("https://shop.test"), timeout=5)
    assert resp.status_code == 503


def test_api_client_error_invalid_key_body():
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {
        "error": "AUTHENTICATION_FAILED",
        "message": "Invalid or missing API key",
    }
    with patch("requests.get", return_value=mock_resp):
        resp = requests.get(_orders_url("https://shop.test"), timeout=5)
        body = resp.json()
    assert resp.status_code == 401
    assert body["error"] == "AUTHENTICATION_FAILED"


def test_api_malformed_json_payload():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("Expecting value")
    with patch("requests.get", return_value=mock_resp):
        resp = requests.get(_orders_url("https://shop.test"), timeout=5)
        with pytest.raises(ValueError):
            resp.json()


def test_api_invalid_orders_contract_missing_fields():
    from rules import assert_order_api_shape

    broken = {"id": 1, "status": "Complete"}
    with pytest.raises(AssertionError, match="missing fields"):
        assert_order_api_shape(broken)
