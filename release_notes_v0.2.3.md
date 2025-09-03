# Release Notes v0.2.3

## 🎉 Protocol Breakthrough - Enhanced Frame Analysis

### Major Improvements

**✅ Frame Header Decoding**
- Added comprehensive frame header analysis according to official Geberit protocol specification
- Decodes Frame ID (bits 7-5), Message Type flags (bit 4), Transaction numbers (bits 3-1), and control flags (bit 0)
- Enhanced debugging output shows detailed frame structure breakdown

**✅ Protocol Alignment Confirmed**
- Frame structure perfectly matches official Geberit BLE command reference
- COBS framing with 0x00 delimiters working correctly
- Header byte analysis follows documented bit layout specification

**🔧 Enhanced Debugging**
- Improved notification handler with detailed frame header parsing
- Added hex data logging with frame length information
- Frame analysis shows Frame ID=4 (Extended frame type) from real device data

### Protocol Details

**Frame Header Format (confirmed working):**
```
Bit Layout: | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
            |Frame ID |M|Transaction|F|
```

**Example Frame Analysis:**
- Header: `0x80` = Frame ID=4, MsgType=0, Transaction=0, Flags=0
- COBS framing with proper 0x00 delimiter
- 20-byte frame length consistent with protocol

### Next Steps
- Ready for high-level command implementation (ToggleAnalShower=0, etc.)
- Data point mapping to 800+ available IDs from documentation
- Enhanced device state monitoring capabilities

### Technical Foundation
- BLE service UUIDs verified and working
- Connection stability with bleak-retry-connector
- Home Assistant Bluetooth best practices implemented
