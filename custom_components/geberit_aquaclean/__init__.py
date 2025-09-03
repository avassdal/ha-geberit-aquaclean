"""Geberit AquaClean integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.const import CONF_MAC_ADDRESS
from homeassistant.core import HomeAssistant, CoreState, callback
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.active_update_coordinator import ActiveBluetoothDataUpdateCoordinator

from .const import DOMAIN
from .geberit_client import GeberitAquaCleanClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SWITCH, Platform.NUMBER, Platform.SENSOR]

SCAN_INTERVAL = timedelta(seconds=15)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Geberit AquaClean from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    mac_address = entry.data[CONF_MAC_ADDRESS]
    
    # Check if Bluetooth scanners are available (best practice)
    scanner_count = bluetooth.async_scanner_count(hass, connectable=True)
    if scanner_count == 0:
        _LOGGER.error("No connectable Bluetooth adapters found for %s", mac_address)
        return False
    
    # Initialize the client with shared scanner (best practice)
    scanner = bluetooth.async_get_scanner(hass)
    client = GeberitAquaCleanClient(mac_address, hass, scanner)
    
    # Get BLE device for coordinator
    ble_device = bluetooth.async_ble_device_from_address(
        hass, mac_address.upper(), connectable=True
    )
    if not ble_device:
        _LOGGER.error("Device %s not found in Bluetooth registry", mac_address)
        return False
    
    # Create ActiveBluetoothCoordinator (best practice for devices needing active connections)
    coordinator = GeberitActiveBluetoothCoordinator(hass, client, ble_device)
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Track device unavailability (best practice)
    entry.async_on_unload(
        bluetooth.async_track_unavailable(
            hass, coordinator._async_handle_unavailable, mac_address, connectable=True
        )
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN].pop(entry.entry_id)
        if client := data.get("client"):
            await client.disconnect()

    return unload_ok


class GeberitActiveBluetoothCoordinator(ActiveBluetoothDataUpdateCoordinator):
    """Active Bluetooth coordinator for Geberit AquaClean devices."""

    def __init__(self, hass: HomeAssistant, client: GeberitAquaCleanClient, ble_device):
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            address=ble_device.address,
            needs_poll_method=self._needs_poll,
            poll_method=self._async_update,
            mode=bluetooth.BluetoothScanningMode.ACTIVE,
            connectable=True,
        )
        self.client = client
        self.ble_device = ble_device

    @callback
    def _needs_poll(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        seconds_since_last_poll: float | None,
    ) -> bool:
        """Check if we need to poll the device."""
        return (
            self.hass.state == CoreState.running
            and (seconds_since_last_poll is None or seconds_since_last_poll >= SCAN_INTERVAL.total_seconds())
            and bool(
                bluetooth.async_ble_device_from_address(
                    self.hass, service_info.device.address, connectable=True
                )
            )
        )

    async def _async_update(self, service_info: bluetooth.BluetoothServiceInfoBleak):
        """Poll the device for data."""
        try:
            return await self.client.get_device_state()
        except Exception as exception:
            raise UpdateFailed(f"Error communicating with API: {exception}")

    @callback
    def _async_handle_unavailable(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Handle the device going unavailable."""
        _LOGGER.warning("Device %s is unavailable", service_info.address)
        # Mark device as unavailable
        if hasattr(self.client, '_device_state'):
            self.client._device_state.connected = False

    @callback
    def _async_handle_bluetooth_event(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle a Bluetooth event (advertisement received)."""
        # For Geberit devices, we primarily use active connections
        # but we can track availability through advertisements
        if change == bluetooth.BluetoothChange.ADVERTISEMENT:
            _LOGGER.debug("Advertisement from %s: RSSI %s", service_info.address, service_info.rssi)