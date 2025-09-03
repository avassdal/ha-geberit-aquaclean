## 🐛 Second Critical Hotfix

### Critical Bug Fix
- **Protocol Import Error**: Fixed `cannot import name 'BLEFrameCollector' from 'custom_components.geberit_aquaclean.protocol'` error
- **Class Name Mismatch**: Renamed `FrameCollector` to `BLEFrameCollector` in protocol.py to match import expectations
- **Config Flow Loading**: Config flow now loads without protocol import errors

## 🔧 Technical Details
- `geberit_client.py` was importing `BLEFrameCollector` but `protocol.py` had class named `FrameCollector`
- Fixed class name inconsistency to resolve import error
- Integration should now load successfully without protocol-related failures

This hotfix resolves the second critical import error discovered after v0.1.8 release.
