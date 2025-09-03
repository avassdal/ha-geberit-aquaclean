## 🔧 Protocol Debugging & Development Tools

### New Debugging Features
- **DEBUG_MODE Flag**: Enable verbose BLE logging without configuration.yaml changes
- **BLE Service Discovery**: Comprehensive logging of device services and characteristics  
- **Hex Data Logging**: Detailed packet inspection for sent/received BLE frames
- **Alternative UUID Detection**: Automatic discovery of available notification characteristics

### New Debug Tools
- **debug_protocol.py**: Standalone BLE testing script for protocol development
- **view_ha_logs.py**: Home Assistant log filtering tool for Geberit-specific entries

### Enhanced Error Handling
- **Smart UUID Discovery**: Integration suggests correct UUIDs when current ones fail
- **Detailed Frame Analysis**: Raw data inspection when protocol parsing fails
- **Connection Diagnostics**: Enhanced BLE connection troubleshooting

## 🚀 Usage

### Enable Debug Mode
Set `DEBUG_MODE = True` in `geberit_client.py` for detailed BLE logging at INFO level.

### Standalone Testing
```bash
python debug_protocol.py AA:BB:CC:DD:EE:FF
```

### Log Analysis  
```bash
python view_ha_logs.py ~/.homeassistant/home-assistant.log
```

## 🎯 Purpose
This release focuses on protocol debugging capabilities to identify correct BLE characteristics and troubleshoot device communication issues. Essential for developers working with Geberit AquaClean protocol implementation.
