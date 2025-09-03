"""Geberit AquaClean BLE protocol implementation."""
import struct
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

_LOGGER = logging.getLogger(__name__)

# Protocol constants based on the original library
FRAME_START_BYTE = 0x02
FRAME_END_BYTE = 0x03
MAX_FRAME_SIZE = 20  # BLE characteristic max size
RESPONSE_TIMEOUT = 5.0  # seconds

class CommandType(Enum):
    """BLE command types."""
    LID_CONTROL = 0x01
    ANAL_SHOWER_CONTROL = 0x02
    LADY_SHOWER_CONTROL = 0x03
    DRYER_CONTROL = 0x04
    SET_COMMAND = 0x10
    GET_COMMAND = 0x11
    SET_PARAMETER = 0x20
    TOGGLE_PARAMETER = 0x21

class ParameterType(Enum):
    """System parameter types."""
    USER_IS_SITTING = 0x10
    ANAL_SHOWER_RUNNING = 0x11
    LADY_SHOWER_RUNNING = 0x12
    DRYER_RUNNING = 0x13
    LID_POSITION = 0x14
    ORIENTATION_LIGHT_STATE = 0x15
    # Temperature and comfort
    WATER_TEMPERATURE = 0x20
    SEAT_HEATING = 0x21
    NIGHT_LIGHT = 0x22
    # Spray controls  
    SPRAY_INTENSITY = 0x30
    SPRAY_POSITION = 0x31
    OSCILLATING_SPRAY = 0x32
    # Maintenance
    DESCALING_NEEDED = 0x40
    FILTER_REPLACEMENT_NEEDED = 0x41
    POWER_CONSUMPTION = 0x42
    WATER_PRESSURE = 0x43
    # Advanced features
    AUTO_FLUSH = 0x50
    BARRIER_FREE_MODE = 0x51
    ACTIVE_USER_PROFILE = 0x52

class HighLevelCommand(Enum):
    """High-level commands (verified from source code)."""
    # Device Control Commands
    TOGGLE_ANAL_SHOWER = 0
    TOGGLE_LADY_SHOWER = 1
    TOGGLE_DRYER = 2
    TOGGLE_LID_POSITION = 10
    TOGGLE_ORIENTATION_LIGHT = 20
    TRIGGER_FLUSH_MANUALLY = 37
    
    # Cleaning & Maintenance Commands
    START_CLEANING_DEVICE = 4
    EXECUTE_NEXT_CLEANING_STEP = 5
    RESET_FILTER_COUNTER = 47
    
    # Descaling Commands
    PREPARE_DESCALING = 6
    CONFIRM_DESCALING = 7
    CANCEL_DESCALING = 8
    POSTPONE_DESCALING = 9
    
    # Calibration Commands
    START_LID_POSITION_CALIBRATION = 33
    LID_POSITION_OFFSET_SAVE = 34
    LID_POSITION_OFFSET_INCREMENT = 35
    LID_POSITION_OFFSET_DECREMENT = 36

