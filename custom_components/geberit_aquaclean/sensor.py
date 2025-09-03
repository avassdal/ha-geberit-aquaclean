"""Sensor entities for Geberit AquaClean integration."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, UnitOfPressure
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import GeberitAquaCleanEntity

_LOGGER = logging.getLogger(__name__)

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="power_consumption",
        name="Power Consumption",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="water_pressure",
        name="Water Pressure",
        icon="mdi:water-pump",
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="active_user_profile",
        name="Active User Profile",
        icon="mdi:account-circle",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Geberit AquaClean sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        GeberitAquaCleanSensorEntity(coordinator, description) 
        for description in SENSORS
    ]

    async_add_entities(entities)


class GeberitAquaCleanSensorEntity(GeberitAquaCleanEntity, SensorEntity):
    """Representation of a Geberit AquaClean sensor entity."""

    def __init__(
        self,
        coordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_name = f"{description.name}"

    @property
    def native_value(self) -> float | str | None:
        """Return the current value."""
        if self.coordinator.data is None:
            return None
        return getattr(self.coordinator.data, self.entity_description.key, None)
