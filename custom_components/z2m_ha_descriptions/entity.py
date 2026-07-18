"""Sensor entity exposing the Z2M user description."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ENTITY_UNIQUE_ID_PREFIX
from .mapper import ieee_to_device_identifiers

if TYPE_CHECKING:
    from .coordinator import Z2mDescriptionsCoordinator


class Z2mDescriptionSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic sensor with the Z2M top-level device description."""

    _attr_has_entity_name = True
    _attr_name = "Description"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:label-outline"
    _attr_native_unit_of_measurement = None

    def __init__(
        self,
        coordinator: Z2mDescriptionsCoordinator,
        ieee: str,
        description: str,
        device_id: str,
    ) -> None:
        """Initialize the description sensor."""
        super().__init__(coordinator)
        self._ieee = ieee
        self._device_id = device_id
        self._attr_unique_id = f"{ENTITY_UNIQUE_ID_PREFIX}{ieee.lower()}"
        self._attr_native_value = description

    @property
    def device_info(self) -> DeviceInfo:
        """Attach to the existing Z2M MQTT device."""
        return DeviceInfo(identifiers=ieee_to_device_identifiers(self._ieee))

    def update_description(self, description: str) -> None:
        """Update the sensor state when the Z2M description changes."""
        self._attr_native_value = description
        self.async_write_ha_state()
