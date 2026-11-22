"""
Sandbox order lifecycle for OpenCart payment/delivery tests.

Mirrors Mobilpay callback behavior + Europarcel export rule
(order_status_id > 0) without hitting live payment/courier.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rules import MOBILPAY_ACTION_STATUS_KEYS, mobilpay_status_config_key

# From Mobilpay_Payment_Request_Abstract
ERR_NONE = 0x00
ERR_TEMPORARY = 0x01
ERR_PERMANENT = 0x02
ERR_INVALID_METHOD = 0x300000F4
ERR_INVALID_PARAMS = 0x300000F5
ERR_INVALID_ACTION = 0x300000F6

# Demo status ids (sandbox config)
STATUS = {
    "pending": 0,  # cart / unpaid — not exported to Europarcel
    "paid": 2,
    "processing": 3,
    "complete": 5,
    "canceled": 7,
    "confirmed_pending": 11,
    "paid_pending": 12,
    "credit": 13,
}

ACTION_TO_STATUS = {
    "confirmed": STATUS["complete"],
    "confirmed_pending": STATUS["confirmed_pending"],
    "paid_pending": STATUS["paid_pending"],
    "paid": STATUS["paid"],
    "canceled": STATUS["canceled"],
    "credit": STATUS["credit"],
}


@dataclass
class Order:
    order_id: int
    status_id: int = STATUS["pending"]
    payment_code: str = "mobilpay"
    total: float = 100.0
    history: list[int] = field(default_factory=list)


@dataclass
class WebhookResult:
    error_type: int
    error_code: int
    message: str

    @property
    def ok(self) -> bool:
        return self.error_code == 0


class OrderStore:
    def __init__(self) -> None:
        self._orders: dict[int, Order] = {}
        self._next_id = 1

    def create(self, total: float = 100.0, payment_code: str = "mobilpay") -> Order:
        order = Order(order_id=self._next_id, total=total, payment_code=payment_code)
        self._orders[self._next_id] = order
        self._next_id += 1
        return order

    def get(self, order_id: int) -> Order | None:
        return self._orders.get(order_id)

    def set_status(self, order_id: int, status_id: int) -> None:
        order = self._orders[order_id]
        order.status_id = status_id
        order.history.append(status_id)

    def exportable(self, order_id: int) -> bool:
        """Europarcel API filter: order_status_id > 0."""
        order = self.get(order_id)
        return bool(order and order.status_id > 0)


def handle_mobilpay_webhook(
    store: OrderStore,
    *,
    method: str,
    post: dict,
    notify_error_code: int = 0,
    action: str | None = None,
    order_id: int | None = None,
) -> WebhookResult:
    """Mirrors ControllerExtensionPaymentMobilpay::callback decision tree."""
    if method.upper() != "POST":
        return WebhookResult(ERR_PERMANENT, ERR_INVALID_METHOD, "invalid request metod")

    if "env_key" not in post or "data" not in post:
        return WebhookResult(ERR_PERMANENT, ERR_INVALID_PARAMS, "invalid parameters")

    if order_id is None or store.get(order_id) is None:
        return WebhookResult(ERR_TEMPORARY, 1, "order not found")

    if notify_error_code != 0:
        # payment failed / rejected — status unchanged
        return WebhookResult(ERR_NONE, 0, "crc-failed-payment")

    if not action or action not in ACTION_TO_STATUS:
        return WebhookResult(
            ERR_PERMANENT,
            ERR_INVALID_ACTION,
            "mobilpay_refference_action paramaters is invalid",
        )

    store.set_status(order_id, ACTION_TO_STATUS[action])
    return WebhookResult(ERR_NONE, 0, f"crc-{action}")


def apply_duplicate_confirmed(store: OrderStore, order_id: int) -> WebhookResult:
    """Second confirmed webhook: status stays paid/complete, history grows."""
    return handle_mobilpay_webhook(
        store,
        method="POST",
        post={"env_key": "x", "data": "y"},
        action="confirmed",
        order_id=order_id,
    )


def lifecycle_pay_success(store: OrderStore, order_id: int) -> list[int]:
    """create already done → paid → confirmed (shippable / Complete)."""
    handle_mobilpay_webhook(
        store,
        method="POST",
        post={"env_key": "x", "data": "y"},
        action="paid",
        order_id=order_id,
    )
    handle_mobilpay_webhook(
        store,
        method="POST",
        post={"env_key": "x", "data": "y"},
        action="confirmed",
        order_id=order_id,
    )
    return list(store.get(order_id).history)


def assert_action_keys_aligned() -> None:
    """Guard: sandbox ACTION_TO_STATUS keys match production mapping keys."""
    missing = set(MOBILPAY_ACTION_STATUS_KEYS) - set(ACTION_TO_STATUS)
    if missing:
        raise AssertionError(f"sandbox missing actions: {missing}")
    for action in ACTION_TO_STATUS:
        if mobilpay_status_config_key(action) is None:
            raise AssertionError(f"no production key for {action}")
