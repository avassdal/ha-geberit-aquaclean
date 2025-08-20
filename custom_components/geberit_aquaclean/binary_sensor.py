"""Binary sensor platform for Geberit AquaClean."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    entities = [
        GeberitBinarySensor(coordinator, "user_is_sitting", "User Sitting", BinarySensorDeviceClass.OCCUPANCY),
        GeberitBinarySensor(coordinator, "anal_shower_running", "Anal Shower", BinarySensorDeviceClass.RUNNING),
        GeberitBinarySensor(coordinator, "lady_shower_running", "Lady Shower", BinarySensorDeviceClass.RUNNING),
        GeberitBinarySensor(coordinator, "dryer_running", "Dryer", BinarySensorDeviceClass.RUNNING),
        GeberitBinarySensor(coordinator, "connected", "Connection", BinarySensorDeviceClass.CONNECTIVITY),
    ]
    
    async_add_entities(entities)


class GeberitBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Geberit AquaClean binary sensor."""

    def __init__(self, coordinator, sensor_key: str, name: str, device_class: BinarySensorDeviceClass):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._sensor_key = sensor_key
        self._attr_name = f"Geberit AquaClean {name}"
        self._attr_unique_id = f"geberit_aquaclean_{sensor_key}_{coordinator.client.mac_address.replace(':', '')}"
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if self.coordinator.data is None:
            return None
        return getattr(self.coordinator.data, self._sensor_key, False)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.client.mac_address)},
            "name": "Geberit AquaClean",
            "manufacturer": "Geberit",
            "model": "AquaClean",
            "sw_version": getattr(self.coordinator.data, "sap_number", "Unknown"),
        }
