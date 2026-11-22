"""Assert helpers that never include PII in failure messages."""

from __future__ import annotations

SAFE_ORDER_KEYS = (
    "id",
    "status",
    "status_id",
    "currency",
    "payment_code",
    "is_cod",
)


def public_order_view(order: dict) -> dict:
    """Keep only non-PII fields for assertions / error text."""
    view = {k: order.get(k) for k in SAFE_ORDER_KEYS}
    ep = order.get("europarcel") or {}
    view["europarcel_service"] = ep.get("service_name")
    view["carrier_id"] = ep.get("carrier_id")
    view["service_id"] = ep.get("service_id")
    return view


def assert_status_ids(orders: list[dict], allowed: set[int]) -> None:
    bad = [
        {"id": o.get("id"), "status_id": o.get("status_id")}
        for o in orders
        if o.get("status_id") not in allowed
    ]
    assert not bad, f"unexpected status_id values: {bad}"


def assert_ids_after(orders: list[dict], after_id: int) -> None:
    bad = [o.get("id") for o in orders if not isinstance(o.get("id"), int) or o["id"] <= after_id]
    assert not bad, f"order_id_after={after_id} violated by ids: {bad}"


def assert_has_contract_keys(order: dict) -> None:
    required = {
        "id",
        "status_id",
        "payment_code",
        "is_cod",
        "europarcel",
        "line_items",
    }
    missing = sorted(required - set(order))
    assert not missing, f"order id={order.get('id')} missing keys: {missing}"
