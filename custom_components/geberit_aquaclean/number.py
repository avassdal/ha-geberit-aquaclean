"""Number entities for Geberit AquaClean integration."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import GeberitAquaCleanEntity

_LOGGER = logging.getLogger(__name__)

NUMBERS: tuple[NumberEntityDescription, ...] = (
    NumberEntityDescription(
        key="water_temperature",
        name="Water Temperature",
        icon="mdi:thermometer",
        native_min_value=34,
        native_max_value=40,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    NumberEntityDescription(
        key="spray_intensity", 
        name="Spray Intensity",
        icon="mdi:water-pump",
        native_min_value=1,
        native_max_value=5,
        native_step=1,
    ),
    NumberEntityDescription(
        key="spray_position",
        name="Spray Position", 
        icon="mdi:crosshairs-gps",
        native_min_value=1,
        native_max_value=5,
        native_step=1,
    ),
    NumberEntityDescription(
        key="active_user_profile",
        name="Active User Profile",
        icon="mdi:account-circle",
        native_min_value=1,
        native_max_value=4,
        native_step=1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Geberit AquaClean number entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]["client"]

    entities = [
        GeberitAquaCleanNumberEntity(coordinator, client, description) 
        for description in NUMBERS
    ]

    async_add_entities(entities)


class GeberitAquaCleanNumberEntity(GeberitAquaCleanEntity, NumberEntity):
    """Representation of a Geberit AquaClean number entity."""

    def __init__(
        self,
        coordinator,
        client,
        description: NumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, description.key)
        self._client = client
        self.entity_description = description
        self._attr_name = f"{description.name}"

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if self.coordinator.data is None:
            return None
        return getattr(self.coordinator.data, self.entity_description.key, None)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        try:
            # Convert to int for our parameters
            int_value = int(value)
            
            if self.entity_description.key == "water_temperature":
                await self._client.set_water_temperature(int_value)
            elif self.entity_description.key == "spray_intensity":
                await self._client.set_spray_intensity(int_value)
            elif self.entity_description.key == "spray_position":
                await self._client.set_spray_position(int_value)
            elif self.entity_description.key == "active_user_profile":
                await self._client.set_user_profile(int_value)
                
            # Trigger a coordinator refresh to update the state
            await self.coordinator.async_request_refresh()
            
        except Exception as ex:
            _LOGGER.error("Failed to set %s to %s: %s", self.entity_description.key, value, ex)
