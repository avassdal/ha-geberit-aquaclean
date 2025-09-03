"""Light platform for Geberit AquaClean integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import GeberitAquaCleanEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Geberit AquaClean light entities from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = data["coordinator"]
    
    entities = []
    
    # Add night light entity if feature is available
    if coordinator.client.has_feature("night_light"):
        entities.append(GeberitNightLight(coordinator))
        _LOGGER.info("Added night light entity")
    
    # Add orientation light entity if feature is available (Sela only)
    if coordinator.client.has_feature("orientation_light"):
        entities.append(GeberitOrientationLight(coordinator))
        _LOGGER.info("Added orientation light entity")
    
    if entities:
        async_add_entities(entities, True)


class GeberitNightLight(GeberitAquaCleanEntity, LightEntity):
    """Representation of the Geberit AquaClean night light."""

    _attr_name = "Night Light"
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_icon = "mdi:lightbulb-night"

    def __init__(self, coordinator) -> None:
        """Initialize the night light."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.coordinator.base_unique_id}_night_light"

    @property
    def is_on(self) -> bool:
        """Return true if the night light is on."""
        if not self.coordinator.data:
            return False
        return getattr(self.coordinator.data, 'night_light', False)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the night light (0-255)."""
        if not self.coordinator.data:
            return None
        # Get brightness from device state (0-100) and convert to HA format (0-255)
        device_brightness = getattr(self.coordinator.data, 'night_light_brightness', 0)
        return int((device_brightness / 100.0) * 255) if device_brightness else 0

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the RGB color value."""
        if not self.coordinator.data:
            return None
        
        red = getattr(self.coordinator.data, 'night_light_red', 255)
        green = getattr(self.coordinator.data, 'night_light_green', 255) 
        blue = getattr(self.coordinator.data, 'night_light_blue', 255)
        
        return (red, green, blue)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the night light."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        rgb_color = kwargs.get(ATTR_RGB_COLOR)
        
        try:
            # Turn on the night light
            await self.coordinator.client.set_night_light_state(True)
            
            # Set brightness if provided (convert from 0-255 to 0-100)
            if brightness is not None:
                device_brightness = int((brightness / 255.0) * 100)
                await self.coordinator.client.set_night_light_brightness(device_brightness)
            
            # Set RGB color if provided
            if rgb_color is not None:
                red, green, blue = rgb_color
                await self.coordinator.client.set_night_light_color(red, green, blue)
                
            # Request coordinator update
            await self.coordinator.async_request_refresh()
            
        except Exception as e:
            _LOGGER.error("Failed to turn on night light: %s", e)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the night light."""
        try:
            await self.coordinator.client.set_night_light_state(False)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to turn off night light: %s", e)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class GeberitOrientationLight(GeberitAquaCleanEntity, LightEntity):
    """Representation of the Geberit AquaClean orientation light (Sela only)."""

    _attr_name = "Orientation Light"
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_icon = "mdi:lightbulb-on-outline"

    def __init__(self, coordinator) -> None:
        """Initialize the orientation light."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.coordinator.base_unique_id}_orientation_light"

    @property
    def is_on(self) -> bool:
        """Return true if the orientation light is on."""
        if not self.coordinator.data:
            return False
        return getattr(self.coordinator.data, 'orientation_light', False)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the orientation light (0-255)."""
        if not self.coordinator.data:
            return None
        # Get brightness from device state (0-100) and convert to HA format (0-255)
        device_brightness = getattr(self.coordinator.data, 'orientation_light_brightness', 0)
        return int((device_brightness / 100.0) * 255) if device_brightness else 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the orientation light."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        
        try:
            # Turn on the orientation light
            await self.coordinator.client.set_orientation_light_state(True)
            
            # Set brightness if provided (convert from 0-255 to 0-100)
            if brightness is not None:
                device_brightness = int((brightness / 255.0) * 100)
                await self.coordinator.client.set_orientation_light_brightness(device_brightness)
                
            # Request coordinator update
            await self.coordinator.async_request_refresh()
            
        except Exception as e:
            _LOGGER.error("Failed to turn on orientation light: %s", e)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the orientation light."""
        try:
            await self.coordinator.client.set_orientation_light_state(False)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to turn off orientation light: %s", e)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
