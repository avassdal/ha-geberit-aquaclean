"""Base entity for Geberit AquaClean integration."""
from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GeberitAquaCleanCoordinator
from .const import DOMAIN


class GeberitAquaCleanEntity(CoordinatorEntity):
    """Base entity for Geberit AquaClean devices."""

    def __init__(self, coordinator: GeberitAquaCleanCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"geberit_aquaclean_{key}_{coordinator.client.mac_address.replace(':', '')}"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success 
            and self.coordinator.client.device_state is not None 
            and self.coordinator.client.device_state.connected
        )

    @property
    def device_info(self):
        """Return device information."""
        device_data = self.coordinator.client.device_state
        return {
            "identifiers": {(DOMAIN, self.coordinator.client.mac_address)},
            "name": getattr(device_data, "description", "Geberit AquaClean") if device_data else "Geberit AquaClean",
            "manufacturer": "Geberit",
            "model": "AquaClean",
            "sw_version": getattr(device_data, "firmware_version", "Unknown") if device_data else "Unknown",
            "serial_number": getattr(device_data, "serial_number", None) if device_data else None,
            "hw_version": getattr(device_data, "sap_number", None) if device_data else None,
        }
