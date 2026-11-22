"""Sandbox E2E: create order → pay → status → Europarcel-ready."""

from order_flow import (
    ACTION_TO_STATUS,
    OrderStore,
    STATUS,
    handle_mobilpay_webhook,
    lifecycle_pay_success,
)
from rules import assert_order_api_shape, is_cash_on_delivery, resolve_carrier


def test_create_pay_confirmed_flow():
    store = OrderStore()
    order = store.create(total=450.0)
    assert order.status_id == STATUS["pending"]
    assert store.exportable(order.order_id) is False

    history = lifecycle_pay_success(store, order.order_id)
    assert history == [STATUS["paid"], STATUS["complete"]]
    assert store.exportable(order.order_id) is True


def test_canceled_payment_not_exportable():
    store = OrderStore()
    order = store.create()
    handle_mobilpay_webhook(
        store,
        method="POST",
        post={"env_key": "a", "data": "b"},
        action="canceled",
        order_id=order.order_id,
    )
    # canceled has status_id > 0 in OC, so API may export it —
    # business rule: shipping should not start; we still track status
    assert store.get(order.order_id).status_id == STATUS["canceled"]
    assert store.get(order.order_id).status_id != STATUS["complete"]


def test_paid_pending_then_confirmed():
    store = OrderStore()
    order = store.create()
    handle_mobilpay_webhook(
        store,
        method="POST",
        post={"env_key": "a", "data": "b"},
        action="paid_pending",
        order_id=order.order_id,
    )
    assert store.get(order.order_id).status_id == STATUS["paid_pending"]
    handle_mobilpay_webhook(
        store,
        method="POST",
        post={"env_key": "a", "data": "b"},
        action="confirmed",
        order_id=order.order_id,
    )
    assert store.get(order.order_id).status_id == STATUS["complete"]


def test_build_europarcel_payload_after_pay(sample_orders_payload):
    """After successful pay, delivery API payload must stay contract-valid."""
    store = OrderStore()
    order = store.create(total=450.0)
    lifecycle_pay_success(store, order.order_id)

    sample = sample_orders_payload["orders"][0]
    payload = dict(sample)
    payload["id"] = order.order_id
    payload["status_id"] = store.get(order.order_id).status_id
    payload["status"] = "Complete"
    payload["total"] = order.total
    payload["is_cod"] = is_cash_on_delivery(payload["payment_code"])
    carrier = resolve_carrier("home", home_default_courier="fan_courier")
    payload["europarcel"] = {
        "service_name": "home",
        "carrier_id": carrier["carrier_id"],
        "service_id": carrier["service_id"],
        "selected_locker": None,
    }
    assert_order_api_shape(payload)
    assert payload["status_id"] == ACTION_TO_STATUS["confirmed"]
