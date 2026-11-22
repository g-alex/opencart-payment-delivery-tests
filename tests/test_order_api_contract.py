"""Contract checks for Europarcel orders API payload shape."""

import pytest
import requests

from rules import assert_order_api_shape, is_cash_on_delivery


def test_fixture_orders_match_contract(sample_orders_payload):
    assert "orders" in sample_orders_payload
    assert sample_orders_payload["total"] == len(sample_orders_payload["orders"])
    for order in sample_orders_payload["orders"]:
        assert_order_api_shape(order)


def test_fixture_cod_flag_matches_payment_code(sample_orders_payload):
    for order in sample_orders_payload["orders"]:
        expected = is_cash_on_delivery(order["payment_code"])
        assert order["is_cod"] is expected


def test_fixture_europarcel_carrier_present_for_known_services(sample_orders_payload):
    for order in sample_orders_payload["orders"]:
        ep = order["europarcel"]
        if ep["service_name"] in ("home", "locker"):
            assert ep["service_id"] in (1, 2)
            assert ep["carrier_id"] is not None


@pytest.mark.integration
def test_live_api_rejects_missing_key(api_base):
    url = f"{api_base}/index.php?route=extension/europarcel/europarcel/api/test"
    resp = requests.get(url, timeout=20)
    assert resp.status_code == 401
    body = resp.json()
    assert body.get("error") == "AUTHENTICATION_FAILED"


@pytest.mark.integration
def test_live_api_test_and_orders(api_base, api_key):
    """Read-only GET. Asserts non-PII fields only."""
    if not api_key:
        pytest.skip("Set EUROPARCEL_API_KEY to run live API checks")

    from safe_assert import assert_has_contract_keys

    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    test_url = f"{api_base}/index.php?route=extension/europarcel/europarcel/api/test"
    test_resp = requests.get(test_url, headers=headers, timeout=20)
    assert test_resp.status_code == 200
    test_body = test_resp.json()
    assert test_body.get("success") is True
    assert test_body.get("extension") == "europarcel"

    orders_url = (
        f"{api_base}/index.php?route=extension/europarcel/europarcel/api/orders"
        f"&status=Complete&limit=5"
    )
    orders_resp = requests.get(orders_url, headers=headers, timeout=30)
    assert orders_resp.status_code == 200
    payload = orders_resp.json()
    assert "orders" in payload
    assert "total" in payload
    for order in payload["orders"][:5]:
        assert_has_contract_keys(order)
        assert order["status_id"] > 0
        if order.get("payment_code") == "mobilpay":
            assert order["is_cod"] is False


@pytest.mark.integration
def test_live_api_order_not_found(api_base, api_key):
    if not api_key:
        pytest.skip("Set EUROPARCEL_API_KEY to run live API checks")
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    url = (
        f"{api_base}/index.php?route=extension/europarcel/europarcel/api/order"
        f"&order_id=999999999"
    )
    resp = requests.get(url, headers=headers, timeout=20)
    assert resp.status_code == 404
    assert resp.json().get("error") == "ORDER_NOT_FOUND"
