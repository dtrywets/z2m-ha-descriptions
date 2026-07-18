"""The Z2M HA Descriptions integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, SERVICE_CLEAR, SERVICE_SYNC_NOW

if TYPE_CHECKING:
    from .coordinator import Z2mDescriptionsCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Z2M HA Descriptions from a config entry."""
    from .coordinator import Z2mDescriptionsCoordinator

    coordinator = Z2mDescriptionsCoordinator(hass, entry)
    await coordinator.async_setup()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_sync_now(call: ServiceCall) -> None:
        """Handle the sync_now service."""
        for data in hass.data[DOMAIN].values():
            await data["coordinator"].async_sync_now()

    async def handle_clear(call: ServiceCall) -> None:
        """Handle the clear service."""
        for data in hass.data[DOMAIN].values():
            await data["coordinator"].async_clear()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SYNC_NOW,
        handle_sync_now,
        schema=vol.Schema({}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR,
        handle_clear,
        schema=vol.Schema({}),
    )

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unloads(entry, PLATFORMS)

    if unload_ok:
        coordinator: Z2mDescriptionsCoordinator = hass.data[DOMAIN][entry.entry_id][
            "coordinator"
        ]
        await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)

    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_SYNC_NOW)
        hass.services.async_remove(DOMAIN, SERVICE_CLEAR)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: Z2mDescriptionsCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    data = await coordinator.async_get_data()
    return {
        "base_topic": coordinator.base_topic,
        "devices_topic": coordinator.devices_topic,
        "pending_ieees": sorted(coordinator._pending.keys()),
        "entity_count": len(coordinator._entities),
        **data,
    }
