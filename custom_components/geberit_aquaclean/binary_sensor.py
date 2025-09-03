"""Binary sensor platform for Geberit AquaClean."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass, BinarySensorEntityDescription
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
    
    BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
        BinarySensorEntityDescription(
            key="user_is_sitting",
            name="User Present",
            icon="mdi:account-check",
            device_class=BinarySensorDeviceClass.OCCUPANCY,
        ),
        BinarySensorEntityDescription(
            key="anal_shower_running",
            name="Rear Wash Active",
            icon="mdi:shower",
            device_class=BinarySensorDeviceClass.RUNNING,
        ),
        BinarySensorEntityDescription(
            key="lady_shower_running", 
            name="Front Wash Active",
            icon="mdi:shower-head",
            device_class=BinarySensorDeviceClass.RUNNING,
        ),
        BinarySensorEntityDescription(
            key="dryer_running",
            name="Air Dry Active",
            icon="mdi:air-purifier",
            device_class=BinarySensorDeviceClass.RUNNING,
        ),
        BinarySensorEntityDescription(
            key="lid_position",
            name="Lid Open",
            icon="mdi:toilet",
            device_class=BinarySensorDeviceClass.OPENING,
        ),
        BinarySensorEntityDescription(
            key="descaling_needed",
            name="Descaling Required",
            icon="mdi:alert-circle",
            device_class=BinarySensorDeviceClass.PROBLEM,
        ),
        BinarySensorEntityDescription(
            key="filter_replacement_needed",
            name="Filter Replacement Required",
            icon="mdi:air-filter",
            device_class=BinarySensorDeviceClass.PROBLEM,
        ),
    )
    
    entities = [
        GeberitBinarySensor(coordinator, description) for description in BINARY_SENSORS
    ]
    
    async_add_entities(entities)


class GeberitBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Geberit AquaClean binary sensor."""

    def __init__(self, coordinator, description: BinarySensorEntityDescription):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"geberit_aquaclean_{description.key}_{coordinator.client.mac_address.replace(':', '')}"
        self._attr_device_class = description.device_class
        self._attr_icon = description.icon

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if self.coordinator.data is None:
            return None
        return getattr(self.coordinator.data, self.entity_description.key, False)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.data is not None 
            and getattr(self.coordinator.data, "connected", False)
        )

    @property
    def device_info(self):
        """Return device information."""
        device_data = self.coordinator.data
        return {
            "identifiers": {(DOMAIN, self.coordinator.client.mac_address)},
            "name": getattr(device_data, "description", "Geberit AquaClean") if device_data else "Geberit AquaClean",
            "manufacturer": "Geberit",
            "model": "AquaClean",
            "sw_version": getattr(device_data, "firmware_version", "Unknown") if device_data else "Unknown",
            "serial_number": getattr(device_data, "serial_number", None) if device_data else None,
            "hw_version": getattr(device_data, "sap_number", None) if device_data else None,
        }
