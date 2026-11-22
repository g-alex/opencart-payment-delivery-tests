"""Minimal page objects for OpenCart UI smoke (no order submit)."""

from __future__ import annotations

import re


class StorePages:
    CATALOG_SELECTORS = (
        "a[href*='route=product/category']",
        "a[href*='product/category']",
        "a[href*='product/product']",
        ".product-thumb a",
        ".product-layout a",
    )

    def __init__(self, page, base_url: str) -> None:
        self.page = page
        self.base = base_url.rstrip("/")

    def open_home(self) -> None:
        self.page.goto(self.base)

    def open_cart(self) -> None:
        self.page.goto(f"{self.base}/index.php?route=checkout/cart")

    def open_checkout(self) -> None:
        self.page.goto(f"{self.base}/index.php?route=checkout/checkout")

    def open_first_catalog_link(self) -> bool:
        for sel in self.CATALOG_SELECTORS:
            links = self.page.locator(sel)
            if links.count() == 0:
                continue
            href = links.first.get_attribute("href") or ""
            if href.startswith("http"):
                self.page.goto(href)
                return True
            if href.startswith("/"):
                self.page.goto(f"{self.base}/{href.lstrip('/')}")
                return True
        return False

    def has_body(self) -> bool:
        return self.page.locator("body").count() == 1

    def title(self) -> str:
        return self.page.title() or ""

    def is_confirm_route(self) -> bool:
        return "route=checkout/confirm" in self.page.url

    def looks_like_cart(self) -> bool:
        text = self.page.content().lower()
        return re.search(r"cart|co[sș]|cos|basket|empty|gol", text) is not None

    def looks_like_checkout(self) -> bool:
        url = self.page.url.lower()
        return "checkout" in url or "simplecheckout" in self.page.content().lower()
