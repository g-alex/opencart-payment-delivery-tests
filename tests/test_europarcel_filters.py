"""Europarcel status / cursor filters — unit + read-only live GET."""

from __future__ import annotations

import pytest
import requests

from europarcel_filters import filter_by_status_ids, filter_date_after, filter_order_id_after
from rules import status_names_to_ids
from safe_assert import assert_has_contract_keys, assert_ids_after, assert_status_ids

SAMPLE = [
    {"id": 1, "status_id": 5, "date_created": "2026-01-01 10:00:00"},
    {"id": 2, "status_id": 7, "date_created": "2026-01-02 10:00:00"},
    {"id": 3, "status_id": 5, "date_created": "2026-01-03 10:00:00"},
    {"id": 4, "status_id": 1, "date_created": "2026-01-04 10:00:00"},
]


def test_filter_complete_excludes_canceled_and_pending():
    status_map = {"complete": 5, "canceled": 7, "pending": 1}
    ids = status_names_to_ids("Complete", status_map)
    filtered = filter_by_status_ids(SAMPLE, ids)
    assert [o["id"] for o in filtered] == [1, 3]
    assert_status_ids(filtered, {5})


def test_filter_order_id_after_cursor():
    filtered = filter_order_id_after(SAMPLE, after_id=2)
    assert [o["id"] for o in filtered] == [3, 4]
    assert_ids_after(filtered, 2)


def test_filter_date_after():
    filtered = filter_date_after(SAMPLE, "2026-01-02 23:59:59")
    assert [o["id"] for o in filtered] == [3, 4]


def test_order_id_after_wins_over_older_ids():
    # mirrors PHP: order_id_after is authoritative cursor
    by_id = filter_order_id_after(SAMPLE, 1)
    assert all(o["id"] > 1 for o in by_id)


@pytest.mark.integration
def test_live_status_filter_complete_read_only(api_base, api_key):
    """GET only — no order create. Asserts status_id only (no PII)."""
    if not api_key:
        pytest.skip("Set EUROPARCEL_API_KEY")
    url = (
        f"{api_base}/index.php?route=extension/europarcel/europarcel/api/orders"
        f"&status=Complete&limit=5"
    )
    resp = requests.get(
        url,
        headers={"X-API-Key": api_key, "Accept": "application/json"},
        timeout=30,
    )
    assert resp.status_code == 200
    orders = resp.json().get("orders") or []
    for order in orders:
        assert_has_contract_keys(order)
    if orders:
        # Complete name may map to one id; all returned must share that id
        expected = {orders[0]["status_id"]}
        assert_status_ids(orders, expected)
        assert all(o["status_id"] > 0 for o in orders)


@pytest.mark.integration
def test_live_order_id_after_cursor_read_only(api_base, api_key):
    if not api_key:
        pytest.skip("Set EUROPARCEL_API_KEY")
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    base = f"{api_base}/index.php?route=extension/europarcel/europarcel/api/orders"
    first = requests.get(f"{base}&limit=2", headers=headers, timeout=30)
    assert first.status_code == 200
    orders = first.json().get("orders") or []
    if len(orders) < 1:
        pytest.skip("no orders to cursor over")
    cursor = min(o["id"] for o in orders)
    second = requests.get(
        f"{base}&order_id_after={cursor}&limit=5",
        headers=headers,
        timeout=30,
    )
    assert second.status_code == 200
    nxt = second.json().get("orders") or []
    assert_ids_after(nxt, cursor)
