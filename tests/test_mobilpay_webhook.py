"""Mobilpay webhook: negatives, failed payment, idempotency."""

from order_flow import (
    ACTION_TO_STATUS,
    ERR_INVALID_ACTION,
    ERR_INVALID_METHOD,
    ERR_INVALID_PARAMS,
    OrderStore,
    STATUS,
    apply_duplicate_confirmed,
    assert_action_keys_aligned,
    handle_mobilpay_webhook,
)


def test_sandbox_actions_match_production_keys():
    assert_action_keys_aligned()


def test_webhook_rejects_get_method():
    store = OrderStore()
    order = store.create()
    result = handle_mobilpay_webhook(
        store,
        method="GET",
        post={"env_key": "a", "data": "b"},
        action="confirmed",
        order_id=order.order_id,
    )
    assert not result.ok
    assert result.error_code == ERR_INVALID_METHOD
    assert store.get(order.order_id).status_id == STATUS["pending"]


def test_webhook_rejects_missing_payload():
    store = OrderStore()
    order = store.create()
    result = handle_mobilpay_webhook(
        store,
        method="POST",
        post={},
        action="confirmed",
        order_id=order.order_id,
    )
    assert result.error_code == ERR_INVALID_PARAMS
    assert store.get(order.order_id).status_id == STATUS["pending"]


def test_webhook_rejects_unknown_action():
    store = OrderStore()
    order = store.create()
    result = handle_mobilpay_webhook(
        store,
        method="POST",
        post={"env_key": "a", "data": "b"},
        action="fraud",
        order_id=order.order_id,
    )
    assert result.error_code == ERR_INVALID_ACTION
    assert store.get(order.order_id).status_id == STATUS["pending"]


def test_failed_payment_does_not_change_status():
    store = OrderStore()
    order = store.create()
    result = handle_mobilpay_webhook(
        store,
        method="POST",
        post={"env_key": "a", "data": "b"},
        notify_error_code=16,
        action="confirmed",
        order_id=order.order_id,
    )
    assert result.ok  # CRC still returned to gateway
    assert store.get(order.order_id).status_id == STATUS["pending"]
    assert store.exportable(order.order_id) is False


def test_confirmed_makes_order_exportable_to_europarcel():
    store = OrderStore()
    order = store.create()
    result = handle_mobilpay_webhook(
        store,
        method="POST",
        post={"env_key": "a", "data": "b"},
        action="confirmed",
        order_id=order.order_id,
    )
    assert result.ok
    assert store.get(order.order_id).status_id == ACTION_TO_STATUS["confirmed"]
    assert store.exportable(order.order_id) is True


def test_duplicate_confirmed_is_idempotent_for_final_status():
    store = OrderStore()
    order = store.create()
    first = handle_mobilpay_webhook(
        store,
        method="POST",
        post={"env_key": "a", "data": "b"},
        action="confirmed",
        order_id=order.order_id,
    )
    second = apply_duplicate_confirmed(store, order.order_id)
    assert first.ok and second.ok
    updated = store.get(order.order_id)
    assert updated.status_id == STATUS["complete"]
    assert updated.history == [STATUS["complete"], STATUS["complete"]]
