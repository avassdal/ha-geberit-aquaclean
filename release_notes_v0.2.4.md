# Release Notes v0.2.4

## 🐛 Critical Bug Fix - BLE Property Handling

### Fixed Issues

**✅ Property Enumeration Error**
- Fixed `'str' object has no attribute 'name'` error during BLE characteristic discovery
- Added proper type checking for characteristic properties (string vs object)
- Prevents notification setup failures that blocked device connection

**✅ Improved Error Handling**
- Enhanced property detection with `hasattr()` checks
- Robust handling of different bleak property formats
- Better compatibility across different Python/bleak versions

### Technical Details

**Bug Summary:**
- BLE characteristic property enumeration was failing when properties were returned as strings instead of objects
- This prevented the notification setup from completing successfully
- Integration would fail to connect to devices

**Fix Applied:**
```python
# Before: Assumed properties always have .name attribute
props = [p.name for p in char.properties]  # FAILED

# After: Handle both string and object properties
props = []
for p in char.properties:
    if hasattr(p, 'name'):
        props.append(p.name)
    else:
        props.append(str(p))
```

### Impact
- Resolves connection failures seen in v0.2.3
- Ensures reliable BLE service discovery
- Enables enhanced frame analysis to work properly
- Critical fix for integration functionality

### Compatibility
- All enhanced frame analysis features from v0.2.3 remain intact
- Protocol alignment and COBS framing detection working
- Ready for high-level command implementation and data point mapping
