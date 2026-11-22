"""In-memory Europarcel orders filters (mirrors API query params)."""

from __future__ import annotations


def filter_by_status_ids(orders: list[dict], status_ids: list[int]) -> list[dict]:
    allowed = set(status_ids)
    return [o for o in orders if o.get("status_id") in allowed]


def filter_order_id_after(orders: list[dict], after_id: int) -> list[dict]:
    return [o for o in orders if int(o["id"]) > after_id]


def filter_date_after(orders: list[dict], date_after: str) -> list[dict]:
    return [o for o in orders if o.get("date_created", "") > date_after]