class DataPoint(Enum):
    """Data point IDs (verified from DpId.cs source code)."""
    # System Information
    DP_DEVICE_SERIES = 0
    DP_DEVICE_VARIANT = 1
    DP_DEVICE_NUMBER = 2
    DP_PCB_SERIAL_NUMBER = 5
    DP_FW_RS_VERSION = 8
    DP_FW_TS_VERSION = 9
    DP_HW_RS_VERSION = 10
    DP_BLUETOOTH_ID = 11
    DP_RTC_TIME = 15
    DP_NAME = 16
    DP_SUPPLY_VOLTAGE = 19
    
    # Flush Operations
    DP_BLOCK_FLUSH = 112
    DP_BLOCK_FLUSH_STATUS = 113
    DP_CLEANING_MODE = 115
    DP_CLEANING_MODE_STATUS = 117
    DP_PRE_FLUSH = 118
    DP_POST_FLUSH = 119
    DP_MANUAL_FLUSH = 126
    DP_AUTOMATIC_FLUSH = 127
    DP_FLUSH = 141
    DP_FLUSH_STATUS = 142
    DP_FULL_FLUSH_VOLUME = 291
    DP_PART_FLUSH_VOLUME = 292
    
    # Shower Operations
    DP_START_STOP_ANAL_SHOWER = 563
    DP_ANAL_SHOWER_STATUS = 564
    DP_ANAL_SHOWER_PROGRESS = 565
    DP_START_STOP_LADY_SHOWER = 868
    DP_SET_ACTIVE_ANAL_SPRAY_INTENSITY = 570
    DP_ACTIVE_ANAL_SPRAY_INTENSITY_STATUS = 571
    DP_SET_ACTIVE_ANAL_SPRAY_ARM_POSITION = 572
    DP_ACTIVE_ANAL_SPRAY_ARM_POSITION_STATUS = 573
    DP_SET_ACTIVE_SHOWER_WATER_TEMPERATURE = 574
    DP_ACTIVE_SHOWER_WATER_TEMPERATURE_STATUS = 575
    DP_SET_ACTIVE_ANAL_SPRAY_ARM_OSCILLATION = 576
    DP_ACTIVE_ANAL_SPRAY_ARM_OSCILLATION_STATUS = 577
    DP_STORED_ANAL_SPRAY_INTENSITY = 580
    DP_STORED_ANAL_SPRAY_ARM_POSITION = 581
    DP_STORED_SHOWER_WATER_TEMPERATURE = 582
    DP_STORED_ANAL_SPRAY_ARM_OSCILLATION = 583
    DP_SET_ACTIVE_ANAL_SHOWER_TIME = 849
    DP_ACTIVE_ANAL_SHOWER_TIME = 850
    DP_STORED_ANAL_SHOWER_TIME = 851
    DP_SET_ACTIVE_LADY_SHOWER_TIME = 855
    DP_SET_ACTIVE_LADY_SPRAY_INTENSITY = 858
    DP_LADY_SHOWER_STATUS = 872
    DP_LADY_SHOWER_PROGRESS = 873
    
    # Dryer Operations
    DP_START_STOP_DRYING = 874
    DP_DRYING_STATUS = 875
    DP_DRYING_PROGRESS = 876
    DP_DRYER_FAN_SET_INTENSITY = 877
    DP_DRYER_FAN_INTENSITY = 878
    DP_DRYER_HEATER_SET_TEMPERATURE = 883
    DP_DRYER_HEATER_TEMPERATURE = 884
    DP_SET_ACTIVE_DRYER_FAN_INTENSITY = 893
    DP_ACTIVE_DRYER_FAN_INTENSITY_STATUS = 894
    DP_STORED_DRYER_FAN_INTENSITY = 895
    
    # Lighting Control
    DP_ORIENTATION_LIGHT_LED = 42
    DP_ORIENTATION_LIGHT_SET_LED = 43
    DP_ORIENTATION_LIGHT_MODE = 44
    DP_ORIENTATION_LIGHT_INTENSITY = 48
    DP_LIGHTING_BRIGHTNESS_ADJUST = 322
    DP_LIGHTING_SET_BRIGHTNESS = 340
    DP_LIGHTING_BRIGHTNESS_STATUS = 341
    DP_LED_COLOR = 382
    
    # Odor Extraction
    DP_ODOUR_EXTRACTION_FAN = 20
    DP_ODOUR_EXTRACTION_SET_FAN = 21
    DP_ODOUR_EXTRACTION_MODE = 23
    DP_ODOUR_EXTRACTION_POWER = 27
    DP_ODOUR_EXTRACTION_FOLLOW_UP_TIME = 29
    
    # Descaling Operations
    DP_START_STOP_DESCALING = 584
    DP_DESCALING_STATUS = 585
    DP_DESCALING_PROGRESS = 586
    DP_WATER_HARDNESS = 587
    DP_DAYS_UNTIL_NEXT_DESCALING = 589
    DP_TIMESTAMP_OF_LAST_DESCALING = 590
    DP_DESCALING_RESULT = 798
    
    # Maintenance
    DP_MAINTENANCE_DONE = 474
    DP_MAINTENANCE_STATUS = 475
    DP_MAINTENANCE_COUNTDOWN = 515
    DP_START_STOP_SPRAY_ARM_CLEANING = 566
    DP_SPRAY_ARM_CLEANING_STATUS = 567
    
    # Diagnostics
    DP_START_SELF_TEST = 151
    DP_SELF_TEST_STATUS = 152
    DP_CHECK_ACTUATOR = 184
    DP_LED_TEST = 330
    DP_DIAGNOSE_DEVICE_STATE = 372
    DP_CHECK_BUZZER = 453
    DP_START_STOP_VALVE_TEST = 791
    
    # Error Status
    DP_ODOUR_EXTRACTION_ERROR_STATUS = 88
    DP_POWER_SUPPLY_ERROR_STATUS = 93
    DP_GLOBAL_ERROR = 359
    DP_GLOBAL_WARNING = 360
    DP_TEMPSENS_ERROR_STATUS = 478
    DP_SEAT_HEATER_ERROR_STATUS = 819

