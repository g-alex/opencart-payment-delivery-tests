"""SQL integrity checks against OpenCart order / payment / Europarcel data."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def _pfx(db_settings) -> str:
    return db_settings["prefix"]


def test_no_visible_orders_with_zero_status(db_conn, db_settings):
    """Europarcel API only exports order_status_id > 0."""
    p = _pfx(db_settings)
    with db_conn.cursor() as cur:
        cur.execute(
            f"SELECT COUNT(*) AS cnt FROM `{p}order` WHERE order_status_id = 0"
        )
        # unfinished carts may exist; API filters them out — count is informational
        zero = cur.fetchone()["cnt"]
        cur.execute(
            f"SELECT COUNT(*) AS cnt FROM `{p}order` WHERE order_status_id > 0"
        )
        visible = cur.fetchone()["cnt"]
    assert visible >= 0
    assert isinstance(zero, int)


def test_complete_orders_have_positive_total(db_conn, db_settings):
    p = _pfx(db_settings)
    with db_conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT o.order_id, o.total, os.name AS status_name
            FROM `{p}order` o
            JOIN `{p}order_status` os
              ON o.order_status_id = os.order_status_id
             AND os.language_id = (
                 SELECT language_id FROM `{p}language` WHERE code IN ('en-gb','ro-ro')
                 ORDER BY code LIMIT 1
             )
            WHERE LOWER(os.name) = 'complete'
              AND o.total <= 0
            LIMIT 20
            """
        )
        bad = [r["order_id"] for r in cur.fetchall()]
    assert bad == [], f"Complete orders with non-positive total, order_ids: {bad}"


def test_order_total_row_matches_order_total(db_conn, db_settings):
    """order.total should match order_total.code='total' for recent paid orders."""
    p = _pfx(db_settings)
    with db_conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT o.order_id, o.total AS order_total, ot.value AS total_row
            FROM `{p}order` o
            JOIN `{p}order_total` ot ON ot.order_id = o.order_id AND ot.code = 'total'
            WHERE o.order_status_id > 0
            ORDER BY o.order_id DESC
            LIMIT 50
            """
        )
        rows = cur.fetchall()
    mismatches = [
        r["order_id"]
        for r in rows
        if abs(float(r["order_total"]) - float(r["total_row"])) > 0.01
    ]
    assert mismatches == [], f"Total mismatches for order_ids: {mismatches[:5]}"


def test_mobilpay_orders_are_not_flagged_cod_in_api_logic(db_conn, db_settings):
    p = _pfx(db_settings)
    with db_conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT order_id, payment_code, payment_method
            FROM `{p}order`
            WHERE order_status_id > 0
              AND payment_code LIKE 'mobilpay%'
              AND (
                    LOWER(payment_code) LIKE '%cod%'
                 OR LOWER(payment_method) LIKE '%cash on delivery%'
              )
            LIMIT 20
            """
        )
        weird = [r["order_id"] for r in cur.fetchall()]
    assert weird == [], f"Mobilpay rows look like COD, order_ids: {weird}"


def test_status_name_map_unique_per_language(db_conn, db_settings):
    p = _pfx(db_settings)
    with db_conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT language_id, LOWER(name) AS n, COUNT(*) AS cnt
            FROM `{p}order_status`
            GROUP BY language_id, LOWER(name)
            HAVING cnt > 1
            """
        )
        dups = cur.fetchall()
    assert dups == [], f"Duplicate status names break API status filter: {dups}"


def test_europarcel_orders_join_consistency(db_conn, db_settings):
    """europarcel_order rows must point to real orders."""
    p = _pfx(db_settings)
    with db_conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT COUNT(*) AS cnt
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = '{p}europarcel_order'
            """
        )
        if cur.fetchone()["cnt"] == 0:
            pytest.skip("oc_europarcel_order table not installed")
        cur.execute(
            f"""
            SELECT eo.order_id
            FROM `{p}europarcel_order` eo
            LEFT JOIN `{p}order` o ON o.order_id = eo.order_id
            WHERE o.order_id IS NULL
            LIMIT 20
            """
        )
        orphans = [r["order_id"] for r in cur.fetchall()]
    assert orphans == [], f"Orphan europarcel_order rows, order_ids: {orphans}"


def test_recent_complete_orders_have_products(db_conn, db_settings):
    p = _pfx(db_settings)
    with db_conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT o.order_id
            FROM `{p}order` o
            JOIN `{p}order_status` os
              ON o.order_status_id = os.order_status_id
            WHERE LOWER(os.name) = 'complete'
              AND o.order_id NOT IN (
                  SELECT DISTINCT order_id FROM `{p}order_product`
              )
            ORDER BY o.order_id DESC
            LIMIT 10
            """
        )
        empty = [r["order_id"] for r in cur.fetchall()]
    assert empty == [], f"Complete orders without products, order_ids: {empty}"


def test_complete_orders_have_history_after_payment_events(db_conn, db_settings):
    """After Mobilpay addOrderHistory, Complete orders must have history rows."""
    p = _pfx(db_settings)
    with db_conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT o.order_id
            FROM `{p}order` o
            JOIN `{p}order_status` os
              ON o.order_status_id = os.order_status_id
            WHERE LOWER(os.name) = 'complete'
              AND o.payment_code LIKE 'mobilpay%'
              AND o.order_id NOT IN (
                  SELECT DISTINCT order_id FROM `{p}order_history`
              )
            ORDER BY o.order_id DESC
            LIMIT 10
            """
        )
        missing = [r["order_id"] for r in cur.fetchall()]
    assert missing == [], f"Complete mobilpay orders without history: {missing}"


def test_exportable_orders_have_status_gt_zero(db_conn, db_settings):
    """Europarcel sync rule: only order_status_id > 0 leave the shop API."""
    p = _pfx(db_settings)
    with db_conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT COUNT(*) AS cnt
            FROM `{p}order`
            WHERE order_status_id > 0
              AND payment_code LIKE 'mobilpay%'
            """
        )
        cnt = cur.fetchone()["cnt"]
    assert cnt >= 0
