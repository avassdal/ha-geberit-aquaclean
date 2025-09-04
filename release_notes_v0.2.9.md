# Release Notes - v0.2.9

## 🚀 Major Bluetooth Reliability Improvements

**Comprehensive stability enhancements for Bluetooth connectivity and error handling**

### ✨ New Features

- **Model-based feature detection:** Replaced unreliable data point probing with SAP number-based feature detection
- **Enhanced notification parsing:** Improved handling of device status notifications
- **Comprehensive model support:** Detection for Sela, Mera, and basic AquaClean models based on SAP patterns
- **Bluetooth connection retry logic:** Automatic retry for transient connection failures
- **Enhanced error recovery:** Improved handling of connection timeouts and network issues

### 🔧 Bluetooth Stability Improvements

- **Connection state tracking:** Fixed inconsistent connection state management
- **Response timeout optimization:** Increased timeout from 10s to 15s for better reliability
- **Retry mechanism:** Added comprehensive retry logic with exponential backoff
- **Error handling:** Enhanced error handling in notification processing to prevent crashes
- **Connection management:** Improved connection lifecycle management

### 🏠 Home Assistant Integration

- **Faster setup:** Integration loads significantly faster without data point probing delays
- **More stable connections:** Eliminates connection timeouts causing setup failures
- **Better entity creation:** Entities created based on confirmed device capabilities
- **Enhanced debugging:** Better logging for troubleshooting both features and Bluetooth issues
- **Reliable operation:** Improved handling of Bluetooth adapter changes and network issues

### 📋 Model Detection Patterns

- **Sela models (146.016-146.019):** Full feature set including mood lighting, spray controls, sensors
- **Mera models (146.012-146.015):** Mid-tier features with basic spray and lighting controls
- **Basic models (146.010-146.011):** Essential wash and dry functions
- **Unknown models:** Safe fallback to basic functionality

### 🐛 Bug Fixes

- Fixed feature discovery timeouts caused by unresponsive data point reads
- Resolved notification parsing errors with actual device data structure
- Fixed import and syntax errors preventing proper protocol parsing
- Eliminated race conditions in feature detection process
- Fixed inconsistent connection state tracking
- Resolved potential coordinator reference crashes
- Improved handling of malformed Bluetooth data packets

### 💡 Bluetooth Best Practices Compliance

- Uses Home Assistant shared Bluetooth scanner
- Implements proper connection timeouts (≥10 seconds)
- Utilizes bleak-retry-connector for reliable connections
- Follows HA Bluetooth integration guidelines for stability
- Proper cleanup and resource management

### 🔄 Upgrade Notes

- Existing integrations will automatically benefit from improved stability
- No configuration changes required
- Feature availability determined by device model rather than probing
- Better entity creation based on actual device capabilities
- Enhanced error recovery for Bluetooth connectivity issues

## 📊 Technical Details

### Connection Improvements
- Response timeout increased from 10s to 15s
- Added retry logic with 2 attempts for critical operations
- Enhanced connection state management
- Improved disconnect handling

### Error Handling
- Granular error handling in notification processing
- Safe fallbacks for malformed data
- Better logging for debugging Bluetooth issues
- Prevention of crashes from protocol parsing errors

This release significantly improves integration reliability, Bluetooth stability, and user experience with comprehensive error handling and recovery mechanisms.
