"""Switch platform for Geberit AquaClean."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][config_entry.entry_id]["client"]
    
    entities = [
        GeberitLidSwitch(coordinator, client),
    ]
    
    async_add_entities(entities)


class GeberitLidSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Geberit AquaClean lid switch."""

    def __init__(self, coordinator, client):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._client = client
        self._attr_name = "Geberit AquaClean Lid"
        self._attr_unique_id = f"geberit_aquaclean_lid_{coordinator.client.mac_address.replace(':', '')}"

    @property
    def is_on(self) -> bool | None:
        """Return true if the lid is open."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.lid_position

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success 
            and self.coordinator.data is not None 
            and self.coordinator.data.connected
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the lid switch on (open lid)."""
        if self.coordinator.data and not self.coordinator.data.lid_position:
            await self._toggle_lid()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the lid switch off (close lid)."""
        if self.coordinator.data and self.coordinator.data.lid_position:
            await self._toggle_lid()

    async def _toggle_lid(self) -> None:
        """Toggle the lid position."""
        try:
            success = await self._client.toggle_lid_position()
            if success:
                # Request an immediate update
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to toggle lid position")
        except Exception as e:
            _LOGGER.error("Error toggling lid position: %s", e)

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.client.mac_address)},
            "name": "Geberit AquaClean",
            "manufacturer": "Geberit",
            "model": "AquaClean",
            "sw_version": getattr(self.coordinator.data, "sap_number", "Unknown") if self.coordinator.data else "Unknown",
        }