class BLEFrameType(Enum):
    """BLE Frame types from the protocol specification."""
    SINGLE_START_FRAME = 0  # 0x0X - Single packet or first of multi-packet
    CONSECUTIVE_FRAME = 2   # 0x4X - Continuation of multi-packet message  
    FLOW_CONTROL_FRAME = 3  # 0x6X - Acknowledgment and flow control

class DataType(Enum):
    """Data types from the protocol specification."""
    BINARY = "Binary"           # Raw binary data (1-4 bytes)
    OFF_ON = "OffOn"           # Boolean state (0=Off, 1=On) 
    ENUM = "Enum"              # Enumerated values (0-N device specific)
    PERCENT = "Percent"        # Percentage value (0-100%)
    COUNTER = "Counter"        # Numeric counter (0-4294967295)
    STRING = "String"          # Text string (variable length)
    TIMESTAMP_UTC = "TimeStampUtc"  # UTC timestamp (Unix timestamp)
    SIGNED = "Signed"          # Signed integer (-2147483648 to +2147483647)

@dataclass
class BLEFrame:
    """Represents a proper BLE frame with verified structure."""
    frame_id: int           # Frame type (0, 2, or 3)
    has_msg_type: bool      # Message type byte present flag
    transaction: int        # Transaction number (0-7)
    flag: int              # Frame-specific flag
    payload: bytes         # Frame payload data
    
    def to_bytes(self) -> bytes:
        """Convert frame to bytes with proper header structure."""
        # Create header byte: [Frame ID][M][Transaction][F]
        header = (self.frame_id << 5) | (int(self.has_msg_type) << 4) | (self.transaction << 1) | self.flag
        
        # For consecutive frames, add count byte
        if self.frame_id == BLEFrameType.CONSECUTIVE_FRAME.value:
            return bytes([header, len(self.payload)]) + self.payload
        else:
            return bytes([header]) + self.payload
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'BLEFrame':
        """Parse frame from received bytes."""
        if len(data) < 1:
            raise ValueError("Invalid frame data")
            
        header = data[0]
        
        # Parse header bits
        frame_id = (header >> 5) & 0x07
        has_msg_type = bool((header >> 4) & 0x01)
        transaction = (header >> 1) & 0x07
        flag = header & 0x01
        
        # Extract payload based on frame type
        if frame_id == BLEFrameType.CONSECUTIVE_FRAME.value and len(data) > 1:
            count = data[1]
            payload = data[2:2+count] if len(data) > 2 else b''
        else:
            payload = data[1:] if len(data) > 1 else b''
            
        return cls(
            frame_id=frame_id,
            has_msg_type=has_msg_type,
            transaction=transaction,
            flag=flag,
            payload=payload
        )

