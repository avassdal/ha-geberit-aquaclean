# Geberit AquaClean Home Assistant Integration

A Home Assistant custom component for monitoring and controlling Geberit AquaClean smart toilets via Bluetooth Low Energy (BLE).

## ⚠️ **Important Notice**

**This integration is currently in early development and has not been extensively tested.** Use at your own risk. Please report any issues through the [issue tracker](https://github.com/schmidtfx/ha-geberit-aquaclean/issues).

**Known Limitations:**

- Limited testing across different AquaClean models
- BLE connection stability may vary
- Some advanced features may not be implemented

## Features

**Binary Sensors:**

- User sitting detection
- Anal shower status
- Lady shower status  
- Dryer status
- Connection status

**Controls:**

- Lid position toggle (open/close)

## Installation

### Manual Installation

1. Copy the `custom_components/geberit_aquaclean` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to Configuration → Integrations and click the "+" button.
4. Search for "Geberit AquaClean" and select it.
5. **The integration will automatically scan for nearby Geberit devices** - simply select your device from the discovered list.
6. If no devices are found, you can enter the MAC address manually or scan again.

### HACS Installation

1. Add this repository to HACS as a custom repository.
2. Install the integration through HACS.
3. Restart Home Assistant.
4. Add the integration via the UI.

## Setup

1. Add the integration in Home Assistant via Configuration → Integrations
2. The integration will automatically discover nearby Geberit AquaClean devices
3. Select your device from the list of discovered devices
4. If automatic discovery doesn't find your device:
   - Ensure the toilet is powered on and within Bluetooth range
   - Try scanning again
   - Use manual MAC address entry as fallback

## Requirements

- Home Assistant 2024.1 or later
- Python 3.11+
- Bluetooth adapter with BLE support
- Geberit AquaClean toilet with BLE connectivity

## Supported Models

- Geberit AquaClean Mera
- Other AquaClean models with BLE support

## Troubleshooting

### Connection Issues

- Ensure the toilet is powered on and within range
- Restart the toilet by disconnecting power for a few seconds
- Check for Bluetooth interference from other devices

### Device Not Found

- Verify the MAC address format (XX:XX:XX:XX:XX:XX)
- Use `bluetoothctl scan on` to confirm the device is discoverable

## Implementation Notes

This integration is based on the excellent work by:

- [Thomas Bingel's C# implementation](https://github.com/thomas-bingel/geberit-aquaclean)
- [Jens62's Python port](https://github.com/jens62/geberit-aquaclean)

The current implementation provides a simplified version of the BLE protocol. For advanced features, consider using the full protocol implementation from the reference projects.
