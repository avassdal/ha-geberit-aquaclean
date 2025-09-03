## 🐛 Hotfix

### Critical Bug Fix
- **Config Flow Import Error**: Fixed `cannot import name 'CONF_MAC_ADDRESS' from 'homeassistant.const'` error
- **Constant Update**: Replaced deprecated `CONF_MAC_ADDRESS` with `CONF_MAC` for Home Assistant compatibility
- **Translation Keys**: Updated strings.json keys from "mac_address" to "mac" for consistency

## 🔧 Technical Details
- Home Assistant core removed `CONF_MAC_ADDRESS` constant in recent versions
- All references updated to use the standard `CONF_MAC` constant
- Config flow now loads without import errors
- Maintains backward compatibility with existing config entries

This hotfix resolves the integration loading failure reported in v0.1.7.
