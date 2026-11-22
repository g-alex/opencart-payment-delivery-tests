"""Order-status mapping for Netopia/Mobilpay payment callbacks."""

import re
from pathlib import Path

import pytest

from rules import MOBILPAY_ACTION_STATUS_KEYS, mobilpay_status_config_key

# Optional local shop checkout (skipped in portfolio-only clone)
MOBILPAY_CTRL = (
    Path(__file__).resolve().parents[2]
    / "www"
    / "catalog"
    / "controller"
    / "extension"
    / "payment"
    / "mobilpay.php"
)


@pytest.mark.parametrize(
    "action,key",
    list(MOBILPAY_ACTION_STATUS_KEYS.items()),
)
def test_action_maps_to_config_key(action, key):
    assert mobilpay_status_config_key(action) == key


def test_unknown_action_has_no_mapping():
    assert mobilpay_status_config_key("fraud") is None


def test_callback_source_uses_configured_statuses():
    """Guard: production callback still wires each action to config status ids."""
    if not MOBILPAY_CTRL.is_file():
        pytest.skip("shop source not bundled in portfolio checkout")
    src = MOBILPAY_CTRL.read_text(encoding="utf-8", errors="ignore")
    for action, key in MOBILPAY_ACTION_STATUS_KEYS.items():
        assert f"case '{action}'" in src or f'case "{action}"' in src
        assert key in src


def test_confirmed_updates_history_not_silent():
    if not MOBILPAY_CTRL.is_file():
        pytest.skip("shop source not bundled in portfolio checkout")
    src = MOBILPAY_CTRL.read_text(encoding="utf-8", errors="ignore")
    # confirmed path must push order history (paid -> shippable for Europarcel sync)
    confirmed_block = re.search(
        r"case\s+'confirmed':(.*?)break;",
        src,
        re.S,
    )
    assert confirmed_block, "confirmed case missing"
    assert "addOrderHistory" in confirmed_block.group(1)
