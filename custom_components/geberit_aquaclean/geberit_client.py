"""Geberit AquaClean BLE client implementation."""
import asyncio
import logging
import binascii
from dataclasses import dataclass
from typing import Optional
from bleak import BleakClient, BleakScanner
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from .protocol import (
    BLEFrameCollector,
    GeberitProtocolSerializer,
    DeviceIdentification,
    HighLevelCommand,
    DataPoint
)

_LOGGER = logging.getLogger(__name__)

# BLE communication characteristics - Geberit custom service
# Service: 3334429d-90f3-4c41-a02d-5cb3a03e0000
WRITE_CHARACTERISTIC_UUID = "3334429d-90f3-4c41-a02d-5cb3a33e0000"  # Write capability (Handle 8)
NOTIFY_CHARACTERISTIC_UUID = "3334429d-90f3-4c41-a02d-5cb3a63e0000"  # Notify capability (Handle 18)

# Response timeout for BLE commands (increased per HA best practices)
RESPONSE_TIMEOUT = 10.0

# Debug mode (set to True to enable verbose logging without config changes)
DEBUG_MODE = True
CONNECTION_TIMEOUT = 15.0

@dataclass
class DeviceState:
    """Device state data."""
    # Basic status
    user_is_sitting: bool = False
    anal_shower_running: bool = False
    lady_shower_running: bool = False
    dryer_running: bool = False
    lid_position: bool = False  # True = open, False = closed
    connected: bool = False
    # Device info
    sap_number: str = ""
    serial_number: str = ""
    production_date: str = ""
    description: str = ""
    firmware_version: str = ""
    # Temperature and comfort
    water_temperature: int = 37  # 34-40°C
    seat_heating: bool = False
    night_light: bool = False
    night_light_brightness: int = 50  # 0-100%
    night_light_red: int = 255     # RGB Red 0-255
    night_light_green: int = 255   # RGB Green 0-255
    night_light_blue: int = 255    # RGB Blue 0-255
    # Orientation light (Sela only)
    orientation_light: bool = False
    orientation_light_brightness: int = 50  # 0-100%
    orientation_light_mode: int = 0     # 0-2: mode setting
    orientation_light_intensity: int = 2  # 0-4: intensity level
    orientation_light_sensor_dependent: bool = False  # 0-1: sensor activation
    orientation_light_ambient_dependent: bool = False  # 0-1: ambient light dependent
    orientation_light_led_override: bool = False  # 0-1: LED override
    orientation_light_follow_up_time: int = 30  # Follow-up time (seconds)
    orientation_light_sensor_distance: int = 2  # Sensor distance setting
    orientation_light_sensor_sensitivity: int = 2  # Sensor sensitivity
    orientation_light_movement_sensor: bool = True  # 0-1: movement sensor
    orientation_light_ambient_sensitivity: int = 2  # Ambient light sensitivity
    orientation_light_dark_threshold: int = 10  # Dark threshold setting
    # Spray controls
    spray_intensity: int = 3  # 1-5 levels
    spray_position: int = 3  # 1-5 positions
    oscillating_spray: bool = False
    # Maintenance alerts
    descaling_needed: bool = False
    filter_replacement_needed: bool = False
    power_consumption: float = 0.0  # Watts
    water_pressure: float = 0.0  # Bar
    # Advanced features
    auto_flush: bool = True
    barrier_free_mode: bool = False
    active_user_profile: int = 1  # 1-4


