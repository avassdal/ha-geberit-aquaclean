## 🚀 New Feature: Automatic Bluetooth Discovery

### Bluetooth Discovery
- **Automatic Device Detection**: Integration now automatically discovers Geberit AquaClean devices via Bluetooth
- **Device Matchers**: Added manifest matchers for `Geberit*`, `AquaClean*` local names and manufacturer ID 1281
- **Seamless Setup**: Config flow will trigger automatically when compatible devices are found
- **Fallback Option**: Manual MAC address entry still available if automatic discovery fails

## 🔧 Technical Changes
- Added `bluetooth` section to manifest.json with device discovery patterns
- Config flow `async_step_bluetooth()` will now be triggered automatically
- Bluetooth confirmation step guides users through discovered device setup
- Enhanced user experience with automatic vs manual setup options

This major update transforms the integration from manual-only setup to automatic Bluetooth discovery while maintaining backward compatibility.
