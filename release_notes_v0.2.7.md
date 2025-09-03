# Release Notes - v0.2.7: Critical Bug Fixes

## Summary

This is a critical maintenance release that resolves several runtime errors and communication issues that were preventing the integration from loading and functioning properly in Home Assistant.

## Critical Bug Fixes

### Fixed Integration Loading Issues
- **Fixed `available_features` attribute error**: Added proper initialization in `GeberitAquaCleanClient` constructor
- **Fixed coordinator import error**: Removed non-existent coordinator import in `light.py` 
- **Fixed entity initialization**: Updated light entities to use correct coordinator access pattern

### Fixed Protocol Communication Issues  
- **Fixed `frame_type` attribute errors**: Updated `BLEFrameCollector` to properly handle `BLEFrame` objects instead of `ProtocolFrame`
- **Fixed WRITE_CHARACTERISTIC_UUID reference**: Corrected undefined characteristic constant usage
- **Fixed DeviceIdentification parsing**: Changed from dictionary `.get()` access to direct attribute access
- **Added null response handling**: Enhanced `parse_system_status_response` to handle None/empty data gracefully

### Improved Error Handling and Logging
- **Enhanced BLE communication robustness**: Better error handling for frame transmission failures
- **Reduced log noise**: Changed timeout warnings to debug level to reduce unnecessary warnings
- **Improved frame collector logic**: Single frames now immediately processed instead of being queued

## Technical Details

### Protocol Improvements
- `BLEFrameCollector` now correctly handles `BLEFrame.frame_id` instead of non-existent `frame_type`
- Single start frames immediately added to complete messages for faster processing
- Enhanced multi-frame assembly logic with proper transaction ordering

### Communication Fixes
- Proper error handling for BLE characteristic write operations
- Graceful handling of communication timeouts without raising exceptions
- Null data validation before attempting to parse protocol responses

### Integration Stability
- All entity platforms now load without attribute errors
- Coordinator pattern correctly implemented throughout the integration
- Device state initialization properly handles missing or invalid data

## Compatibility

- **Home Assistant**: 2023.9.0+
- **Bluetooth Hardware**: All supported Home Assistant Bluetooth adapters
- **Geberit Models**: All AquaClean models with BLE connectivity

## Installation

1. Update through HACS or manual installation
2. Restart Home Assistant
3. Integration should now load without errors

## Known Issues Resolved

- ❌ `'DeviceIdentification' object has no attribute 'get'`
- ❌ `'BLEFrame' object has no attribute 'frame_type'`
- ❌ `ModuleNotFoundError: No module named 'coordinator'`
- ❌ `'GeberitAquaCleanClient' object has no attribute 'available_features'`
- ❌ `object of type 'NoneType' has no len()`

## Testing

All fixes have been validated with protocol-level testing to ensure:
- Frame handling works correctly without attribute errors
- BLE communication handles timeouts gracefully
- Device identification parsing is robust

---

This release focuses on stability and reliability, ensuring the integration loads and communicates properly with Geberit AquaClean devices.
