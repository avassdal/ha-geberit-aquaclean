#!/usr/bin/env python3
"""
Protocol debugging utility for Geberit AquaClean BLE communication.
Run this script to test protocol communication independently of Home Assistant.
"""

import asyncio
import logging
import binascii
from bleak import BleakClient, BleakScanner

# For now, skip protocol import to focus on BLE discovery
# We'll decode the basic frame structure manually
# from custom_components.geberit_aquaclean.protocol import GeberitProtocolSerializer

# Configure detailed logging to both console and file
log_filename = f"geberit_debug_{asyncio.get_event_loop().time():.0f}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

print(f"Debug output will be saved to: {log_filename}")

# BLE UUIDs - Geberit custom service discovered
WRITE_CHARACTERISTIC_UUID = "3334429d-90f3-4c41-a02d-5cb3a33e0000"  # Write capability (Handle 8)
NOTIFY_CHARACTERISTIC_UUID = "3334429d-90f3-4c41-a02d-5cb3a63e0000"  # Notify capability (Handle 18)

class ProtocolDebugger:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client = None
        self.notifications = []
        
    async def scan_and_connect(self):
        """Scan for device and connect."""
        print(f"Scanning for device {self.mac_address}...")
        
        device = await BleakScanner.find_device_by_address(self.mac_address)
        if not device:
            print(f"Device {self.mac_address} not found!")
            return False
            
        print(f"Found device: {device.name} ({device.address})")
        
        self.client = BleakClient(device)
        await self.client.connect()
        print(f"Connected: {self.client.is_connected}")
        
        return True
        
    async def discover_services(self):
        """Discover all BLE services and characteristics."""
        print("\n=== BLE Services Discovery ===")
        
        for service in self.client.services:
            print(f"Service: {service.uuid}")
            print(f"  Description: {service.description}")
            
            for char in service.characteristics:
                # Handle different property formats
                try:
                    if hasattr(char.properties[0], 'name'):
                        props = [p.name for p in char.properties]
                        readable = "read" in [p.name.lower() for p in char.properties]
                        notifiable = "notify" in [p.name.lower() for p in char.properties]
                    else:
                        props = list(char.properties)
                        readable = "read" in char.properties
                        notifiable = "notify" in char.properties
                except (IndexError, AttributeError):
                    props = str(char.properties)
                    readable = "read" in str(char.properties).lower()
                    notifiable = "notify" in str(char.properties).lower()
                
                print(f"  Characteristic: {char.uuid}")
                print(f"    Properties: {props}")
                print(f"    Handle: {char.handle}")
                if notifiable:
                    print("    -> NOTIFY CAPABLE!")
                
                # Try to read characteristic if readable
                if readable:
                    try:
                        value = await self.client.read_gatt_char(char.uuid)
                        hex_value = binascii.hexlify(value).decode('ascii')
                        print(f"    Value: {hex_value} ('{value.decode('ascii', errors='ignore')}')")
                    except Exception as e:
                        print(f"    Read failed: {e}")
                        
    def notification_handler(self, sender: int, data: bytes):
        """Handle BLE notifications for debugging."""
        hex_data = binascii.hexlify(data).decode('ascii')
        print(f"NOTIFICATION from {sender}: {hex_data} (len={len(data)})")
        
        # Store for analysis
        self.notifications.append({
            'sender': sender,
            'data': data,
            'hex': hex_data,
            'timestamp': asyncio.get_event_loop().time()
        })
        
        # Basic frame analysis (without protocol import)
        try:
            # Simple COBS detection - look for 0x00 delimiter
            if data and data[-1] == 0x00:
                print("  Possible COBS frame (ends with 0x00)")
            else:
                print("  Raw data frame")
            
            # Look for common patterns
            if len(data) > 0:
                print(f"  First byte: 0x{data[0]:02x}, Last byte: 0x{data[-1]:02x}")
        except Exception as e:
            print(f"  Analysis error: {e}")
            
    async def setup_notifications(self):
        """Setup notifications on target characteristic."""
        try:
            print(f"Setting up notifications on {NOTIFY_CHARACTERISTIC_UUID}")
            await self.client.start_notify(NOTIFY_CHARACTERISTIC_UUID, self.notification_handler)
            print("Notifications setup successful")
            return True
        except Exception as e:
            print(f"Failed to setup notifications: {e}")
            
            # Try to find notify-capable characteristics
            notify_chars = []
            for service in self.client.services:
                for char in service.characteristics:
                    # Handle different property formats
                    try:
                        if hasattr(char.properties[0], 'name'):
                            notifiable = "notify" in [p.name.lower() for p in char.properties]
                        else:
                            notifiable = "notify" in char.properties
                    except (IndexError, AttributeError):
                        notifiable = "notify" in str(char.properties).lower()
                    
                    if notifiable:
                        notify_chars.append(str(char.uuid))
                        print(f"  Found notify characteristic: {char.uuid}")
            return False
            
    async def send_test_commands(self):
        """Send test commands to device."""
        test_commands = [
            # Device identification request
            b'\x00\x01\x02\x03',  # Example command - replace with actual protocol
            # Status request
            b'\x00\x01\x02\x04',  # Example command - replace with actual protocol
        ]
        
        print("\n=== Sending Test Commands ===")
        
        for i, cmd in enumerate(test_commands):
            try:
                hex_cmd = binascii.hexlify(cmd).decode('ascii')
                print(f"Sending command {i+1}: {hex_cmd}")
                
                await self.client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, cmd)
                print("Command sent successfully")
                
                # Wait for response
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Failed to send command {i+1}: {e}")
                
    async def run_debug_session(self):
        """Run complete debugging session."""
        if not await self.scan_and_connect():
            return
            
        await self.discover_services()
        
        if await self.setup_notifications():
            await self.send_test_commands()
            
            # Wait for more notifications
            print("\nListening for notifications (press Ctrl+C to stop)...")
            try:
                await asyncio.sleep(30)  # Listen for 30 seconds
            except KeyboardInterrupt:
                print("Stopping...")
                
        # Analyze collected data
        print(f"\n=== Analysis: Collected {len(self.notifications)} notifications ===")
        for notif in self.notifications:
            print(f"Time: {notif['timestamp']:.2f}, Data: {notif['hex']}")
            
        await self.client.disconnect()
        print("Disconnected")

async def main():
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python debug_protocol.py <MAC_ADDRESS>")
        print("Example: python debug_protocol.py AA:BB:CC:DD:EE:FF")
        return
        
    mac_address = sys.argv[1]
    debugger = ProtocolDebugger(mac_address)
    await debugger.run_debug_session()

if __name__ == "__main__":
    asyncio.run(main())
