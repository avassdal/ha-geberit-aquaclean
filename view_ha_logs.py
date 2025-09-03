#!/usr/bin/env python3
"""
Quick Home Assistant log viewer for Geberit AquaClean debugging.
Filters and displays only relevant log entries.
"""

import sys
import re

def filter_geberit_logs(log_file_path):
    """Filter and display Geberit-related log entries."""
    geberit_patterns = [
        r'geberit_aquaclean',
        r'BLE Services Discovery',
        r'NOTIFY capable',
        r'Available notify characteristics',
        r'Received notification',
        r'Failed to setup notifications',
        r'Attempting to setup notifications'
    ]
    
    combined_pattern = '|'.join(geberit_patterns)
    
    try:
        with open(log_file_path, 'r') as f:
            for line in f:
                if re.search(combined_pattern, line, re.IGNORECASE):
                    # Clean up the line and highlight important parts
                    clean_line = line.strip()
                    
                    # Highlight BLE discoveries
                    if 'Service:' in clean_line or 'Char:' in clean_line:
                        print(f"🔍 {clean_line}")
                    # Highlight notifications
                    elif 'notification' in clean_line.lower():
                        print(f"📡 {clean_line}")
                    # Highlight errors
                    elif 'error' in clean_line.lower() or 'failed' in clean_line.lower():
                        print(f"❌ {clean_line}")
                    # General info
                    else:
                        print(f"ℹ️  {clean_line}")
                        
    except FileNotFoundError:
        print(f"Log file not found: {log_file_path}")
        print("Common HA log locations:")
        print("  Docker: /config/home-assistant.log")
        print("  Supervised: /usr/share/hassio/homeassistant/home-assistant.log")
        print("  Core: ~/.homeassistant/home-assistant.log")

def main():
    if len(sys.argv) != 2:
        print("Usage: python view_ha_logs.py <path_to_home_assistant.log>")
        print("Example: python view_ha_logs.py ~/.homeassistant/home-assistant.log")
        return
        
    log_file = sys.argv[1]
    print(f"Filtering Geberit AquaClean logs from: {log_file}")
    print("=" * 60)
    
    filter_geberit_logs(log_file)

if __name__ == "__main__":
    main()
