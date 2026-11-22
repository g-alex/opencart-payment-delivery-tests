"""
UI smoke (Playwright) — browse only, NO order create.

Opt-in: MOP_UI_SMOKE=1 and MOP_STORE_URL. Never clicks confirm/pay.
"""

from __future__ import annotations

import os

import pytest

from pages import StorePages

pytestmark = pytest.mark.ui


def _store_url() -> str | None:
    if os.getenv("MOP_UI_SMOKE", "").strip() != "1":
        return None
    return (os.getenv("MOP_STORE_URL") or "").rstrip("/") or None


@pytest.fixture(scope="module")
def store_url():
    url = _store_url()
    if not url:
        pytest.skip("UI smoke disabled. Set MOP_UI_SMOKE=1 and MOP_STORE_URL")
    return url


@pytest.fixture(scope="module")
def store(store_url):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright not installed")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(20000)
        yield StorePages(page, store_url)
        browser.close()


def test_home_page_loads(store):
    store.open_home()
    assert store.title()
    assert store.has_body()


def test_catalog_or_product_list_reachable(store):
    store.open_home()
    if not store.open_first_catalog_link():
        pytest.skip("no catalog/product links found")
    assert store.has_body()


def test_cart_page_opens_without_placing_order(store):
    store.open_cart()
    assert not store.is_confirm_route()
    assert store.looks_like_cart()


def test_checkout_page_reachable_but_not_confirmed(store):
    store.open_checkout()
    assert store.looks_like_checkout()
    # explicitly do not click confirm/pay
