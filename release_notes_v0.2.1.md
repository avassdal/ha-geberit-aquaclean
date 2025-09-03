## 🐛 Critical Entity Loading Hotfix

### Critical Bug Fixes
- **Entity Loading Error**: Fixed `AttributeError: 'GeberitActiveBluetoothCoordinator' object has no attribute 'last_update_success'`
- **ActiveBluetoothCoordinator Compatibility**: Removed `last_update_success` references from all entity availability properties
- **Device Registry Warning**: Removed invalid `via_device` reference causing HA 2025.12.0 deprecation warning

### Files Updated
- **entity.py**: Updated base availability property to remove `last_update_success`
- **binary_sensor.py**: Fixed availability and removed `via_device` from device_info
- **switch.py**: Updated all switch entity availability properties

## 🔧 Technical Details
- `ActiveBluetoothDataUpdateCoordinator` doesn't have `last_update_success` attribute
- All entities now use proper availability checks based on coordinator data
- Device registry entries no longer reference self as `via_device`
- Integration should now load all entities without AttributeError

This hotfix resolves the entity loading failures preventing the integration from functioning after v0.2.0.
