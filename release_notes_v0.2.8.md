# Release Notes - v0.2.8

## 🎯 Model-Based Feature Detection

**Major improvement to fix feature discovery timeouts**

### ✨ New Features

- **Model-based feature detection:** Replaced unreliable data point probing with SAP number-based feature detection
- **Enhanced notification parsing:** Improved handling of device status notifications (`30140c030003000000003130001200cf08`)
- **Comprehensive model support:** Detection for Sela, Mera, and basic AquaClean models based on SAP patterns
- **Reliable feature availability:** No more timeouts during feature discovery process

### 🔧 Technical Improvements

- **Eliminated timeout issues:** Feature detection now based on device model instead of probing individual data points
- **Better protocol parsing:** Enhanced notification structure analysis and parsing
- **Improved logging:** More detailed debugging output for feature detection process
- **Fixed import errors:** Resolved syntax issues in protocol parsing modules

### 🏠 Home Assistant Integration

- **Faster setup:** Integration loads significantly faster without data point probing delays
- **More stable:** Eliminates connection timeouts that were causing setup failures
- **Better entity creation:** Entities now created based on confirmed device capabilities
- **Enhanced debugging:** Better logging for troubleshooting feature detection

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

### 💡 Usage

The integration now:
1. Connects to device and reads device identification
2. Determines available features based on SAP number pattern matching
3. Creates appropriate entities for confirmed device capabilities
4. Provides live status updates via enhanced notification parsing

This release significantly improves integration reliability and setup speed.

## 🔄 Upgrade Notes

- Existing integrations will automatically benefit from improved feature detection
- No configuration changes required
- Feature availability now determined by device model rather than probing
- Better entity creation based on actual device capabilities
