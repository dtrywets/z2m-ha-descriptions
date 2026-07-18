"""Tests for bridge/devices payload parsing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.z2m_ha_descriptions.mapper import parse_bridge_devices_payload

FIXTURES = Path(__file__).parent / "fixtures" / "bridge_devices.json"


def test_parse_fixture_payload() -> None:
    """Parse the sample bridge/devices JSON array."""
    payload = FIXTURES.read_bytes()
    devices = parse_bridge_devices_payload(payload)

    assert len(devices) == 3
    assert devices[0]["ieee_address"] == "0xa4c138df78859a58"
    assert devices[0]["description"] == "KG Büro - Regal"
    assert devices[1]["description"] == "Whirlpool"


def test_parse_string_payload() -> None:
    """Accept UTF-8 string payloads."""
    payload = json.dumps([{"ieee_address": "0xabc", "type": "EndDevice"}])
    devices = parse_bridge_devices_payload(payload)
    assert devices[0]["ieee_address"] == "0xabc"


def test_parse_rejects_non_array_payload() -> None:
    """Reject payloads that are not JSON arrays."""
    with pytest.raises(ValueError, match="JSON array"):
        parse_bridge_devices_payload('{"ieee_address": "0xabc"}')