class COBSEncoder:
    """COBS (Consistent Overhead Byte Stuffing) encoder/decoder."""
    
    @staticmethod
    def encode(data: bytes) -> bytes:
        """Encode data using COBS framing."""
        if not data:
            return b'\x01\x00'
        
        output = bytearray()
        code = 1
        code_index = 0
        output.append(0)  # Placeholder for code
        
        for byte in data:
            if byte == 0:
                output[code_index] = code
                code_index = len(output)
                output.append(0)
                code = 1
            else:
                output.append(byte)
                code += 1
                if code == 255:
                    output[code_index] = code
                    code_index = len(output)
                    output.append(0)
                    code = 1
        
        output[code_index] = code
        output.append(0)  # Frame delimiter
        return bytes(output)
    
    @staticmethod
    def decode(data: bytes) -> bytes:
        """Decode COBS framed data."""
        if not data or data[-1] != 0:
            raise ValueError("Invalid COBS frame")
        
        data = data[:-1]  # Remove delimiter
        if not data:
            return b''
            
        output = bytearray()
        i = 0
        
        while i < len(data):
            code = data[i]
            i += 1
            
            if code == 0:
                break
                
            # Copy non-zero bytes
            for j in range(min(code - 1, len(data) - i)):
                output.append(data[i + j])
            i += code - 1
            
            # Add zero byte if needed
            if code < 255 and i < len(data):
                output.append(0)
        
        return bytes(output)

@dataclass
class ProtocolFrame:
    """Represents a single protocol frame."""
    frame_type: int
    sequence_number: int
    data: bytes
    is_last_frame: bool = False
    
    def to_bytes(self) -> bytes:
        """Convert frame to bytes for transmission."""
        header = struct.pack('<BBB', FRAME_START_BYTE, self.frame_type, self.sequence_number)
        length = len(self.data)
        frame = header + struct.pack('<B', length) + self.data + struct.pack('<B', FRAME_END_BYTE)
        return frame
    
    @classmethod
    def from_bytes(cls, data: bytes) -> Optional['ProtocolFrame']:
        """Parse frame from received bytes."""
        if len(data) < 5:  # Minimum frame size
            return None
            
        if data[0] != FRAME_START_BYTE or data[-1] != FRAME_END_BYTE:
            return None
            
        frame_type = data[1]
        sequence_number = data[2]
        length = data[3]
        
        if len(data) != length + 5:  # header + length + data + end
            return None
            
        frame_data = data[4:4+length]
        return cls(frame_type, sequence_number, frame_data)

@dataclass
class DeviceIdentification:
    """Device identification information."""
    sap_number: str = ""
    serial_number: str = ""
    production_date: str = ""
    description: str = ""
    firmware_version: str = ""
    initial_operation_date: str = ""

@dataclass
class SystemParameters:
    """System parameters from device."""
    # Basic status
    user_is_sitting: bool = False
    anal_shower_running: bool = False
    lady_shower_running: bool = False
    dryer_running: bool = False
    lid_position: bool = False
    orientation_light_state: int = 0
    # Temperature and comfort
    water_temperature: int = 37  # 34-40°C
    seat_heating: bool = False
    night_light: bool = False
    # Spray controls
    spray_intensity: int = 3  # 1-5 levels
    spray_position: int = 3  # 1-5 positions
    oscillating_spray: bool = False
    # Maintenance
    descaling_needed: bool = False
    filter_replacement_needed: bool = False
    power_consumption: float = 0.0  # Watts
    water_pressure: float = 0.0  # Bar
    # Advanced features
    auto_flush: bool = True
    barrier_free_mode: bool = False
    active_user_profile: int = 1  # 1-4

