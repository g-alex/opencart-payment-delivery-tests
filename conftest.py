"""Pytest fixtures for OpenCart payment/delivery test suite.

Secrets come only from environment variables — never from config.php / .env files
checked into git.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def db_settings() -> dict | None:
    host = os.getenv("MOP_DB_HOST")
    user = os.getenv("MOP_DB_USER")
    password = os.getenv("MOP_DB_PASSWORD")
    database = os.getenv("MOP_DB_NAME")
    port = int(os.getenv("MOP_DB_PORT") or "3306")
    prefix = os.getenv("MOP_DB_PREFIX") or "oc_"
    if not all([host, user, database, password is not None]):
        return None
    return {
        "host": host,
        "user": user,
        "password": password or "",
        "database": database,
        "port": port,
        "prefix": prefix,
    }


@pytest.fixture(scope="session")
def db_conn(db_settings):
    if not db_settings:
        pytest.skip("Set MOP_DB_HOST/USER/PASSWORD/NAME to run SQL checks")
    try:
        import pymysql
    except ImportError:
        pytest.skip("pymysql not installed")
    try:
        conn = pymysql.connect(
            host=db_settings["host"],
            user=db_settings["user"],
            password=db_settings["password"],
            database=db_settings["database"],
            port=db_settings["port"],
            connect_timeout=8,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except Exception as exc:  # noqa: BLE001 — skip cleanly when remote DB blocked
        pytest.skip(f"DB unreachable: {exc}")
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def api_base() -> str:
    base = os.getenv("MOP_API_BASE", "").rstrip("/")
    if not base:
        pytest.skip("Set MOP_API_BASE to run live API checks")
    return base


@pytest.fixture(scope="session")
def api_key() -> str | None:
    return os.getenv("EUROPARCEL_API_KEY") or None


@pytest.fixture(scope="session")
def sample_orders_payload() -> dict:
    path = FIXTURES / "orders_sample.json"
    return json.loads(path.read_text(encoding="utf-8"))
