"""Geberit AquaClean BLE client implementation."""
import asyncio
import logging
from dataclasses import dataclass
from typing import Optional
from bleak import BleakClient
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

# BLE communication characteristics
WRITE_CHARACTERISTIC_UUID = "00002A24-0000-1000-8000-00805F9B34FB"
NOTIFY_CHARACTERISTIC_UUID = "00002A25-0000-1000-8000-00805F9B34FB"

# Response timeout for BLE commands (increased per HA best practices)
RESPONSE_TIMEOUT = 10.0
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
    """Client for Geberit AquaClean toilet."""

    def __init__(self, mac_address: str, hass: HomeAssistant):
        """Initialize the client."""
        self.mac_address = mac_address
        self._hass = hass
        self._client: Optional[BleakClient] = None
        self._device_state = DeviceState()
        # Initialize frame collector for handling multi-frame messages
        self._frame_collector = BLEFrameCollector()
        self._device_identification = DeviceIdentification()
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
            await self._client.start_notify(NOTIFY_CHARACTERISTIC_UUID, self._handle_notification)
            _LOGGER.debug("Notifications setup successfully")
        except Exception as e:
            _LOGGER.warning("Failed to setup notifications: %s", e)
            
    def _handle_notification(self, sender: int, data: bytes):
        """Handle incoming BLE notifications."""
        try:
            _LOGGER.debug("Received notification: %s", data.hex())
            
            # Parse frame from received data  
            frame = GeberitProtocolSerializer.decode_from_cobs(data)
            if frame:
                # Add frame to collector
                if self._frame_collector.add_frame(frame):
                    # Complete message received
                    message_data = self._frame_collector.get_complete_message()
                    if message_data:
                        self._last_response_data = message_data
                        self._response_event.set()
                        
        except Exception as e:
            _LOGGER.error("Error handling notification: %s", e)
            
    async def _initialize_device(self):
        """Initialize device and read basic information."""
        try:
            # Read device information
            await self._read_device_identification()
        except Exception as e:
            _LOGGER.warning("Failed to initialize device: %s", e)
            
    async def _read_device_identification(self):
        """Read device identification data."""
        try:
            if self._client and self._client.is_connected:
                # Send device identification request using protocol
                request_frame = GeberitProtocolSerializer.create_device_info_request()
                frame_data = GeberitProtocolSerializer.encode_with_cobs(request_frame)
                response_data = await self._send_frame_and_wait_response(frame_data)
                self._device_identification = GeberitProtocolSerializer.parse_device_info_response(response_data)
                
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
            await self._client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, frame_data)
            _LOGGER.debug("Sent frame: %s", frame_data.hex())
            
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
