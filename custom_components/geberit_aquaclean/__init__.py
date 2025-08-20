"""The Geberit AquaClean integration."""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_MAC, Platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .geberit_client import GeberitAquaCleanClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SWITCH]

SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Geberit AquaClean from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    mac_address = entry.data[CONF_MAC]
    
    # Initialize the client
    client = GeberitAquaCleanClient(mac_address)
    
    # Create coordinator
    coordinator = GeberitDataUpdateCoordinator(hass, client)
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN].pop(entry.entry_id)
        if client := data.get("client"):
            await client.disconnect()

    return unload_ok


class GeberitDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Geberit AquaClean device."""

    def __init__(self, hass: HomeAssistant, client: GeberitAquaCleanClient):
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.client.get_device_state()
        except Exception as exception:
            raise UpdateFailed(f"Error communicating with API: {exception}")