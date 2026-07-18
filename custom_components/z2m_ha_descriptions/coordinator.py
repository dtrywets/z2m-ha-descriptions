"""Coordinator for syncing Z2M device descriptions via MQTT."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.components import mqtt
from homeassistant.components.mqtt.models import ReceiveMessage
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.device_registry import EventDeviceRegistryUpdatedData
from homeassistant.helpers.event import async_track_device_registry_updated_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ATTR_LAST_SYNC,
    ATTR_SYNCED_COUNT,
    ATTR_UNMATCHED_COUNT,
    CONF_BASE_TOPIC,
    CONF_SYNC_EMPTY,
    DEBOUNCE_COOLDOWN,
    DEFAULT_BASE_TOPIC,
    DOMAIN,
    TOPIC_BRIDGE_DEVICES_SUFFIX,
    TOPIC_BRIDGE_REQUEST_DEVICES_SUFFIX,
)
from .mapper import ieee_to_device_identifiers, map_bridge_devices_to_descriptions, parse_bridge_devices_payload

if TYPE_CHECKING:
    from .entity import Z2mDescriptionSensor

_LOGGER = logging.getLogger(__name__)


class Z2mDescriptionsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manage MQTT subscription and description entity lifecycle."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )
        self.entry = entry
        self._base_topic = entry.options.get(CONF_BASE_TOPIC, DEFAULT_BASE_TOPIC)
        self._sync_empty = entry.options.get(CONF_SYNC_EMPTY, False)

        self._entities: dict[str, Z2mDescriptionSensor] = {}
        self._pending: dict[str, str] = {}
        self._async_add_entities: Callable[[list[Z2mDescriptionSensor]], None] | None = None
        self._unsub_mqtt: Callable[[], None] | None = None
        self._remove_device_listener: Callable[[], None] | None = None
        self._last_payload: bytes | None = None

        self.synced_count = 0
        self.unmatched_count = 0
        self.last_sync: datetime | None = None

        self._debouncer = Debouncer(
            hass,
            logger=_LOGGER,
            cooldown=DEBOUNCE_COOLDOWN,
            immediate=False,
            function=self._async_process_last_payload,
        )

    @property
    def base_topic(self) -> str:
        """Return the configured MQTT base topic."""
        return self._base_topic

    @property
    def devices_topic(self) -> str:
        """Return the bridge/devices MQTT topic."""
        return f"{self._base_topic}/{TOPIC_BRIDGE_DEVICES_SUFFIX}"

    @property
    def request_devices_topic(self) -> str:
        """Return the bridge/request/devices MQTT topic."""
        return f"{self._base_topic}/{TOPIC_BRIDGE_REQUEST_DEVICES_SUFFIX}"

    def set_entity_callback(
        self, async_add_entities: Callable[[list[Z2mDescriptionSensor]], None]
    ) -> None:
        """Register the platform callback used to add entities."""
        self._async_add_entities = async_add_entities

    async def async_setup(self) -> None:
        """Subscribe to MQTT and device registry updates."""
        self._unsub_mqtt = await mqtt.async_subscribe(
            self.hass,
            self.devices_topic,
            self._async_mqtt_message,
            qos=0,
        )
        self._remove_device_listener = async_track_device_registry_updated_event(
            self.hass, self._async_device_registry_updated
        )

    async def async_shutdown(self) -> None:
        """Unsubscribe listeners."""
        if self._unsub_mqtt is not None:
            self._unsub_mqtt()
            self._unsub_mqtt = None
        if self._remove_device_listener is not None:
            self._remove_device_listener()
            self._remove_device_listener = None
        await self._debouncer.async_shutdown()

    @callback
    def _async_mqtt_message(self, msg: ReceiveMessage) -> None:
        """Handle incoming bridge/devices MQTT messages."""
        self._last_payload = msg.payload
        self.hass.async_create_task(self._debouncer.async_call())

    @callback
    def _async_device_registry_updated(
        self, event: Event[EventDeviceRegistryUpdatedData]
    ) -> None:
        """Retry pending devices when the device registry changes."""
        if self._pending:
            self.hass.async_create_task(self._async_retry_pending())

    async def _async_retry_pending(self) -> None:
        """Try to sync descriptions that were waiting for HA devices."""
        matched = 0
        for ieee, description in list(self._pending.items()):
            if await self._async_sync_description(ieee, description):
                matched += 1

        if matched:
            self.synced_count += matched
            self.unmatched_count = max(0, self.unmatched_count - matched)
            self.last_sync = datetime.now()
            await self.async_request_refresh()

    async def _async_process_last_payload(self) -> None:
        """Process the most recently received bridge/devices payload."""
        if self._last_payload is None:
            return
        try:
            await self._async_apply_payload(self._last_payload)
        except Exception as err:
            raise UpdateFailed(f"Failed to process bridge/devices payload: {err}") from err

    async def _async_apply_payload(self, payload: bytes | str) -> None:
        """Parse payload and sync description entities."""
        devices = parse_bridge_devices_payload(payload)
        descriptions = map_bridge_devices_to_descriptions(
            devices, sync_empty=self._sync_empty
        )

        synced = 0
        unmatched = 0
        seen_ieees: set[str] = set()

        for ieee, description in descriptions.items():
            seen_ieees.add(ieee)
            matched = await self._async_sync_description(ieee, description)
            if matched:
                synced += 1
            else:
                unmatched += 1
                self._pending[ieee] = description

        for ieee in list(self._pending):
            if ieee not in seen_ieees:
                self._pending.pop(ieee, None)

        if not self._sync_empty:
            for ieee in list(self._entities):
                if ieee not in seen_ieees:
                    await self._async_remove_entity(ieee)

        self.synced_count = synced
        self.unmatched_count = unmatched
        self.last_sync = datetime.now()
        await self.async_request_refresh()

    async def _async_sync_description(self, ieee: str, description: str) -> bool:
        """Create or update a description entity for the given ieee."""
        from .entity import Z2mDescriptionSensor

        device = self._async_find_ha_device(ieee)
        if device is None:
            return False

        self._pending.pop(ieee, None)

        if ieee in self._entities:
            self._entities[ieee].update_description(description)
            return True

        entity = Z2mDescriptionSensor(self, ieee, description, device.id)
        self._entities[ieee] = entity
        if self._async_add_entities is not None:
            self._async_add_entities([entity])
        return True

    def _async_find_ha_device(self, ieee: str) -> dr.DeviceEntry | None:
        """Find the Z2M MQTT device in the HA device registry."""
        device_registry = dr.async_get(self.hass)
        return device_registry.async_get_device(identifiers=ieee_to_device_identifiers(ieee))

    async def _async_remove_entity(self, ieee: str) -> None:
        """Remove a description entity."""
        entity = self._entities.pop(ieee, None)
        if entity is not None:
            await entity.async_remove()

    async def async_sync_now(self) -> None:
        """Request a fresh bridge/devices payload and reprocess the last message."""
        await mqtt.async_publish(
            self.hass,
            self.request_devices_topic,
            "",
            qos=0,
            retain=False,
        )
        await asyncio.sleep(0.5)
        await self._async_process_last_payload()

    async def async_clear(self) -> None:
        """Remove all description entities managed by this integration."""
        for ieee in list(self._entities):
            await self._async_remove_entity(ieee)
        self._pending.clear()
        self.synced_count = 0
        self.unmatched_count = 0
        self.last_sync = datetime.now()
        await self.async_request_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        """Return diagnostic data for listeners."""
        return {
            ATTR_SYNCED_COUNT: self.synced_count,
            ATTR_UNMATCHED_COUNT: self.unmatched_count,
            ATTR_LAST_SYNC: self.last_sync.isoformat() if self.last_sync else None,
        }
