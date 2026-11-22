"""Unit tests for Europarcel delivery/payment mapping rules."""

import pytest

from rules import (
    aggregate_order_totals,
    convert_length_to_cm,
    convert_weight_to_kg,
    is_cash_on_delivery,
    resolve_carrier,
    shipping_cost,
    status_names_to_ids,
)


@pytest.mark.parametrize(
    "code,cod_methods,expected",
    [
        ("", None, False),
        ("mobilpay", None, False),
        ("cod", None, True),
        ("cod.cod", None, True),
        ("bank_transfer", ["cod", "cash"], False),
        ("cod.cod", ["cod"], True),
        ("cod", ["cash"], False),
        ("cash.on.delivery", ["cash"], True),
    ],
)
def test_is_cod(code, cod_methods, expected):
    assert is_cash_on_delivery(code, cod_methods) is expected


def test_resolve_home_uses_default_courier():
    assert resolve_carrier("home", home_default_courier="fan_courier") == {
        "carrier_id": 3,
        "service_id": 1,
    }


def test_resolve_home_without_default():
    assert resolve_carrier("home") == {"carrier_id": None, "service_id": 1}


def test_resolve_locker_from_carrier_id():
    assert resolve_carrier("locker", {"carrier_id": 2}) == {
        "carrier_id": 2,
        "service_id": 2,
    }


def test_resolve_locker_from_type():
    assert resolve_carrier("locker", {"type": "fanbox"}) == {
        "carrier_id": 3,
        "service_id": 2,
    }


def test_resolve_locker_fallback_easybox():
    assert resolve_carrier("locker", None) == {"carrier_id": 6, "service_id": 2}


@pytest.mark.parametrize(
    "weight,unit,expected",
    [
        (1000, "g", 1.0),
        (1, "kg", 1.0),
        (10, "lb", 4.53592),
        (16, "oz", pytest.approx(0.453592)),
    ],
)
def test_weight_to_kg(weight, unit, expected):
    assert convert_weight_to_kg(weight, unit) == expected


@pytest.mark.parametrize(
    "length,unit,expected",
    [
        (10, "mm", 1.0),
        (1, "m", 100.0),
        (2, "in", 5.08),
        (12, "cm", 12.0),
    ],
)
def test_length_to_cm(length, unit, expected):
    assert convert_length_to_cm(length, unit) == expected


def test_aggregate_totals_with_discount():
    rows = [
        {"code": "sub_total", "value": 500},
        {"code": "shipping", "value": 20},
        {"code": "coupon", "value": -50},
        {"code": "voucher", "value": -10},
        {"code": "total", "value": 460},
    ]
    assert aggregate_order_totals(rows) == {
        "subtotal": 500.0,
        "shipping_total": 20.0,
        "discount_total": 60.0,
        "total": 460.0,
    }


def test_free_shipping_threshold():
    assert shipping_cost(25, 300, 350) == 0.0
    assert shipping_cost(25, 300, 299) == 25.0
    assert shipping_cost(25, 0, 999) == 25.0


def test_status_filter_mapping():
    status_map = {"complete": 5, "pending": 1, "processing": 2}
    assert status_names_to_ids("Complete,pending", status_map) == [5, 1]
    assert status_names_to_ids("Unknown", status_map) == []
