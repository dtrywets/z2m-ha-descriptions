"""Sensor platform for Z2M HA Descriptions."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Z2mDescriptionsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up description sensors from a config entry."""
    coordinator: Z2mDescriptionsCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    coordinator.set_entity_callback(async_add_entities)

    if coordinator._last_payload is not None:
        await coordinator._async_process_last_payload()
