# Release Notes - Version 0.2.5

## New Features

### Light Control Platform

- Added complete night light control support with RGB color and brightness adjustment
- Light entity appears automatically for devices that support night light feature
- Full Home Assistant UI integration with color picker and brightness slider
- Protocol integration using data points 35-38 for brightness and RGB values

### Dynamic Feature Discovery

- Implemented automatic feature detection by probing device capabilities
- Only creates entities for features actually supported by the connected device model
- Eliminates hardcoded feature assumptions for better multi-model compatibility
- Feature probing with optimized timeouts to avoid blocking device setup

## Technical Improvements

### Enhanced Device State

- Added night light properties to device state tracking
- RGB color values (0-255 per channel) and brightness (0-100%)
- Proper state synchronization between Home Assistant and device

### Protocol Enhancements

- New client methods for night light control:
  - `set_night_light_state(on/off)`
  - `set_night_light_brightness(0-100%)`
  - `set_night_light_color(r, g, b)`
- Feature test map for systematic capability detection

## Usage

Users can now:

- Control night light on/off directly from Home Assistant
- Adjust brightness with smooth slider control (0-100%)
- Set any RGB color using the built-in color picker
- See real-time state updates for light status and settings

The light control only appears for Geberit models that actually support night light functionality.

## Compatibility

- Maintains full backward compatibility with previous versions
- No configuration changes required
- Automatic feature detection adapts to different device models
- Enhanced BLE communication reliability

## Installation

Update through HACS or manually replace the custom component files. The integration will automatically detect and enable light controls for compatible devices.
