"""Tests for ieee mapping and description extraction."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.z2m_ha_descriptions.mapper import (
    extract_device_description,
    ieee_to_device_identifiers,
    map_bridge_devices_to_descriptions,
    should_skip_device,
)

FIXTURES = Path(__file__).parent / "fixtures" / "bridge_devices.json"


def test_ieee_to_device_identifiers() -> None:
    """Map ieee to the Z2M MQTT device identifier used by HA."""
    assert ieee_to_device_identifiers("0xa4c138df78859a58") == {
        ("mqtt", "zigbee2mqtt_0xa4c138df78859a58")
    }


def test_should_skip_coordinator_and_bridge() -> None:
    """Skip bridge and coordinator entries."""
    assert should_skip_device({"type": "Coordinator"}) is True
    assert should_skip_device({"type": "Bridge"}) is True
    assert should_skip_device({"type": "EndDevice"}) is False


def test_extract_uses_top_level_description_only() -> None:
    """Use top-level description, not definition.description."""
    device = {
        "ieee_address": "0xa4c138df78859a58",
        "type": "EndDevice",
        "description": "KG Büro - Regal",
        "definition": {"description": "Temperature and humidity sensor"},
    }
    result = extract_device_description(device, sync_empty=False)
    assert result == ("0xa4c138df78859a58", "KG Büro - Regal")


def test_extract_skips_empty_without_sync_empty() -> None:
    """Skip devices without a user description when sync_empty is false."""
    device = {
        "ieee_address": "0xa4c138df78859a58",
        "type": "EndDevice",
        "description": "",
        "definition": {"description": "Product text"},
    }
    assert extract_device_description(device, sync_empty=False) is None
    assert extract_device_description(device, sync_empty=True) == (
        "0xa4c138df78859a58",
        "",
    )


def test_map_fixture_devices() -> None:
    """Map the sample bridge/devices fixture to expected descriptions."""
    devices = json.loads(FIXTURES.read_text(encoding="utf-8"))
    mapped = map_bridge_devices_to_descriptions(devices, sync_empty=False)

    assert mapped == {
        "0xa4c138df78859a58": "KG Büro - Regal",
        "0xa4c138bcdad2d1d0": "Whirlpool",
    }
    assert "0x00124b002226cccc" not in mapped