class GeberitAquaCleanClient:
    """Client for communicating with Geberit AquaClean devices via BLE."""
    
    def __init__(self, mac_address: str, hass: HomeAssistant, scanner: Optional[BleakScanner] = None):
        """Initialize the client."""
        self.mac_address = mac_address
        self._hass = hass
        self._scanner = scanner or bluetooth.async_get_scanner(hass)
        self._client: Optional[BleakClient] = None
        self._connected = False
        self._device_identification: Optional[DeviceIdentification] = None
        self._device_state = DeviceState()
        self._frame_collector = BLEFrameCollector()
        self._response_event = asyncio.Event()
        self._last_response_data: Optional[bytes] = None
        
    async def connect(self) -> bool:
        """Connect to the device using Home Assistant Bluetooth best practices."""
        try:
            if self._client and self._client.is_connected:
                return True
                
            # Use Home Assistant's Bluetooth scanner (best practice)
            ble_device = bluetooth.async_ble_device_from_address(
                self._hass, self.mac_address.upper(), connectable=True
            )
            
            if not ble_device:
                _LOGGER.error("Device %s not found in Bluetooth registry", self.mac_address)
                return False
                
            # Use bleak-retry-connector for reliable connection (best practice)
            self._client = await establish_connection(
                BleakClient,
                ble_device,
                self.mac_address,
                timeout=CONNECTION_TIMEOUT,
                max_attempts=3,
                use_services_cache=True
            )
            
            if not self._client.is_connected:
                _LOGGER.error("Failed to connect to device %s", self.mac_address)
                return False
                
            # Setup notifications
            await self._setup_notifications()
            
            # Initialize device
            await self._initialize_device()
            
            _LOGGER.info("Successfully connected to device %s", self.mac_address)
            return True
            
        except Exception as e:
            _LOGGER.error("Failed to connect to device %s: %s", self.mac_address, e)
            self._client = None
            return False
            
        return False
        
    async def disconnect(self):
        """Disconnect from the device."""
        if self._client and self._client.is_connected:
            try:
                await self._client.stop_notify(NOTIFY_CHARACTERISTIC_UUID)
            except Exception:
                pass  # Ignore errors during cleanup
            await self._client.disconnect()
            self._connected = False
            _LOGGER.info("Disconnected from Geberit AquaClean")
            
    async def _setup_notifications(self):
        """Setup BLE notifications for receiving data."""
        try:
            # Log available services and characteristics for debugging
            if DEBUG_MODE:
                _LOGGER.info("=== BLE Services Discovery for %s ===", self.mac_address)
                for service in self._client.services:
                    _LOGGER.info("Service: %s (%s)", service.uuid, service.description or "Unknown")
                    for char in service.characteristics:
                        # Handle both string and object properties
                        props = []
                        for p in char.properties:
                            if hasattr(p, 'name'):
                                props.append(p.name)
                            else:
                                props.append(str(p))
                        _LOGGER.info("  Char: %s - Properties: %s", char.uuid, props)
                        
                        # Check for notify capability
                        notify_capable = False
                        for p in char.properties:
                            prop_name = p.name if hasattr(p, 'name') else str(p)
                            if prop_name.lower() == "notify":
                                notify_capable = True
                                break
                        if notify_capable:
                            _LOGGER.info("    -> NOTIFY capable characteristic found!")
            
            if DEBUG_MODE:
                _LOGGER.info("Attempting to setup notifications on %s", NOTIFY_CHARACTERISTIC_UUID)
            await self._client.start_notify(NOTIFY_CHARACTERISTIC_UUID, self._handle_notification)
            _LOGGER.debug("Notifications setup successfully")
        except Exception as e:
            _LOGGER.error("Failed to setup notifications on %s: %s", NOTIFY_CHARACTERISTIC_UUID, e)
            
            # Try to find alternative notification characteristics
            notify_chars = []
            for service in self._client.services:
                for char in service.characteristics:
                    # Handle both string and object properties
                    notify_capable = False
                    for p in char.properties:
                        prop_name = p.name if hasattr(p, 'name') else str(p)
                        if prop_name.lower() == "notify":
                            notify_capable = True
                            break
                    if notify_capable:
                        notify_chars.append(str(char.uuid))
            
            if notify_chars:
                _LOGGER.error("Available notify characteristics: %s", notify_chars)
                _LOGGER.error("Consider updating NOTIFY_CHARACTERISTIC_UUID to one of these")
            else:
                _LOGGER.error("No notify-capable characteristics found on device")
            raise
            
    def _handle_notification(self, sender: int, data: bytes):
        """Handle incoming BLE notifications."""
        try:
            hex_data = binascii.hexlify(data).decode('ascii')
            if DEBUG_MODE:
                _LOGGER.info("Received notification from %s: %s (length: %d)", sender, hex_data, len(data))
                
                # Decode frame header according to Geberit protocol documentation
                if len(data) > 1:
                    header = data[0]
                    frame_id = (header >> 5) & 0x07  # Bits 7-5
                    msg_type_present = (header >> 4) & 0x01  # Bit 4
                    transaction = (header >> 1) & 0x07  # Bits 3-1
                    flags = header & 0x01  # Bit 0
                    
                    _LOGGER.info("Frame Header Analysis: ID=%d, MsgType=%d, Trans=%d, Flags=%d", 
                                frame_id, msg_type_present, transaction, flags)
            
            # Parse frame from received data  
            frame = GeberitProtocolSerializer.decode_from_cobs(data)
            if frame:
                _LOGGER.debug("Successfully decoded frame: length=%d", len(data))
                # Add frame to collector
                if self._frame_collector.add_frame(frame):
                    # Complete message received
                    message_data = self._frame_collector.get_complete_message()
                    if message_data:
                        _LOGGER.debug("Complete message assembled: %s", 
                                     binascii.hexlify(message_data).decode('ascii'))
                        self._last_response_data = message_data
                        self._response_event.set()
                else:
                    _LOGGER.debug("Frame added to collector, waiting for more frames")
            else:
                _LOGGER.warning("Failed to decode frame from notification data: %s", hex_data)
                _LOGGER.debug("Raw data analysis: first_byte=0x%02x, last_byte=0x%02x", 
                             data[0] if data else 0, data[-1] if data else 0)
                
        except Exception as e:
            _LOGGER.error("Error handling notification: %s", e)
            _LOGGER.debug("Exception occurred with data: %s", hex_data)
            
    async def _initialize_device(self):
        """Initialize device and read basic information."""
        try:
            # Read device identification and discover features
            await self._read_device_identification()
            await self._discover_device_features()
            
        except Exception as e:
            _LOGGER.error("Failed to initialize device: %s", e)
            
    async def _discover_device_features(self):
        """Discover which features are available on this device model."""
        _LOGGER.info("Starting feature discovery for device model")
        
        # Define feature test map: feature_name -> data_point_ids_to_test
        feature_tests = {
            "lady_shower": [1, 2, 3],  # Lady shower related data points
            "anal_shower": [0, 4, 5],  # Anal shower related data points  
            "dryer": [6, 7],           # Dryer related data points
            "seat_heating": [8, 9],    # Seat heating data points
            "night_light": [340, 341, 382], # All models: set brightness, read brightness, LED color
            "orientation_light": [42, 43, 44, 45, 46, 47, 48, 50, 51, 53, 55, 56, 58], # Sela only: comprehensive orientation light features
            "oscillating_spray": [12, 13], # Oscillating spray data points
            "auto_flush": [14, 15],    # Auto flush data points
            "user_profiles": [16, 17, 18, 19], # User profile data points
            "descaling": [20, 21],     # Descaling status data points
            "filter_status": [22, 23], # Filter replacement data points
            "barrier_free": [24, 25],  # Barrier-free mode data points
            "water_temperature": [26, 27, 28], # Temperature control
            "spray_position": [29, 30, 31],    # Spray positioning
            "spray_intensity": [32, 33, 34],   # Spray intensity control
        }
        
        self.available_features = {}
        
        for feature_name, data_point_ids in feature_tests.items():
            feature_available = False
            
            for data_point_id in data_point_ids:
                try:
                    # Create read request for this data point
                    read_request = GeberitProtocolSerializer.create_read_data_point_request(data_point_id)
                    frame_data = GeberitProtocolSerializer.encode_with_cobs(read_request)
                    
                    # Send with short timeout for feature probing
                    response_data = await self._send_frame_and_wait_response(frame_data, timeout=2.0)
                    
                    if response_data:
                        # If we get a valid response, feature is available
                        feature_available = True
                        _LOGGER.debug("Feature '%s' available (data point %d responded)", 
                                    feature_name, data_point_id)
                        break
                        
                except Exception as e:
                    _LOGGER.debug("Data point %d for feature '%s' not available: %s", 
                                data_point_id, feature_name, e)
                    continue
                    
            self.available_features[feature_name] = feature_available
            if feature_available:
                _LOGGER.info("✅ Feature '%s' detected and available", feature_name)
            else:
                _LOGGER.info("❌ Feature '%s' not available on this model", feature_name)
                
        _LOGGER.info("Feature discovery complete. Available features: %s", 
                   [name for name, available in self.available_features.items() if available])
                   
    def has_feature(self, feature_name: str) -> bool:
        """Check if a specific feature is available on this device model."""
        return self.available_features.get(feature_name, False)
        
    def get_available_features(self) -> list[str]:
        """Get list of all available features on this device model."""
        return [name for name, available in self.available_features.items() if available]
        
    async def set_night_light_state(self, state: bool) -> bool:
        """Turn night light on or off using brightness control."""
        try:
            # Turn on/off by setting brightness to 100% or 0%
            brightness = 100 if state else 0
            return await self.set_night_light_brightness(brightness)
        except Exception as e:
            _LOGGER.error("Failed to set night light state to %s: %s", state, e)
            return False
            
    async def set_night_light_brightness(self, brightness: int) -> bool:
        """Set night light brightness (0-100%) using official data point 340."""
        try:
            # Clamp brightness to valid range
            brightness = max(0, min(100, brightness))
            
            # Use data point 340: DP_LIGHTING_SET_BRIGHTNESS (Write-Only, All Models)
            write_request = GeberitProtocolSerializer.create_write_data_point_request(340, brightness)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(write_request)
            response_data = await self._send_frame_and_wait_response(frame_data)
            return response_data is not None
        except Exception as e:
            _LOGGER.error("Failed to set night light brightness to %d: %s", brightness, e)
            return False
            
    async def set_night_light_color(self, red: int, green: int, blue: int) -> bool:
        """Set night light RGB color using official data point 382."""
        try:
            # Clamp color values to valid range
            red = max(0, min(255, red))
            green = max(0, min(255, green))
            blue = max(0, min(255, blue))
            
            # Convert RGB to 24-bit color value (0-16777215)
            # Format: 0xRRGGBB
            color_value = (red << 16) | (green << 8) | blue
            
            # Use data point 382: DP_LED_COLOR (Read/Write, All Models)
            write_request = GeberitProtocolSerializer.create_write_data_point_request(382, color_value)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(write_request)
            response_data = await self._send_frame_and_wait_response(frame_data)
            return response_data is not None
        except Exception as e:
            _LOGGER.error("Failed to set night light color to RGB(%d,%d,%d): %s", red, green, blue, e)
            return False
            
    async def set_orientation_light_state(self, state: bool) -> bool:
        """Turn orientation light on or off using brightness control (Sela only)."""
        try:
            # Turn on/off by setting brightness to 100% or 0%
            brightness = 100 if state else 0
            return await self.set_orientation_light_brightness(brightness)
        except Exception as e:
            _LOGGER.error("Failed to set orientation light state to %s: %s", state, e)
            return False
            
    async def set_orientation_light_brightness(self, brightness: int) -> bool:
        """Set orientation light brightness (0-100%) using data point 43 (Sela only)."""
        try:
            # Clamp brightness to valid range
            brightness = max(0, min(100, brightness))
            
            # Use data point 43: DP_ORIENTATION_LIGHT_SET_LED (Write-Only, Sela Only)
            write_request = GeberitProtocolSerializer.create_write_data_point_request(43, brightness)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(write_request)
            response_data = await self._send_frame_and_wait_response(frame_data)
            return response_data is not None
        except Exception as e:
            _LOGGER.error("Failed to set orientation light brightness to %d: %s", brightness, e)
            return False
            
    async def set_orientation_light_mode(self, mode: int) -> bool:
        """Set orientation light mode (0-2) using data point 44 (Sela only)."""
        try:
            # Clamp mode to valid range (0-2)
            mode = max(0, min(2, mode))
            
            # Use data point 44: DP_ORIENTATION_LIGHT_MODE (Read/Write, Sela Only)
            write_request = GeberitProtocolSerializer.create_write_data_point_request(44, mode)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(write_request)
            response_data = await self._send_frame_and_wait_response(frame_data)
            return response_data is not None
        except Exception as e:
            _LOGGER.error("Failed to set orientation light mode to %d: %s", mode, e)
            return False
            
    async def set_orientation_light_intensity(self, intensity: int) -> bool:
        """Set orientation light intensity (0-4) using data point 48 (Sela only)."""
        try:
            # Clamp intensity to valid range (0-4)
            intensity = max(0, min(4, intensity))
            
            # Use data point 48: DP_ORIENTATION_LIGHT_INTENSITY (Read/Write, Sela Only)
            write_request = GeberitProtocolSerializer.create_write_data_point_request(48, intensity)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(write_request)
            response_data = await self._send_frame_and_wait_response(frame_data)
            return response_data is not None
        except Exception as e:
            _LOGGER.error("Failed to set orientation light intensity to %d: %s", intensity, e)
            return False
            
    async def set_orientation_light_sensor_dependent(self, enabled: bool) -> bool:
        """Enable/disable sensor-dependent activation (data point 45, Sela only)."""
        try:
            value = 1 if enabled else 0
            write_request = GeberitProtocolSerializer.create_write_data_point_request(45, value)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(write_request)
            response_data = await self._send_frame_and_wait_response(frame_data)
            return response_data is not None
        except Exception as e:
            _LOGGER.error("Failed to set orientation light sensor dependent to %s: %s", enabled, e)
            return False
            
    async def set_orientation_light_ambient_dependent(self, enabled: bool) -> bool:
        """Enable/disable ambient light-dependent activation (data point 46, Sela only)."""
        try:
            value = 1 if enabled else 0
            write_request = GeberitProtocolSerializer.create_write_data_point_request(46, value)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(write_request)
            response_data = await self._send_frame_and_wait_response(frame_data)
            return response_data is not None
        except Exception as e:
            _LOGGER.error("Failed to set orientation light ambient dependent to %s: %s", enabled, e)
            return False
            
    async def set_orientation_light_led_override(self, enabled: bool) -> bool:
        """Enable/disable LED override control (data point 47, Sela only)."""
        try:
            value = 1 if enabled else 0
            write_request = GeberitProtocolSerializer.create_write_data_point_request(47, value)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(write_request)
            response_data = await self._send_frame_and_wait_response(frame_data)
            return response_data is not None
        except Exception as e:
            _LOGGER.error("Failed to set orientation light LED override to %s: %s", enabled, e)
            return False
            
    async def set_orientation_light_follow_up_time(self, seconds: int) -> bool:
        """Set follow-up time in seconds (data point 50, Sela only)."""
        try:
            # Clamp to reasonable range
            seconds = max(0, min(300, seconds))  # 0-300 seconds (5 minutes max)
            write_request = GeberitProtocolSerializer.create_write_data_point_request(50, seconds)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(write_request)
            response_data = await self._send_frame_and_wait_response(frame_data)
            return response_data is not None
        except Exception as e:
            _LOGGER.error("Failed to set orientation light follow-up time to %d: %s", seconds, e)
            return False
            
    async def set_orientation_light_sensor_distance(self, distance: int) -> bool:
        """Set sensor distance setting (data point 51, Sela only)."""
        try:
            # Distance setting - check valid range dynamically via data point 52 if needed
            distance = max(0, min(10, distance))  # Assume 0-10 range
            write_request = GeberitProtocolSerializer.create_write_data_point_request(51, distance)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(write_request)
            response_data = await self._send_frame_and_wait_response(frame_data)
            return response_data is not None
        except Exception as e:
            _LOGGER.error("Failed to set orientation light sensor distance to %d: %s", distance, e)
            return False
            
    async def set_orientation_light_sensor_sensitivity(self, sensitivity: int) -> bool:
        """Set sensor sensitivity (data point 53, Sela only)."""
        try:
            # Sensitivity setting - check valid range dynamically via data point 54 if needed
            sensitivity = max(0, min(10, sensitivity))  # Assume 0-10 range
            write_request = GeberitProtocolSerializer.create_write_data_point_request(53, sensitivity)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(write_request)
            response_data = await self._send_frame_and_wait_response(frame_data)
            return response_data is not None
        except Exception as e:
            _LOGGER.error("Failed to set orientation light sensor sensitivity to %d: %s", sensitivity, e)
            return False
            
    async def set_orientation_light_movement_sensor(self, enabled: bool) -> bool:
        """Enable/disable movement sensor control (data point 55, Sela only)."""
        try:
            value = 1 if enabled else 0
            write_request = GeberitProtocolSerializer.create_write_data_point_request(55, value)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(write_request)
            response_data = await self._send_frame_and_wait_response(frame_data)
            return response_data is not None
        except Exception as e:
            _LOGGER.error("Failed to set orientation light movement sensor to %s: %s", enabled, e)
            return False
            
    async def set_orientation_light_ambient_sensitivity(self, sensitivity: int) -> bool:
        """Set ambient light sensitivity (data point 56, Sela only)."""
        try:
            # Ambient sensitivity - check valid range dynamically via data point 57 if needed
            sensitivity = max(0, min(10, sensitivity))  # Assume 0-10 range
            write_request = GeberitProtocolSerializer.create_write_data_point_request(56, sensitivity)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(write_request)
            response_data = await self._send_frame_and_wait_response(frame_data)
            return response_data is not None
        except Exception as e:
            _LOGGER.error("Failed to set orientation light ambient sensitivity to %d: %s", sensitivity, e)
            return False
            
    async def set_orientation_light_dark_threshold(self, threshold: int) -> bool:
        """Set dark threshold setting (data point 58, Sela only)."""
        try:
            # Dark threshold - clamp to reasonable range
            threshold = max(0, min(100, threshold))  # 0-100 range
            write_request = GeberitProtocolSerializer.create_write_data_point_request(58, threshold)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(write_request)
            response_data = await self._send_frame_and_wait_response(frame_data)
            return response_data is not None
        except Exception as e:
            _LOGGER.error("Failed to set orientation light dark threshold to %d: %s", threshold, e)
            return False
        
    async def _write_data_point(self, data_point_id: int, value: int) -> bool:
        """Write a value to a specific data point."""
        try:
            write_request = GeberitProtocolSerializer.create_write_data_point_request(data_point_id, value)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(write_request)
            response_data = await self._send_frame_and_wait_response(frame_data)
            return response_data is not None
        except Exception as e:
            _LOGGER.error("Failed to write data point %d with value %d: %s", data_point_id, value, e)
            return False
        
    async def _read_device_identification(self):
        """Read device identification data."""
        try:
            if self._client and self._client.is_connected:
                # Send device identification request using protocol
                request_frame = GeberitProtocolSerializer.create_device_info_request()
                frame_data = GeberitProtocolSerializer.encode_with_cobs(request_frame)
                response_data = await self._send_frame_and_wait_response(frame_data)
                device_info = GeberitProtocolSerializer.parse_device_info_response(response_data)
                
                if device_info:
                    _LOGGER.info("Device identification: %s (S/N: %s, SAP: %s)", 
                               device_info.get("model", "Unknown"), 
                               device_info.get("serial_number", "Unknown"),
                               device_info.get("sap_number", "Unknown"))
                    self._device_identification = device_info
                
                # Update device info from identification
                if self._device_identification:
                    self._device_state.sap_number = self._device_identification.sap_number
                    self._device_state.serial_number = self._device_identification.serial_number
                    self._device_state.production_date = self._device_identification.production_date
                    self._device_state.description = self._device_identification.description
                    self._device_state.firmware_version = self._device_identification.firmware_version or "Geberit AquaClean"
                
                _LOGGER.info("Device identification: %s (S/N: %s, SAP: %s)", 
                           self._device_state.description,
                           self._device_state.serial_number,
                           self._device_state.sap_number)
                
        except Exception as e:
            _LOGGER.warning("Failed to read device identification: %s", e)
    
    async def _send_frame_and_wait_response(self, frame_data: bytes, timeout: float = RESPONSE_TIMEOUT) -> bytes:
        """Send a frame and wait for response."""
        try:
            # Clear previous response
            self._response_event.clear()
            self._last_response_data = None
            
            # Send the frame data (already encoded with COBS)
            hex_data = binascii.hexlify(frame_data).decode('ascii')
            _LOGGER.debug("Sending frame to %s: %s (length: %d)", WRITE_CHARACTERISTIC_UUID, hex_data, len(frame_data))
            await self._client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, frame_data)
            _LOGGER.debug("Frame sent successfully")
            
            # Wait for response
            try:
                await asyncio.wait_for(self._response_event.wait(), timeout=timeout)
                return self._last_response_data
            except asyncio.TimeoutError:
                _LOGGER.warning("Timeout waiting for response")
                return None
                
        except Exception as e:
            _LOGGER.error("Failed to send frame: %s", e)
            return None
            
    async def get_device_state(self) -> DeviceState:
        """Get current device state."""
        if not self._connected or not self._client or not self._client.is_connected:
            if not await self.connect():
                self._device_state.connected = False
                return self._device_state
                
        try:
            # Read system parameters using the protocol
            await self._read_system_parameters()
            self._device_state.connected = True
            
        except Exception as e:
            _LOGGER.error("Failed to get device state: %s", e)
            self._device_state.connected = False
            
        return self._device_state
        
    async def _read_system_parameters(self):
        """Read system parameters from device."""
        try:
            if self._client and self._client.is_connected:
                # Send system parameter list request using protocol
                request_frame = GeberitProtocolSerializer.create_system_status_request()
                frame_data = GeberitProtocolSerializer.encode_with_cobs(request_frame)
                response_data = await self._send_frame_and_wait_response(frame_data)
                system_params = GeberitProtocolSerializer.parse_system_status_response(response_data)
                
                # Update device state from system parameters
                if system_params:
                    self._device_state.user_is_sitting = system_params.user_is_sitting
                    self._device_state.anal_shower_running = system_params.anal_shower_running
                    self._device_state.lady_shower_running = system_params.lady_shower_running
                    self._device_state.dryer_running = system_params.dryer_running
                    self._device_state.lid_position = system_params.lid_position
                    # Temperature and comfort
                    self._device_state.water_temperature = system_params.water_temperature
                    self._device_state.seat_heating = system_params.seat_heating
                    self._device_state.night_light = system_params.night_light
                    # Spray controls
                    self._device_state.spray_intensity = system_params.spray_intensity
                    self._device_state.spray_position = system_params.spray_position
                    self._device_state.oscillating_spray = system_params.oscillating_spray
                    # Maintenance
                    self._device_state.descaling_needed = system_params.descaling_needed
                    self._device_state.filter_replacement_needed = system_params.filter_replacement_needed
                    self._device_state.power_consumption = system_params.power_consumption
                    self._device_state.water_pressure = system_params.water_pressure
                    # Advanced features
                    self._device_state.auto_flush = system_params.auto_flush
                    self._device_state.barrier_free_mode = system_params.barrier_free_mode
                    self._device_state.active_user_profile = system_params.active_user_profile
                    
                    _LOGGER.debug("Updated system parameters: sitting=%s, anal_shower=%s, lady_shower=%s, dryer=%s, lid=%s",
                                system_params.user_is_sitting,
                                system_params.anal_shower_running,
                                system_params.lady_shower_running,
                                system_params.dryer_running,
                                system_params.lid_position)
                else:
                    _LOGGER.warning("No response received for system parameter request")
            
        except Exception as e:
            _LOGGER.error("Failed to read system parameters: %s", e)
            
    async def toggle_lid_position(self) -> bool:
        """Toggle the lid position."""
        if not self._connected or not self._client or not self._client.is_connected:
            if not await self.connect():
                return False
                
        try:
            # Send lid toggle command using protocol
            frame = GeberitProtocolSerializer.create_high_level_command(HighLevelCommand.TOGGLE_LID)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
            response_data = await self._send_frame_and_wait_response(frame_data)
            
            if response_data:
                # Command sent successfully, update state optimistically
                self._device_state.lid_position = not self._device_state.lid_position
                _LOGGER.info("Toggled lid position to %s", self._device_state.lid_position)
                return True
            else:
                _LOGGER.warning("No response received for lid toggle command")
                return False
            
        except Exception as e:
            _LOGGER.error("Failed to toggle lid position: %s", e)
            return False
    
    async def start_rear_wash(self) -> bool:
        """Start rear wash function."""
        if not self._connected or not self._client or not self._client.is_connected:
            if not await self.connect():
                return False
                
        try:
            frame = GeberitProtocolSerializer.create_high_level_command(HighLevelCommand.TOGGLE_ANAL_SHOWER)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
            response_data = await self._send_frame_and_wait_response(frame_data)
            
            if response_data:
                _LOGGER.info("Started rear wash")
                return True
            else:
                _LOGGER.warning("No response received for rear wash start command")
                return False
                
        except Exception as e:
            _LOGGER.error("Failed to start rear wash: %s", e)
            return False
    
    async def stop_rear_wash(self) -> bool:
        """Stop rear wash function."""
        if not self._connected or not self._client or not self._client.is_connected:
            if not await self.connect():
                return False
                
        try:
            frame = GeberitProtocolSerializer.create_high_level_command(HighLevelCommand.TOGGLE_ANAL_SHOWER)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
            response_data = await self._send_frame_and_wait_response(frame_data)
            
            if response_data:
                _LOGGER.info("Stopped rear wash")
                return True
            else:
                _LOGGER.warning("No response received for rear wash stop command")
                return False
                
        except Exception as e:
            _LOGGER.error("Failed to stop rear wash: %s", e)
            return False
    
    async def start_front_wash(self) -> bool:
        """Start front wash function."""
        if not self._connected or not self._client or not self._client.is_connected:
            if not await self.connect():
                return False
                
        try:
            frame = GeberitProtocolSerializer.create_high_level_command(HighLevelCommand.TOGGLE_LADY_SHOWER)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
            response_data = await self._send_frame_and_wait_response(frame_data)
            
            if response_data:
                _LOGGER.info("Started front wash")
                return True
            else:
                _LOGGER.warning("No response received for front wash start command")
                return False
                
        except Exception as e:
            _LOGGER.error("Failed to start front wash: %s", e)
            return False
    
    async def stop_front_wash(self) -> bool:
        """Stop front wash function."""
        if not self._connected or not self._client or not self._client.is_connected:
            if not await self.connect():
                return False
                
        try:
            frame = GeberitProtocolSerializer.create_high_level_command(HighLevelCommand.TOGGLE_LADY_SHOWER)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
            response_data = await self._send_frame_and_wait_response(frame_data)
            
            if response_data:
                _LOGGER.info("Stopped front wash")
                return True
            else:
                _LOGGER.warning("No response received for front wash stop command")
                return False
                
        except Exception as e:
            _LOGGER.error("Failed to stop front wash: %s", e)
            return False
    
    async def start_dryer(self) -> bool:
        """Start dryer function."""
        if not self._connected or not self._client or not self._client.is_connected:
            if not await self.connect():
                return False
                
        try:
            frame = GeberitProtocolSerializer.create_high_level_command(HighLevelCommand.TOGGLE_DRYER)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
            response_data = await self._send_frame_and_wait_response(frame_data)
            
            if response_data:
                _LOGGER.info("Started dryer")
                return True
            else:
                _LOGGER.warning("No response received for dryer start command")
                return False
                
        except Exception as e:
            _LOGGER.error("Failed to start dryer: %s", e)
            return False
    
    async def stop_dryer(self) -> bool:
        """Stop dryer function."""
        if not self._connected or not self._client or not self._client.is_connected:
            if not await self.connect():
                return False
                
        try:
            frame = GeberitProtocolSerializer.create_high_level_command(HighLevelCommand.TOGGLE_DRYER)
            frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
            response_data = await self._send_frame_and_wait_response(frame_data)
            
            if response_data:
                _LOGGER.info("Stopped dryer")
                return True
            else:
                _LOGGER.warning("No response received for dryer stop command")
                return False
                
        except Exception as e:
            _LOGGER.error("Failed to stop dryer: %s", e)
            return False
    
    async def toggle_dryer(self) -> bool:
        """Toggle dryer state."""
        try:
            if self._client and self._client.is_connected:
                # Send dryer toggle command using protocol
                frame = GeberitProtocolSerializer.create_high_level_command(HighLevelCommand.TOGGLE_DRYER)
                frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
                response_data = await self._send_frame_and_wait_response(frame_data)
                
                if response_data:
                    _LOGGER.debug("Dryer toggle command sent successfully")
                    return True
                else:
                    _LOGGER.warning("No response received for dryer toggle command")
                    return False
            else:
                _LOGGER.error("Cannot toggle dryer: device not connected")
                return False
        except Exception as ex:
            _LOGGER.error("Failed to toggle dryer: %s", ex)
            return False

    async def set_water_temperature(self, temperature: int) -> bool:
        """Set water temperature (34-40°C)."""
        try:
            if not 34 <= temperature <= 40:
                _LOGGER.error("Invalid temperature: %s (must be 34-40°C)", temperature)
                return False
                
            if self._client and self._client.is_connected:
                frame = GeberitProtocolSerializer.create_data_point_write(DataPoint.DP_WATER_TEMPERATURE, bytes([temperature]))
                frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
                response_data = await self._send_frame_and_wait_response(frame_data)
                
                if response_data:
                    _LOGGER.debug("Water temperature set to %s°C", temperature)
                    return True
                else:
                    _LOGGER.warning("No response received for water temperature command")
                    return False
            else:
                _LOGGER.error("Cannot set water temperature: device not connected")
                return False
        except Exception as ex:
            _LOGGER.error("Failed to set water temperature: %s", ex)
            return False

    async def set_spray_intensity(self, intensity: int) -> bool:
        """Set spray intensity (1-5)."""
        try:
            if not 1 <= intensity <= 5:
                _LOGGER.error("Invalid spray intensity: %s (must be 1-5)", intensity)
                return False
                
            if self._client and self._client.is_connected:
                frame = GeberitProtocolSerializer.create_data_point_write(DataPoint.DP_SPRAY_INTENSITY, bytes([intensity]))
                frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
                response_data = await self._send_frame_and_wait_response(frame_data)
                
                if response_data:
                    _LOGGER.debug("Spray intensity set to %s", intensity)
                    return True
                else:
                    _LOGGER.warning("No response received for spray intensity command")
                    return False
            else:
                _LOGGER.error("Cannot set spray intensity: device not connected")
                return False
        except Exception as ex:
            _LOGGER.error("Failed to set spray intensity: %s", ex)
            return False

    async def set_spray_position(self, position: int) -> bool:
        """Set spray position (1-5)."""
        try:
            if not 1 <= position <= 5:
                _LOGGER.error("Invalid spray position: %s (must be 1-5)", position)
                return False
                
            if self._client and self._client.is_connected:
                frame = GeberitProtocolSerializer.create_data_point_write(DataPoint.DP_SPRAY_POSITION, bytes([position]))
                frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
                response_data = await self._send_frame_and_wait_response(frame_data)
                
                if response_data:
                    _LOGGER.debug("Spray position set to %s", position)
                    return True
                else:
                    _LOGGER.warning("No response received for spray position command")
                    return False
            else:
                _LOGGER.error("Cannot set spray position: device not connected")
                return False
        except Exception as ex:
            _LOGGER.error("Failed to set spray position: %s", ex)
            return False

    async def set_user_profile(self, profile: int) -> bool:
        """Set active user profile (1-4)."""
        try:
            if not 1 <= profile <= 4:
                _LOGGER.error("Invalid user profile: %s (must be 1-4)", profile)
                return False
                
            if self._client and self._client.is_connected:
                frame = GeberitProtocolSerializer.create_data_point_write(DataPoint.DP_ACTIVE_USER_PROFILE, bytes([profile]))
                frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
                response_data = await self._send_frame_and_wait_response(frame_data)
                
                if response_data:
                    _LOGGER.debug("User profile set to %s", profile)
                    return True
                else:
                    _LOGGER.warning("No response received for user profile command")
                    return False
            else:
                _LOGGER.error("Cannot set user profile: device not connected")
                return False
        except Exception as ex:
            _LOGGER.error("Failed to set user profile: %s", ex)
            return False

    async def toggle_seat_heating(self) -> bool:
        """Toggle seat heating."""
        try:
            if self._client and self._client.is_connected:
                frame = GeberitProtocolSerializer.create_high_level_command(HighLevelCommand.TOGGLE_SEAT_HEATING)
                frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
                response_data = await self._send_frame_and_wait_response(frame_data)
                
                if response_data:
                    _LOGGER.debug("Seat heating toggled")
                    return True
                else:
                    _LOGGER.warning("No response received for seat heating command")
                    return False
            else:
                _LOGGER.error("Cannot toggle seat heating: device not connected")
                return False
        except Exception as ex:
            _LOGGER.error("Failed to toggle seat heating: %s", ex)
            return False

    async def toggle_night_light(self) -> bool:
        """Toggle night light."""
        try:
            if self._client and self._client.is_connected:
                frame = GeberitProtocolSerializer.create_high_level_command(HighLevelCommand.TOGGLE_ORIENTATION_LIGHT)
                frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
                response_data = await self._send_frame_and_wait_response(frame_data)
                
                if response_data:
                    _LOGGER.debug("Night light toggled")
                    return True
                else:
                    _LOGGER.warning("No response received for night light command")
                    return False
            else:
                _LOGGER.error("Cannot toggle night light: device not connected")
                return False
        except Exception as ex:
            _LOGGER.error("Failed to toggle night light: %s", ex)
            return False

    async def toggle_oscillating_spray(self) -> bool:
        """Toggle oscillating spray."""
        try:
            if self._client and self._client.is_connected:
                frame = GeberitProtocolSerializer.create_data_point_write(DataPoint.DP_OSCILLATING, bytes([1]))
                frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
                response_data = await self._send_frame_and_wait_response(frame_data)
                
                if response_data:
                    _LOGGER.debug("Oscillating spray toggled")
                    return True
                else:
                    _LOGGER.warning("No response received for oscillating spray command")
                    return False
            else:
                _LOGGER.error("Cannot toggle oscillating spray: device not connected")
                return False
        except Exception as ex:
            _LOGGER.error("Failed to toggle oscillating spray: %s", ex)
            return False

    async def toggle_auto_flush(self) -> bool:
        """Toggle auto flush."""
        try:
            if self._client and self._client.is_connected:
                frame = GeberitProtocolSerializer.create_data_point_write(DataPoint.DP_AUTO_FLUSH, bytes([1]))
                frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
                response_data = await self._send_frame_and_wait_response(frame_data)
                
                if response_data:
                    _LOGGER.debug("Auto flush toggled")
                    return True
                else:
                    _LOGGER.warning("No response received for auto flush command")
                    return False
            else:
                _LOGGER.error("Cannot toggle auto flush: device not connected")
                return False
        except Exception as ex:
            _LOGGER.error("Failed to toggle auto flush: %s", ex)
            return False

    async def toggle_barrier_free_mode(self) -> bool:
        """Toggle barrier-free mode."""
        try:
            if self._client and self._client.is_connected:
                frame = GeberitProtocolSerializer.create_data_point_write(DataPoint.DP_BARRIER_FREE_MODE, bytes([1]))
                frame_data = GeberitProtocolSerializer.encode_with_cobs(frame)
                response_data = await self._send_frame_and_wait_response(frame_data)
                
                if response_data:
                    _LOGGER.debug("Barrier-free mode toggled")
                    return True
                else:
                    _LOGGER.warning("No response received for barrier-free mode command")
                    return False
            else:
                _LOGGER.error("Cannot toggle barrier-free mode: device not connected")
                return False
        except Exception as ex:
            _LOGGER.error("Failed to toggle barrier-free mode: %s", ex)
            return False
