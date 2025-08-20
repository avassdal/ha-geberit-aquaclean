"""Bluetooth scanner for Geberit AquaClean devices."""
import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from bleak import BleakScanner
from bleak.backends.device import BLEDevice

_LOGGER = logging.getLogger(__name__)

# Geberit device identification patterns
GEBERIT_DEVICE_NAMES = [
    "AquaClean",
    "Geberit",
    "AC-",  # Common prefix for AquaClean models
]

# Known Geberit manufacturer IDs or service UUIDs
GEBERIT_SERVICE_UUIDS = [
    "0000180A-0000-1000-8000-00805F9B34FB",  # Device Information Service
]

SCAN_TIMEOUT = 15.0  # seconds


@dataclass
class DiscoveredDevice:
    """Discovered Geberit device."""
    name: str
    address: str
    rssi: int
    local_name: Optional[str] = None
    manufacturer_data: Optional[Dict[int, bytes]] = None
    
    @property
    def display_name(self) -> str:
        """Get display name for the device."""
        if self.local_name:
            return f"{self.local_name} ({self.address})"
        elif self.name:
            return f"{self.name} ({self.address})"
        else:
            return f"Geberit Device ({self.address})"


class GeberitBLEScanner:
    """Scanner for Geberit AquaClean Bluetooth devices."""
    
    def __init__(self):
        """Initialize the scanner."""
        self._discovered_devices: Dict[str, DiscoveredDevice] = {}
        
    async def scan_for_devices(self, timeout: float = SCAN_TIMEOUT) -> List[DiscoveredDevice]:
        """Scan for Geberit AquaClean devices.
        
        Args:
            timeout: Scan timeout in seconds
            
        Returns:
            List of discovered devices
        """
        self._discovered_devices.clear()
        
        _LOGGER.info("Starting Bluetooth scan for Geberit AquaClean devices (timeout: %ss)", timeout)
        
        try:
            # Start scanning
            scanner = BleakScanner(self._device_detection_callback)
            await scanner.start()
            
            # Wait for scan timeout
            await asyncio.sleep(timeout)
            
            # Stop scanning
            await scanner.stop()
            
            devices = list(self._discovered_devices.values())
            _LOGGER.info("Found %d Geberit devices", len(devices))
            
            return devices
            
        except Exception as e:
            _LOGGER.error("Error during Bluetooth scan: %s", e)
            return []
    
    def _device_detection_callback(self, device: BLEDevice, advertisement_data):
        """Callback for device detection."""
        try:
            # Check if this might be a Geberit device
            if self._is_geberit_device(device, advertisement_data):
                discovered_device = DiscoveredDevice(
                    name=device.name or "Unknown",
                    address=device.address,
                    rssi=advertisement_data.rssi,
                    local_name=advertisement_data.local_name,
                    manufacturer_data=advertisement_data.manufacturer_data,
                )
                
                # Only add if not already discovered or if RSSI is better
                existing = self._discovered_devices.get(device.address)
                if not existing or discovered_device.rssi > existing.rssi:
                    self._discovered_devices[device.address] = discovered_device
                    _LOGGER.debug(
                        "Found Geberit device: %s (%s) RSSI: %d",
                        discovered_device.display_name,
                        device.address,
                        discovered_device.rssi
                    )
                    
        except Exception as e:
            _LOGGER.debug("Error processing device %s: %s", device.address, e)
    
    def _is_geberit_device(self, device: BLEDevice, advertisement_data) -> bool:
        """Check if a device is likely a Geberit AquaClean device.
        
        Args:
            device: The BLE device
            advertisement_data: Advertisement data
            
        Returns:
            True if device is likely a Geberit device
        """
        # Check device name
        if device.name:
            for pattern in GEBERIT_DEVICE_NAMES:
                if pattern.lower() in device.name.lower():
                    return True
        
        # Check local name in advertisement data
        if advertisement_data.local_name:
            for pattern in GEBERIT_DEVICE_NAMES:
                if pattern.lower() in advertisement_data.local_name.lower():
                    return True
        
        # Check for known service UUIDs
        if advertisement_data.service_uuids:
            for uuid in advertisement_data.service_uuids:
                if str(uuid).upper() in [s.upper() for s in GEBERIT_SERVICE_UUIDS]:
                    return True
        
        # Check manufacturer data for known patterns
        if advertisement_data.manufacturer_data:
            # Add manufacturer ID checks here when known
            # For now, we rely on name-based detection
            pass
        
        # Additional heuristics could be added here:
        # - Check for specific service data
        # - Check for specific advertisement patterns
        # - Check device capabilities
        
        return False
    
    async def find_device_by_address(self, address: str) -> Optional[BLEDevice]:
        """Find a specific device by MAC address.
        
        Args:
            address: MAC address of the device
            
        Returns:
            BLE device if found, None otherwise
        """
        try:
            return await BleakScanner.find_device_by_address(address, timeout=10.0)
        except Exception as e:
            _LOGGER.error("Error finding device %s: %s", address, e)
            return None


# Global scanner instance
_scanner_instance: Optional[GeberitBLEScanner] = None


def get_scanner() -> GeberitBLEScanner:
    """Get the global scanner instance."""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = GeberitBLEScanner()
    return _scanner_instance