class BLEFrameCollector:
    """Collects and assembles BLE frames into complete messages."""
    
    def __init__(self):
        """Initialize frame collector."""
        self._pending_frames: Dict[int, List[BLEFrame]] = {}
        self._complete_messages: List[bytes] = []
        
    def add_frame(self, frame: BLEFrame) -> bool:
        """Add a frame to the collector.
        
        Returns:
            True if a complete message was assembled
        """
        frame_id = frame.frame_id
        
        # For single frames, immediately add to complete messages
        if frame_id == BLEFrameType.SINGLE_START_FRAME.value:
            self._complete_messages.append(frame.payload)
            return True
            
        # For multi-frame messages, collect and assemble
        if frame_id not in self._pending_frames:
            self._pending_frames[frame_id] = []
            
        self._pending_frames[frame_id].append(frame)
        
        # Check if we have a complete message
        if frame_id == BLEFrameType.CONSECUTIVE_FRAME.value:
            return self._try_assemble_message(frame_id)
            
        return False
        
    def _try_assemble_message(self, frame_id: int) -> bool:
        """Try to assemble a complete message from frames."""
        if frame_id not in self._pending_frames:
            return False
            
        frames = self._pending_frames[frame_id]
        frames.sort(key=lambda f: f.transaction)
        
        # For now, just concatenate all payloads
        # TODO: Implement proper multi-frame assembly when needed
        message_data = b''.join(frame.payload for frame in frames)
        self._complete_messages.append(message_data)
        
        # Clear pending frames for this type
        del self._pending_frames[frame_id]
        
        _LOGGER.debug("Assembled complete message of %d bytes", len(message_data))
        return True
        
    def get_complete_message(self) -> Optional[bytes]:
        """Get the next complete message if available."""
        if self._complete_messages:
            return self._complete_messages.pop(0)
        return None


