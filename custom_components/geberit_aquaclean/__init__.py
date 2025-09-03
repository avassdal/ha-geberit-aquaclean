"""Geberit AquaClean integration."""
import asyncio
import contextlib
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.const import CONF_MAC_ADDRESS
from homeassistant.core import HomeAssistant, CoreState, callback
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady
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
        raise ConfigEntryNotReady(f"Could not find Geberit AquaClean device with address {mac_address}")
    
    # Create ActiveBluetoothCoordinator (best practice for devices needing active connections)
    coordinator = GeberitActiveBluetoothCoordinator(hass, client, ble_device, entry.title, entry.unique_id)
    entry.async_on_unload(coordinator.async_start())
    
    # Wait for device to be ready
    if not await coordinator.async_wait_ready():
        raise ConfigEntryNotReady(f"{mac_address} is not advertising state")
    
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    # Set up platforms  
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Add update listener for options changes
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN].pop(entry.entry_id)
        if client := data.get("client"):
            await client.disconnect()

    return unload_ok


class GeberitActiveBluetoothCoordinator(ActiveBluetoothDataUpdateCoordinator):
    """Active Bluetooth coordinator for Geberit AquaClean devices."""

    def __init__(self, hass: HomeAssistant, client: GeberitAquaCleanClient, ble_device, device_name: str, base_unique_id: str):
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
        self.device_name = device_name
        self.base_unique_id = base_unique_id
        self._ready_event = asyncio.Event()
        self._was_unavailable = True

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

    async def async_wait_ready(self) -> bool:
        """Wait for the device to be ready."""
        with contextlib.suppress(asyncio.TimeoutError):
            async with asyncio.timeout(30.0):  # 30 second timeout for device readiness
                await self._ready_event.wait()
                return True
        return False

    @callback
    def _async_handle_unavailable(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Handle the device going unavailable."""
        super()._async_handle_unavailable(service_info)
        _LOGGER.warning("Device %s is unavailable", service_info.address)
        self._was_unavailable = True
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
        self.ble_device = service_info.device
        _LOGGER.debug("Bluetooth event from %s: %s", service_info.address, change)
        self._ready_event.set()

        if not self._was_unavailable:
            return

        self._was_unavailable = False
        _LOGGER.info("Device %s is now available (RSSI: %s)", service_info.address, service_info.rssi)
        super()._async_handle_bluetooth_event(service_info, change)