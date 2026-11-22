"""Sandbox: COD vs card payment → Europarcel export readiness."""

from order_flow import STATUS, OrderStore, handle_mobilpay_webhook, lifecycle_pay_success
from rules import is_cash_on_delivery, resolve_carrier


def test_card_pending_then_confirmed():
    store = OrderStore()
    order = store.create(payment_code="mobilpay")
    assert is_cash_on_delivery(order.payment_code) is False
    assert store.exportable(order.order_id) is False

    history = lifecycle_pay_success(store, order.order_id)
    assert history == [STATUS["paid"], STATUS["complete"]]
    assert store.exportable(order.order_id) is True


def test_cod_exportable_without_card_webhook():
    store = OrderStore()
    order = store.create(payment_code="cod")
    assert is_cash_on_delivery(order.payment_code) is True
    # merchant marks order Processing manually (no Mobilpay)
    store.set_status(order.order_id, STATUS["processing"])
    assert store.exportable(order.order_id) is True
    assert store.get(order.order_id).status_id != STATUS["pending"]


def test_cod_and_card_locker_carrier_differs_from_home():
    home = resolve_carrier("home", home_default_courier="fan_courier")
    locker = resolve_carrier("locker", {"type": "easybox"})
    assert home["service_id"] == 1
    assert locker["service_id"] == 2
    assert locker["carrier_id"] == 6


def test_failed_card_stays_non_complete():
    store = OrderStore()
    order = store.create(payment_code="mobilpay")
    handle_mobilpay_webhook(
        store,
        method="POST",
        post={"env_key": "a", "data": "b"},
        notify_error_code=16,
        action="confirmed",
        order_id=order.order_id,
    )
    assert store.get(order.order_id).status_id == STATUS["pending"]
    assert store.exportable(order.order_id) is False
