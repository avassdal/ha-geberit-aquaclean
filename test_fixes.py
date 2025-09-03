#!/usr/bin/env python3
"""Test script to verify critical fixes in Geberit AquaClean integration."""

import sys
import logging
from pathlib import Path

# Add custom components to path
sys.path.insert(0, str(Path(__file__).parent / "custom_components"))

logging.basicConfig(level=logging.INFO)

def test_imports():
    """Test that all modules can be imported without errors."""
    print("Testing imports...")
    
    try:
        from geberit_aquaclean.geberit_client import GeberitAquaCleanClient
        print("✅ GeberitAquaCleanClient imported successfully")
    except Exception as e:
        print(f"❌ Failed to import GeberitAquaCleanClient: {e}")
        return False
    
    try:
        from geberit_aquaclean.protocol import BLEFrame, BLEFrameCollector, GeberitProtocolSerializer
        print("✅ Protocol classes imported successfully")
    except Exception as e:
        print(f"❌ Failed to import protocol classes: {e}")
        return False
    
    try:
        from geberit_aquaclean.light import async_setup_entry
        print("✅ Light platform imported successfully")
    except Exception as e:
        print(f"❌ Failed to import light platform: {e}")
        return False
    
    return True

def test_client_initialization():
    """Test client initialization with required attributes."""
    print("\nTesting client initialization...")
    
    try:
        from geberit_aquaclean.geberit_client import GeberitAquaCleanClient
        
        # Mock hass object
        class MockHass:
            pass
        
        client = GeberitAquaCleanClient("00:11:22:33:44:55", MockHass())
        
        # Check required attributes exist
        if not hasattr(client, 'available_features'):
            print("❌ Client missing available_features attribute")
            return False
            
        if not isinstance(client.available_features, dict):
            print("❌ available_features is not a dict")
            return False
            
        print("✅ Client initialized with required attributes")
        return True
        
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        return False

def test_ble_frame_handling():
    """Test BLE frame creation and handling."""
    print("\nTesting BLE frame handling...")
    
    try:
        from geberit_aquaclean.protocol import BLEFrame, BLEFrameCollector, BLEFrameType
        
        # Create a test frame
        frame = BLEFrame(
            frame_id=BLEFrameType.SINGLE_START_FRAME.value,
            has_msg_type=True,
            transaction=0,
            flag=0,
            payload=b'\x01\x02\x03'
        )
        
        # Test frame collector
        collector = BLEFrameCollector()
        result = collector.add_frame(frame)
        
        if not result:
            print("❌ Frame collector did not return True for single frame")
            return False
            
        message = collector.get_complete_message()
        if message != b'\x01\x02\x03':
            print(f"❌ Expected payload b'\\x01\\x02\\x03', got {message}")
            return False
            
        print("✅ BLE frame handling works correctly")
        return True
        
    except Exception as e:
        print(f"❌ BLE frame handling failed: {e}")
        return False

def test_protocol_serialization():
    """Test protocol serialization functionality."""
    print("\nTesting protocol serialization...")
    
    try:
        from geberit_aquaclean.protocol import GeberitProtocolSerializer, HighLevelCommand
        
        # Test high-level command creation
        frame = GeberitProtocolSerializer.create_high_level_command(
            HighLevelCommand.TOGGLE_ANAL_SHOWER
        )
        
        if frame.frame_id != 0:  # SINGLE_START_FRAME
            print(f"❌ Expected frame_id 0, got {frame.frame_id}")
            return False
            
        if not frame.has_msg_type:
            print("❌ Expected has_msg_type to be True")
            return False
            
        print("✅ Protocol serialization works correctly")
        return True
        
    except Exception as e:
        print(f"❌ Protocol serialization failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Running Geberit AquaClean Integration Fix Tests\n")
    
    tests = [
        test_imports,
        test_client_initialization,
        test_ble_frame_handling,
        test_protocol_serialization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Integration fixes verified successfully.")
        return 0
    else:
        print("❌ Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