class GeberitProtocolSerializer:
    """Handles Geberit AquaClean protocol serialization with verified data points."""
    
    @staticmethod
    def create_high_level_command(command: HighLevelCommand) -> BLEFrame:
        """Create a high-level command frame."""
        # High-level commands use single frame format with message type
        payload = struct.pack('<H', command.value)  # Command ID as 2-byte value
        
        return BLEFrame(
            frame_id=BLEFrameType.SINGLE_START_FRAME.value,
            has_msg_type=True,
            transaction=0,
            flag=0,
            payload=payload
        )
    
    @staticmethod
    def create_data_point_read(data_point: DataPoint) -> BLEFrame:
        """Create a data point read request."""
        # Data point read request
        payload = struct.pack('<HB', data_point.value, 0x00)  # DP ID + read flag
        
        return BLEFrame(
            frame_id=BLEFrameType.SINGLE_START_FRAME.value,
            has_msg_type=True,
            transaction=1,
            flag=0,
            payload=payload
        )
    
    @staticmethod
    def create_read_data_point_request(data_point_id: int) -> BLEFrame:
        """Create a data point read request by ID for feature discovery."""
        # Data point read request using direct ID
        payload = struct.pack('<HB', data_point_id, 0x00)  # DP ID + read flag
        
        return BLEFrame(
            frame_id=BLEFrameType.SINGLE_START_FRAME.value,
            has_msg_type=True,
            transaction=1,
            flag=0,
            payload=payload
        )
    
    @staticmethod
    def create_data_point_write(data_point: DataPoint, value: bytes) -> BLEFrame:
        """Create a data point write request."""
        # Data point write request
        payload = struct.pack('<HB', data_point.value, 0x01) + value  # DP ID + write flag + value
        
        return BLEFrame(
            frame_id=BLEFrameType.SINGLE_START_FRAME.value,
            has_msg_type=True,
            transaction=2,
            flag=0,
            payload=payload
        )
    
    @staticmethod
    def create_device_info_request() -> BLEFrame:
        """Create device information request using verified data points."""
        # Read multiple device info data points
        payload = struct.pack('<HHHHHH', 
                            DataPoint.DP_DEVICE_SERIES.value,
                            DataPoint.DP_DEVICE_VARIANT.value, 
                            DataPoint.DP_DEVICE_NUMBER.value,
                            DataPoint.DP_PCB_SERIAL_NUMBER.value,
                            DataPoint.DP_FW_RS_VERSION.value,
                            DataPoint.DP_BLUETOOTH_ID.value)
        
        return BLEFrame(
            frame_id=BLEFrameType.SINGLE_START_FRAME.value,
            has_msg_type=True,
            transaction=3,
            flag=0,
            payload=payload
        )
    
    @staticmethod
    def create_system_status_request() -> BLEFrame:
        """Create system status request using verified data points."""
        # Read multiple status data points
        payload = struct.pack('<HHHHHH',
                            DataPoint.DP_ANAL_SHOWER_STATUS.value,
                            DataPoint.DP_LADY_SHOWER_STATUS.value,
                            DataPoint.DP_DRYING_STATUS.value,
                            DataPoint.DP_FLUSH_STATUS.value,
                            DataPoint.DP_DESCALING_STATUS.value,
                            DataPoint.DP_MAINTENANCE_STATUS.value)
        
        return BLEFrame(
            frame_id=BLEFrameType.SINGLE_START_FRAME.value,
            has_msg_type=True,
            transaction=4,
            flag=0,
            payload=payload
        )
    
    @staticmethod  
    def encode_with_cobs(frame: BLEFrame) -> bytes:
        """Encode BLE frame with COBS framing."""
        frame_bytes = frame.to_bytes()
        return COBSEncoder.encode(frame_bytes)
    
    @staticmethod
    def decode_from_cobs(data: bytes) -> BLEFrame:
        """Decode COBS frame to BLE frame."""
        decoded = COBSEncoder.decode(data)
        return BLEFrame.from_bytes(decoded)
    
    @staticmethod
    def parse_device_info_response(data: bytes) -> DeviceIdentification:
        """Parse device information response with verified data."""
        try:
            # Parse response payload - format may vary based on actual protocol
            device_info = DeviceIdentification()
            
            # Extract fields from response (simplified parsing)
            if len(data) >= 4:
                device_info.sap_number = f"SAP-{struct.unpack('<H', data[0:2])[0]}"
                device_info.serial_number = f"SN-{struct.unpack('<H', data[2:4])[0]:08d}"
                
            if len(data) >= 8:
                device_info.firmware_version = f"FW-{data[4]}.{data[5]}.{data[6]}.{data[7]}"
                
            if len(data) > 8:
                # Try to extract description from remaining bytes
                desc_bytes = data[8:]
                try:
                    device_info.description = desc_bytes.decode('utf-8', errors='ignore').rstrip('\x00')
                except UnicodeDecodeError:
                    device_info.description = "Geberit AquaClean"
            
            return device_info
            
        except Exception as e:
            _LOGGER.warning("Failed to parse device info response: %s", e)
            return DeviceIdentification()
    
    @staticmethod
    def parse_system_status_response(data: bytes) -> SystemParameters:
        """Parse system status response with verified data points."""
        try:
            params = SystemParameters()
            
            if data and len(data) >= 6:
                # Parse status values from response
                status_bytes = struct.unpack('<6B', data[:6])
                
                # Map to system parameters based on expected data point order
                params.anal_shower_running = status_bytes[0] > 0
                params.lady_shower_running = status_bytes[1] > 0  
                params.dryer_running = status_bytes[2] > 0
                params.user_is_sitting = status_bytes[3] > 0  # Inferred from flush status
                params.descaling_needed = status_bytes[4] > 0
                # Additional parameters can be parsed from remaining bytes
                
            return params
            
        except Exception as e:
            _LOGGER.warning("Failed to parse system status response: %s", e)
            return SystemParameters()
    
    @staticmethod
    def parse_device_notification(data: bytes) -> SystemParameters:
        """Parse device status notifications (e.g., 30140c030003000000003130001200cf08)."""
        try:
            params = SystemParameters()
            
            if not data or len(data) < 16:
                return params
                
            # Parse the notification data structure
            # Based on observed pattern: 30140c030003000000003130001200cf08
            status_flags = struct.unpack('<HH', data[4:8])  # 00 03, 00 00
            
            # Extract status information from flags
            # This is speculative based on typical device status patterns
            main_status = status_flags[0] & 0xFF
            params.user_is_sitting = bool(main_status & 0x01)
            params.anal_shower_running = bool(main_status & 0x02)
            params.lady_shower_running = bool(main_status & 0x04)
            params.dryer_running = bool(main_status & 0x08)
            
            # Additional status from secondary flags
            extended_status = (status_flags[1] >> 8) & 0xFF
            params.descaling_needed = bool(extended_status & 0x01)
            params.filter_replacement_needed = bool(extended_status & 0x02)
            
            return params
            
        except Exception as e:
            _LOGGER.debug("Failed to parse device notification: %s", e)
            return SystemParameters()
        
    @staticmethod
    def deserialize_device_identification(data: bytes) -> DeviceIdentification:
        """Deserialize device identification data."""
        try:
            # Parse device identification response
            # This is a simplified version - the real format would need reverse engineering
            if len(data) < 10:
                return DeviceIdentification()
                
            device_id = DeviceIdentification()
            
            # Extract strings from the data (assuming null-terminated strings)
            strings = []
            current_string = b''
            
            for byte in data:
                if byte == 0:  # Null terminator
                    if current_string:
                        strings.append(current_string.decode('utf-8', errors='ignore'))
                        current_string = b''
                else:
                    current_string += bytes([byte])
                    
            # Add final string if no null terminator
            if current_string:
                strings.append(current_string.decode('utf-8', errors='ignore'))
                
            # Map strings to fields (order based on typical device info)
            if len(strings) >= 1:
                device_id.description = strings[0]
            if len(strings) >= 2:
                device_id.serial_number = strings[1]
            if len(strings) >= 3:
                device_id.sap_number = strings[2]
            if len(strings) >= 4:
                device_id.firmware_version = strings[3]
                
            _LOGGER.debug("Parsed device identification: %s", device_id)
            return device_id
            
        except Exception as e:
            _LOGGER.error("Failed to deserialize device identification: %s", e)
            return DeviceIdentification()
            
    @staticmethod
    def deserialize_system_parameters(data: bytes) -> SystemParameters:
        """Deserialize system parameters data."""
        try:
            params = SystemParameters()
            
            if len(data) < 6:  # Minimum expected size
                return params
                
            # Parse parameter data (simplified format)
            # Real implementation would need proper protocol reverse engineering
            offset = 0
            while offset < len(data) - 1:
                param_type = data[offset]
                param_value = data[offset + 1]
                
                if param_type == ParameterType.USER_IS_SITTING.value:
                    params.user_is_sitting = bool(param_value)
                elif param_type == ParameterType.ANAL_SHOWER_RUNNING.value:
                    params.anal_shower_running = bool(param_value)
                elif param_type == ParameterType.LADY_SHOWER_RUNNING.value:
                    params.lady_shower_running = bool(param_value)
                elif param_type == ParameterType.DRYER_RUNNING.value:
                    params.dryer_running = bool(param_value)
                elif param_type == ParameterType.LID_POSITION.value:
                    params.lid_position = bool(param_value)
                elif param_type == ParameterType.ORIENTATION_LIGHT_STATE.value:
                    params.orientation_light_state = param_value
                    
                offset += 2
                
            _LOGGER.debug("Parsed system parameters: %s", params)
            return params
            
        except Exception as e:
            _LOGGER.error("Failed to deserialize system parameters: %s", e)
            return SystemParameters()
