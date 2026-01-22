#!/usr/bin/env python3
"""
Script to find MAC addresses of network devices.
This can be used to identify the MAC address of the local machine
or connected devices like ESP32/ESP8266.
"""
#address = "F4:65:0B:49:8F:66" 
import uuid
import socket
import platform
import subprocess
import sys

def get_mac_address():
    """Get the MAC address of the primary network interface."""
    mac = uuid.getnode()
    mac_address = ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))
    return mac_address

def get_all_network_interfaces():
    """Get MAC addresses of all network interfaces."""
    interfaces = {}
    system = platform.system()
    
    try:
        if system == "Windows":
            result = subprocess.run(['ipconfig', '/all'], capture_output=True, text=True)
            output = result.stdout
            
            current_adapter = None
            for line in output.split('\n'):
                line = line.strip()
                if 'adapter' in line.lower():
                    current_adapter = line.split(':')[0].strip()
                elif 'Physical Address' in line:
                    mac = line.split(':')[1].strip()
                    if current_adapter:
                        interfaces[current_adapter] = mac
                        
        elif system == "Linux":
            result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
            output = result.stdout
            
            current_interface = None
            for line in output.split('\n'):
                if ': ' in line and not line.startswith(' '):
                    parts = line.split(': ')
                    if len(parts) >= 2:
                        current_interface = parts[1].split('@')[0]
                elif 'link/ether' in line and current_interface:
                    mac = line.split()[1]
                    interfaces[current_interface] = mac
                    current_interface = None
                    
        elif system == "Darwin":  # macOS
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
            output = result.stdout
            
            current_interface = None
            for line in output.split('\n'):
                if not line.startswith('\t') and not line.startswith(' '):
                    current_interface = line.split(':')[0]
                elif 'ether' in line and current_interface:
                    mac = line.split()[1]
                    interfaces[current_interface] = mac
                    
    except Exception as e:
        print(f"Error getting network interfaces: {e}")
    
    return interfaces

def get_bluetooth_devices():
    """Scan for and list connected Bluetooth devices with their MAC addresses."""
    devices = []
    system = platform.system()
    
    try:
        if system == "Windows":
            # Try using Windows Bluetooth API via PowerShell
            ps_command = """
            Get-PnpDevice | Where-Object {
                $_.Class -eq 'Bluetooth' -and $_.Status -eq 'OK'
            } | Select-Object FriendlyName, InstanceId | ForEach-Object {
                $name = $_.FriendlyName
                $id = $_.InstanceId
                # Extract MAC address from InstanceId if available
                if ($id -match '([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})') {
                    Write-Output "$name|$($matches[0])"
                } else {
                    Write-Output "$name|$id"
                }
            }
            """
            result = subprocess.run(['powershell', '-Command', ps_command], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line and '|' in line:
                        parts = line.split('|')
                        devices.append({'name': parts[0], 'address': parts[1]})
            
            # Alternative: Try using bluetooth module if available
            try:
                import bluetooth
                nearby_devices = bluetooth.discover_devices(lookup_names=True, duration=8)
                for addr, name in nearby_devices:
                    devices.append({'name': name, 'address': addr})
            except ImportError:
                pass
            except Exception as e:
                print(f"  Note: bluetooth module scan failed: {e}")
                
        elif system == "Linux":
            # Use bluetoothctl or hcitool
            try:
                result = subprocess.run(['bluetoothctl', 'devices'], 
                                      capture_output=True, text=True, timeout=5)
                for line in result.stdout.split('\n'):
                    if line.startswith('Device'):
                        parts = line.split(maxsplit=2)
                        if len(parts) >= 3:
                            devices.append({'name': parts[2], 'address': parts[1]})
            except FileNotFoundError:
                # Try hcitool as fallback
                result = subprocess.run(['hcitool', 'con'], 
                                      capture_output=True, text=True, timeout=5)
                for line in result.stdout.split('\n')[1:]:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            devices.append({'name': 'Unknown', 'address': parts[2]})
                            
        elif system == "Darwin":  # macOS
            # Use system_profiler
            result = subprocess.run(['system_profiler', 'SPBluetoothDataType'], 
                                  capture_output=True, text=True, timeout=10)
            output = result.stdout
            
            current_device = None
            for line in output.split('\n'):
                line_stripped = line.strip()
                if ':' in line and not line.startswith(' ' * 8):
                    current_device = line_stripped.rstrip(':')
                elif 'Address:' in line and current_device:
                    mac = line.split(':', 1)[1].strip()
                    devices.append({'name': current_device, 'address': mac})
                    current_device = None
                    
    except subprocess.TimeoutExpired:
        print("  Note: Bluetooth scan timed out")
    except Exception as e:
        print(f"  Error scanning Bluetooth devices: {e}")
    
    return devices

def get_serial_devices():
    """List available serial devices (for connected microcontrollers)."""
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        return [(port.device, port.description, port.hwid) for port in ports]
    except ImportError:
        print("pyserial not installed. Install with: pip install pyserial")
        return []

def main():
    """Main function to display all MAC address information."""
    print("=" * 60)
    print("MAC Address Finder")
    print("=" * 60)
    
    # Primary MAC address
    print(f"\nPrimary MAC Address: {get_mac_address()}")
    
    # Hostname
    print(f"Hostname: {socket.gethostname()}")
    
    # All network interfaces
    print("\nAll Network Interfaces:")
    print("-" * 60)
    interfaces = get_all_network_interfaces()
    if interfaces:
        for interface, mac in interfaces.items():
            print(f"  {interface}: {mac}")
    else:
        print("  Unable to retrieve network interfaces")
    
    # Connected serial devices
    print("\nConnected Serial Devices:")
    print("-" * 60)
    devices = get_serial_devices()
    if devices:
        for device, description, hwid in devices:
            print(f"  Port: {device}")
            print(f"    Description: {description}")
            print(f"    Hardware ID: {hwid}")
    else:
        print("  No serial devices found or pyserial not installed")
    
    # Bluetooth devices
    print("\nBluetooth Devices:")
    print("-" * 60)
    bt_devices = get_bluetooth_devices()
    if bt_devices:
        for device in bt_devices:
            print(f"  Name: {device['name']}")
            print(f"    MAC Address: {device['address']}")
    else:
        print("  No Bluetooth devices found")
        print("  Optional: Install PyBluez with: pip install pybluez")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
