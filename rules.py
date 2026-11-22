"""
Business rules mirrored from OpenCart production code (payment/delivery).

Source of truth:
  - www/catalog/model/extension/shipping/europarcel_api.php
  - www/catalog/controller/extension/payment/mobilpay.php
  - www/catalog/model/extension/shipping/europarcel.php
"""

from __future__ import annotations

CARRIER_SETTINGS = {
    "cargus_national": {"carrier_id": 1, "service_id": 1},
    "dpd_standard": {"carrier_id": 2, "service_id": 1},
    "fan_courier": {"carrier_id": 3, "service_id": 1},
    "gls_national": {"carrier_id": 4, "service_id": 1},
    "sameday": {"carrier_id": 6, "service_id": 1},
    "bookurier": {"carrier_id": 5, "service_id": 1},
    "easybox": {"carrier_id": 6, "service_id": 2},
    "fanbox": {"carrier_id": 3, "service_id": 2},
    "dpdbox": {"carrier_id": 2, "service_id": 2},
    "carguslocker": {"carrier_id": 1, "service_id": 2},
}

# Mobilpay callback action -> config key for target order_status_id
MOBILPAY_ACTION_STATUS_KEYS = {
    "confirmed": "payment_mobilpay_order_status_id",
    "confirmed_pending": "payment_mobilpay_order_status_confirmed_pending_id",
    "paid_pending": "payment_mobilpay_order_status_paid_pending_id",
    "paid": "payment_mobilpay_order_status_paid_id",
    "canceled": "payment_mobilpay_order_status_canceled_id",
    "credit": "payment_mobilpay_order_status_credit_id",
}

ORDER_API_REQUIRED_FIELDS = (
    "id",
    "status",
    "status_id",
    "currency",
    "total",
    "subtotal",
    "shipping_total",
    "discount_total",
    "date_created",
    "payment_method",
    "payment_code",
    "is_cod",
    "customer",
    "shipping",
    "shipping_method",
    "europarcel",
    "line_items",
)


def is_cash_on_delivery(payment_code: str, cod_methods: list[str] | None = None) -> bool:
    """Mirrors ModelExtensionShippingEuroparcelApi::isCashOnDeliveryPayment."""
    if not payment_code:
        return False
    if not cod_methods:
        return "cod" in payment_code.lower()
    base = payment_code.split(".", 1)[0]
    return payment_code in cod_methods or base in cod_methods


def resolve_carrier(
    service_name: str | None,
    selected_locker: dict | None = None,
    home_default_courier: str | None = None,
) -> dict:
    """Mirrors ModelExtensionShippingEuroparcelApi::resolveCarrierInfo."""
    if service_name == "home":
        if home_default_courier and home_default_courier in CARRIER_SETTINGS:
            return dict(CARRIER_SETTINGS[home_default_courier])
        return {"carrier_id": None, "service_id": 1}

    if service_name == "locker":
        if selected_locker:
            if selected_locker.get("carrier_id"):
                return {
                    "carrier_id": int(selected_locker["carrier_id"]),
                    "service_id": 2,
                }
            locker_type = selected_locker.get("type") or selected_locker.get("locker_type")
            if locker_type and locker_type in CARRIER_SETTINGS:
                return dict(CARRIER_SETTINGS[locker_type])
        # ponytail: locker without saved data falls back to Sameday easybox
        return {"carrier_id": 6, "service_id": 2}

    return {"carrier_id": None, "service_id": None}


def convert_weight_to_kg(weight: float, unit: str) -> float:
    unit = (unit or "kg").lower()
    if unit == "g":
        return weight / 1000
    if unit == "lb":
        return weight * 0.453592
    if unit == "oz":
        return weight * 0.0283495
    return weight


def convert_length_to_cm(length: float, unit: str) -> float:
    unit = (unit or "cm").lower()
    if unit == "mm":
        return length / 10
    if unit == "in":
        return length * 2.54
    if unit == "m":
        return length * 100
    return length


def aggregate_order_totals(rows: list[dict]) -> dict:
    """Mirrors ModelExtensionShippingEuroparcelApi::getOrderTotals."""
    totals = {
        "subtotal": 0.0,
        "shipping_total": 0.0,
        "discount_total": 0.0,
        "total": 0.0,
    }
    for row in rows:
        code = row["code"]
        value = float(row["value"])
        if code == "sub_total":
            totals["subtotal"] = value
        elif code == "shipping":
            totals["shipping_total"] = value
        elif code == "total":
            totals["total"] = value
        elif code in ("coupon", "voucher"):
            totals["discount_total"] += abs(value)
    return totals


def shipping_cost(base_cost: float, free_from: float, sub_total: float) -> float:
    """Mirrors free-shipping threshold in ModelExtensionShippingEuroparcel::getQuote."""
    if free_from != 0 and free_from < sub_total:
        return 0.0
    return float(base_cost)


def status_names_to_ids(status_csv: str, status_map: dict[str, int]) -> list[int]:
    """Mirrors status filter parsing in ControllerEuroparcelApi::orders."""
    ids = []
    for name in [n.strip() for n in status_csv.split(",") if n.strip()]:
        key = name.lower()
        if key in status_map:
            ids.append(status_map[key])
    return ids


def mobilpay_status_config_key(action: str) -> str | None:
    return MOBILPAY_ACTION_STATUS_KEYS.get(action)


def assert_order_api_shape(order: dict) -> None:
    missing = [f for f in ORDER_API_REQUIRED_FIELDS if f not in order]
    if missing:
        raise AssertionError(f"Order missing fields: {missing}")
    for nested in ("customer", "shipping", "shipping_method", "europarcel"):
        if not isinstance(order[nested], dict):
            raise AssertionError(f"{nested} must be object")
    if not isinstance(order["line_items"], list):
        raise AssertionError("line_items must be list")
    if not isinstance(order["is_cod"], bool):
        raise AssertionError("is_cod must be bool")
    if not isinstance(order["status_id"], int):
        raise AssertionError("status_id must be int")
