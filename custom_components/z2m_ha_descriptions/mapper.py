"""Pure mapping and parsing helpers without Home Assistant dependencies."""

from __future__ import annotations

import json
from typing import Any

from .const import MQTT_DOMAIN, SKIP_DEVICE_TYPES, Z2M_DEVICE_ID_PREFIX


def ieee_to_device_identifiers(ieee: str) -> set[tuple[str, str]]:
    """Map a Z2M ieee_address to Home Assistant MQTT device identifiers."""
    return {(MQTT_DOMAIN, f"{Z2M_DEVICE_ID_PREFIX}{ieee.lower()}")}


def should_skip_device(device: dict[str, Any]) -> bool:
    """Return True for bridge/coordinator entries that must not be synced."""
    return device.get("type") in SKIP_DEVICE_TYPES


def extract_device_description(
    device: dict[str, Any], *, sync_empty: bool
) -> tuple[str, str] | None:
    """Extract ieee and top-level description from a bridge/devices entry."""
    if should_skip_device(device):
        return None

    ieee = device.get("ieee_address")
    if not isinstance(ieee, str) or not ieee:
        return None

    description = device.get("description")
    if description is None:
        description = ""
    if not isinstance(description, str):
        description = str(description)

    if not sync_empty and not description.strip():
        return None

    return ieee, description


def parse_bridge_devices_payload(payload: bytes | str) -> list[dict[str, Any]]:
    """Parse the retained bridge/devices MQTT payload into device dicts."""
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")

    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("bridge/devices payload must be a JSON array")

    devices: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict):
            devices.append(item)
    return devices


def map_bridge_devices_to_descriptions(
    devices: list[dict[str, Any]], *, sync_empty: bool
) -> dict[str, str]:
    """Map bridge/devices entries to ieee -> description."""
    result: dict[str, str] = {}
    for device in devices:
        extracted = extract_device_description(device, sync_empty=sync_empty)
        if extracted is None:
            continue
        ieee, description = extracted
        result[ieee] = description
    return result
