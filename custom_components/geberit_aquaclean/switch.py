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
        GeberitRearWashSwitch(coordinator, client),
        GeberitFrontWashSwitch(coordinator, client),
        GeberitDryerSwitch(coordinator, client),
    ]
    
    async_add_entities(entities)


class GeberitLidSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Geberit AquaClean lid switch."""

    def __init__(self, coordinator, client):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._client = client
        self._attr_name = "Lid"
        self._attr_unique_id = f"geberit_aquaclean_lid_{coordinator.client.mac_address.replace(':', '')}"
        self._attr_icon = "mdi:toilet"

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if self.coordinator.data is None:
            return None
        return getattr(self.coordinator.data, "lid_open", False)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success 
            and self.coordinator.data is not None 
            and getattr(self.coordinator.data, "connected", False)
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the lid switch on (open lid)."""
        if self.coordinator.data and not getattr(self.coordinator.data, "lid_open", False):
            await self._toggle_lid()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the lid switch off (close lid)."""
        if self.coordinator.data and getattr(self.coordinator.data, "lid_open", False):
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


class GeberitRearWashSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Geberit AquaClean rear wash switch."""

    def __init__(self, coordinator, client):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._client = client
        self._attr_name = "Rear Wash"
        self._attr_unique_id = f"geberit_aquaclean_rear_wash_{coordinator.client.mac_address.replace(':', '')}"
        self._attr_icon = "mdi:shower"

    @property
    def is_on(self) -> bool | None:
        """Return true if rear wash is running."""
        if self.coordinator.data is None:
            return None
        return getattr(self.coordinator.data, "anal_shower_running", False)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success 
            and self.coordinator.data is not None 
            and getattr(self.coordinator.data, "connected", False)
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start rear wash."""
        try:
            success = await self._client.start_rear_wash()
            if success:
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to start rear wash")
        except Exception as e:
            _LOGGER.error("Error starting rear wash: %s", e)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop rear wash."""
        try:
            success = await self._client.stop_rear_wash()
            if success:
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to stop rear wash")
        except Exception as e:
            _LOGGER.error("Error stopping rear wash: %s", e)

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


class GeberitFrontWashSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Geberit AquaClean front wash switch."""

    def __init__(self, coordinator, client):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._client = client
        self._attr_name = "Front Wash"
        self._attr_unique_id = f"geberit_aquaclean_front_wash_{coordinator.client.mac_address.replace(':', '')}"
        self._attr_icon = "mdi:shower-head"

    @property
    def is_on(self) -> bool | None:
        """Return true if front wash is running."""
        if self.coordinator.data is None:
            return None
        return getattr(self.coordinator.data, "lady_shower_running", False)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success 
            and self.coordinator.data is not None 
            and getattr(self.coordinator.data, "connected", False)
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start front wash."""
        try:
            success = await self._client.start_front_wash()
            if success:
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to start front wash")
        except Exception as e:
            _LOGGER.error("Error starting front wash: %s", e)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop front wash."""
        try:
            success = await self._client.stop_front_wash()
            if success:
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to stop front wash")
        except Exception as e:
            _LOGGER.error("Error stopping front wash: %s", e)

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


class GeberitDryerSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Geberit AquaClean dryer switch."""

    def __init__(self, coordinator, client):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._client = client
        self._attr_name = "Air Dry"
        self._attr_unique_id = f"geberit_aquaclean_dryer_{coordinator.client.mac_address.replace(':', '')}"
        self._attr_icon = "mdi:air-purifier"

    @property
    def is_on(self) -> bool | None:
        """Return true if dryer is running."""
        if self.coordinator.data is None:
            return None
        return getattr(self.coordinator.data, "dryer_running", False)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success 
            and self.coordinator.data is not None 
            and getattr(self.coordinator.data, "connected", False)
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start dryer."""
        try:
            success = await self._client.start_dryer()
            if success:
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to start dryer")
        except Exception as e:
            _LOGGER.error("Error starting dryer: %s", e)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop dryer."""
        try:
            success = await self._client.stop_dryer()
            if success:
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to stop dryer")
        except Exception as e:
            _LOGGER.error("Error stopping dryer: %s", e)

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
