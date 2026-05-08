#!/usr/bin/env python3
"""Unified BLE logger and control for the ESP32 greenhouse monitor.

This script maintains a single BLE connection and provides:
- Continuous data logging to CSV
- Live threshold and mode changes via keyboard commands
- Real-time sensor display

Only ONE instance can connect to the ESP32 at a time.
"""

import asyncio
import csv
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Optional, Tuple

from bleak import BleakClient, BleakScanner


# BLE Configuration
DEVICE_NAME = "Greenhouse Monitor system"
SERVICE_UUID = "FFF0"
CHAR_SENSOR = "FFF1"
CHAR_CONTROL = "FFF4"
CHAR_THRESHOLD = "FFF7"

# Logging Configuration
CSV_FILE = "greenhouse_complete_log.csv"
POLL_INTERVAL_SECONDS = 5.0
RECONNECT_DELAY_SECONDS = 2.0

CSV_COLUMNS = [
    "timestamp",
    "temperature",
    "humidity",
    "soil_moisture",
    "battery_voltage",
    "mode",
    "mist_status",
    "pump_status",
    "temperature_threshold",
    "humidity_threshold",
    "soil_threshold",
]


def setup_logging() -> None:
    """Configure console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def ensure_csv_exists(path: str) -> None:
    """Create the CSV file with headers if it does not exist."""
    if os.path.exists(path):
        return
    with open(path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(CSV_COLUMNS)


def parse_sensor_payload(payload: str) -> Optional[Tuple[str, str, str, str]]:
    """Parse temperature, humidity, soil moisture, and battery voltage."""
    parts = [p.strip() for p in payload.split(",")]
    if len(parts) != 4:
        return None
    return parts[0], parts[1], parts[2], parts[3]


def parse_control_payload(payload: str) -> Optional[Tuple[str, str, str]]:
    """Parse mode, mist, and pump states."""
    parts = [p.strip() for p in payload.split(",")]
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


def parse_threshold_payload(payload: str) -> Optional[Tuple[str, str, str]]:
    """Parse temperature, humidity, and soil thresholds."""
    parts = [p.strip() for p in payload.split(",")]
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


def utc_timestamp() -> str:
    """Return local timestamp string for CSV."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_row(state: Dict[str, Optional[str]], csv_path: str) -> None:
    """Write a single row to CSV and flush immediately."""
    row = [
        utc_timestamp(),
        state.get("temperature"),
        state.get("humidity"),
        state.get("soil_moisture"),
        state.get("battery_voltage"),
        state.get("mode"),
        state.get("mist_status"),
        state.get("pump_status"),
        state.get("temperature_threshold"),
        state.get("humidity_threshold"),
        state.get("soil_threshold"),
    ]

    with open(csv_path, "a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(row)
        csv_file.flush()

    logging.info("Writing CSV row")


def print_live_data(state: Dict[str, Optional[str]]) -> None:
    """Display the most recent values in a readable format."""
    line = (
        "Temp: {temperature} C | Hum: {humidity} % | Soil: {soil_moisture} | "
        "Batt: {battery_voltage} V | Mode: {mode} | Mist: {mist_status} | "
        "Pump: {pump_status} | TThresh: {temperature_threshold} | "
        "HThresh: {humidity_threshold} | SThresh: {soil_threshold}"
    ).format(**state)
    logging.info(line)


def default_state() -> Dict[str, Optional[str]]:
    """Initialize the latest-value state dictionary."""
    return {
        "temperature": None,
        "humidity": None,
        "soil_moisture": None,
        "battery_voltage": None,
        "mode": None,
        "mist_status": None,
        "pump_status": None,
        "temperature_threshold": None,
        "humidity_threshold": None,
        "soil_threshold": None,
    }


def print_menu() -> None:
    """Print the interactive control menu."""
    print("\n" + "=" * 60)
    print("GREENHOUSE MONITOR - Unified Logger & Control")
    print("=" * 60)
    print("Commands:")
    print("  1 - Set temperature threshold (mist ON when temp > threshold)")
    print("  2 - Set humidity threshold (mist ON when humidity < threshold)")
    print("  3 - Set soil moisture threshold (pump ON when soil > threshold)")
    print("  4 - Set ALL thresholds at once")
    print("  5 - Switch to AUTO mode (threshold-based control)")
    print("  6 - Switch to MANUAL mode")
    print("  7 - Turn mist ON/OFF (manual mode)")
    print("  8 - Turn pump ON/OFF (manual mode)")
    print("  s - Show current status")
    print("  h - Show this help menu")
    print("  q - Quit")
    print("=" * 60)


async def find_device() -> Optional[str]:
    """Scan and return the BLE address for the greenhouse monitor."""
    logging.info("Scanning for BLE device")
    devices = await BleakScanner.discover()
    for device in devices:
        if device.name == DEVICE_NAME:
            logging.info(f"Found device: {device.name} ({device.address})")
            return device.address
    return None


async def read_characteristic(client: BleakClient, uuid: str) -> Optional[str]:
    """Read a characteristic as a UTF-8 string."""
    try:
        data = await client.read_gatt_char(uuid)
        return bytes(data).decode("utf-8").strip()
    except Exception as exc:
        logging.warning("Failed to read %s: %s", uuid, exc)
        return None


async def write_characteristic(client: BleakClient, uuid: str, value: str) -> bool:
    """Write a string value to a characteristic."""
    try:
        await client.write_gatt_char(uuid, value.encode("utf-8"))
        logging.info("Wrote to %s: %s", uuid, value)
        return True
    except Exception as exc:
        logging.warning("Failed to write %s: %s", uuid, exc)
        return False


async def set_thresholds(client: BleakClient, temp_thresh: float, humid_thresh: float, 
                         soil_thresh: int, state: Dict[str, Optional[str]]) -> bool:
    """Set temperature, humidity, and soil moisture thresholds."""
    value = f"{temp_thresh:.1f},{humid_thresh:.1f},{soil_thresh}"
    success = await write_characteristic(client, CHAR_THRESHOLD, value)
    if success:
        # Update local state immediately for display
        state["temperature_threshold"] = f"{temp_thresh:.1f}"
        state["humidity_threshold"] = f"{humid_thresh:.1f}"
        state["soil_threshold"] = str(soil_thresh)
        logging.info(f"Thresholds updated: T={temp_thresh}°C, H={humid_thresh}%, S={soil_thresh}")
    return success


async def set_control(client: BleakClient, mode: int, mist: int, pump: int,
                      state: Dict[str, Optional[str]]) -> bool:
    """Set control mode and manual actuator states."""
    value = f"{mode},{mist},{pump}"
    success = await write_characteristic(client, CHAR_CONTROL, value)
    if success:
        # Update local state immediately for display
        state["mode"] = str(mode)
        state["mist_status"] = str(mist)
        state["pump_status"] = str(pump)
        mode_str = "AUTO" if mode == 0 else "MANUAL"
        logging.info(f"Control updated: Mode={mode_str}, Mist={mist}, Pump={pump}")
    return success


async def poll_characteristics(client: BleakClient, state: Dict[str, Optional[str]],
                               csv_path: str) -> None:
    """Periodically poll control and threshold characteristics."""
    while client.is_connected:
        try:
            control = await read_characteristic(client, CHAR_CONTROL)
            if control:
                parsed = parse_control_payload(control)
                if parsed:
                    state["mode"], state["mist_status"], state["pump_status"] = parsed
                    logging.debug("Polled control data: %s", control)

            threshold = await read_characteristic(client, CHAR_THRESHOLD)
            if threshold:
                parsed = parse_threshold_payload(threshold)
                if parsed:
                    (
                        state["temperature_threshold"],
                        state["humidity_threshold"],
                        state["soil_threshold"],
                    ) = parsed
                    logging.debug("Polled threshold data: %s", threshold)
            
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logging.warning("Poll error: %s", exc)
            await asyncio.sleep(1.0)


async def handle_notifications(client: BleakClient, state: Dict[str, Optional[str]],
                               csv_path: str) -> None:
    """Subscribe to notifications and update the state."""

    def on_sensor(_, data: bytearray) -> None:
        payload = bytes(data).decode("utf-8").strip()
        parsed = parse_sensor_payload(payload)
        if not parsed:
            return
        state["temperature"], state["humidity"], state["soil_moisture"], state["battery_voltage"] = parsed
        logging.info("Receiving sensor data")
        log_row(state, csv_path)  # Only log when sensor data arrives
        print_live_data(state)

    def on_control(_, data: bytearray) -> None:
        payload = bytes(data).decode("utf-8").strip()
        parsed = parse_control_payload(payload)
        if not parsed:
            return
        state["mode"], state["mist_status"], state["pump_status"] = parsed
        logging.info("Receiving control data")
        print_live_data(state)

    def on_threshold(_, data: bytearray) -> None:
        payload = bytes(data).decode("utf-8").strip()
        parsed = parse_threshold_payload(payload)
        if not parsed:
            return
        (
            state["temperature_threshold"],
            state["humidity_threshold"],
            state["soil_threshold"],
        ) = parsed
        logging.info("Receiving threshold data")
        print_live_data(state)

    try:
        await client.start_notify(CHAR_SENSOR, on_sensor)
    except Exception as exc:
        logging.warning("Sensor notifications unavailable: %s", exc)

    try:
        await client.start_notify(CHAR_CONTROL, on_control)
    except Exception as exc:
        logging.warning("Control notifications unavailable: %s", exc)

    try:
        await client.start_notify(CHAR_THRESHOLD, on_threshold)
    except Exception as exc:
        logging.warning("Threshold notifications unavailable: %s", exc)


async def read_user_input(loop: asyncio.AbstractEventLoop) -> str:
    """Read user input asynchronously."""
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    return await reader.readline()


async def handle_user_commands(client: BleakClient, state: Dict[str, Optional[str]]) -> None:
    """Handle interactive keyboard commands while connected."""
    loop = asyncio.get_event_loop()
    
    # Current threshold values (local cache)
    temp_thresh = 25.0
    humid_thresh = 40.0
    soil_thresh = 2500
    
    print_menu()
    
    while client.is_connected:
        try:
            # Use asyncio.to_thread for blocking input
            raw_line = await asyncio.to_thread(input, "\nEnter command (h for help): ")
            choice = raw_line.strip().lower()
            
            if choice == 'q':
                logging.info("Quit requested by user")
                print("Disconnecting...")
                break
            
            elif choice == 'h':
                print_menu()
            
            elif choice == 's':
                print("\n--- Current Status ---")
                print(f"Temperature: {state.get('temperature', 'N/A')} °C")
                print(f"Humidity: {state.get('humidity', 'N/A')} %")
                print(f"Soil Moisture: {state.get('soil_moisture', 'N/A')}")
                print(f"Battery: {state.get('battery_voltage', 'N/A')} V")
                print(f"Mode: {'AUTO' if state.get('mode') == '0' else 'MANUAL' if state.get('mode') == '1' else 'N/A'}")
                print(f"Mist: {'ON' if state.get('mist_status') == '1' else 'OFF'}")
                print(f"Pump: {'ON' if state.get('pump_status') == '1' else 'OFF'}")
                print(f"Temp Threshold: {state.get('temperature_threshold', 'N/A')} °C")
                print(f"Humid Threshold: {state.get('humidity_threshold', 'N/A')} %")
                print(f"Soil Threshold: {state.get('soil_threshold', 'N/A')}")
                print("----------------------")
            
            elif choice == '1':
                try:
                    val = input(f"Enter temperature threshold °C (current: {temp_thresh}): ")
                    temp_thresh = float(val)
                    await set_thresholds(client, temp_thresh, humid_thresh, soil_thresh, state)
                except ValueError:
                    print("Invalid number!")
            
            elif choice == '2':
                try:
                    val = input(f"Enter humidity threshold % (current: {humid_thresh}): ")
                    humid_thresh = float(val)
                    await set_thresholds(client, temp_thresh, humid_thresh, soil_thresh, state)
                except ValueError:
                    print("Invalid number!")
            
            elif choice == '3':
                try:
                    val = input(f"Enter soil moisture threshold (current: {soil_thresh}): ")
                    soil_thresh = int(val)
                    await set_thresholds(client, temp_thresh, humid_thresh, soil_thresh, state)
                except ValueError:
                    print("Invalid number!")
            
            elif choice == '4':
                try:
                    temp_thresh = float(input("Enter temperature threshold °C: "))
                    humid_thresh = float(input("Enter humidity threshold %: "))
                    soil_thresh = int(input("Enter soil moisture threshold: "))
                    await set_thresholds(client, temp_thresh, humid_thresh, soil_thresh, state)
                except ValueError:
                    print("Invalid number!")
            
            elif choice == '5':
                await set_control(client, 0, 0, 0, state)
                print("Switched to AUTO mode")
            
            elif choice == '6':
                await set_control(client, 1, 0, 0, state)
                print("Switched to MANUAL mode (actuators OFF)")
            
            elif choice == '7':
                val = input("Turn mist ON or OFF? (on/off): ").strip().lower()
                if val == 'on':
                    await set_control(client, 1, 1, int(state.get("pump_status", 0)), state)
                    print("Mist turned ON (MANUAL mode)")
                elif val == 'off':
                    await set_control(client, 1, 0, int(state.get("pump_status", 0)), state)
                    print("Mist turned OFF (MANUAL mode)")
                else:
                    print("Invalid input! Use 'on' or 'off'")
            
            elif choice == '8':
                val = input("Turn pump ON or OFF? (on/off): ").strip().lower()
                if val == 'on':
                    await set_control(client, 1, int(state.get("mist_status", 0)), 1, state)
                    print("Pump turned ON (MANUAL mode)")
                elif val == 'off':
                    await set_control(client, 1, int(state.get("mist_status", 0)), 0, state)
                    print("Pump turned OFF (MANUAL mode)")
                else:
                    print("Invalid input! Use 'on' or 'off'")
            
            else:
                print("Unknown command! Press 'h' for help.")
        
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logging.warning("Input handling error: %s", exc)


async def connect_and_run(csv_path: str) -> None:
    """Connect to the device and run both logging and interactive control."""
    state = default_state()
    
    while True:
        try:
            address = await find_device()
            if not address:
                logging.info("Device not found, rescanning in %ss", RECONNECT_DELAY_SECONDS)
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)
                continue
            
            logging.info("Connecting to %s", address)
            async with BleakClient(address) as client:
                if not client.is_connected:
                    logging.warning("Connection failed, retrying")
                    await asyncio.sleep(RECONNECT_DELAY_SECONDS)
                    continue
                
                logging.info("✓ Connected! Ready for commands...")
                print("\n" + "=" * 60)
                print("CONNECTED to Greenhouse Monitor")
                print("Logging to:", CSV_FILE)
                print("=" * 60)
                
                # Start notification handler
                notify_task = asyncio.create_task(
                    handle_notifications(client, state, csv_path)
                )
                
                # Start polling task (for characteristics that don't notify)
                poll_task = asyncio.create_task(
                    poll_characteristics(client, state, csv_path)
                )
                
                # Run user command handler (blocking until quit or disconnect)
                await handle_user_commands(client, state)
                
                # Clean up tasks
                notify_task.cancel()
                poll_task.cancel()
                
                try:
                    await asyncio.gather(notify_task, poll_task, return_exceptions=True)
                except asyncio.CancelledError:
                    pass
                
                # Check if user requested quit
                if not client.is_connected:
                    logging.info("User disconnected")
                    return
        
        except asyncio.CancelledError:
            logging.info("Shutdown requested")
            return
        except Exception as exc:
            logging.warning("Unexpected error: %s", exc)
        
        logging.info("Reconnecting in %ss", RECONNECT_DELAY_SECONDS)
        await asyncio.sleep(RECONNECT_DELAY_SECONDS)


async def main() -> None:
    """Entry point."""
    setup_logging()
    ensure_csv_exists(CSV_FILE)
    logging.info("Starting unified BLE greenhouse logger & control")
    logging.info("CSV file: %s", CSV_FILE)
    await connect_and_run(CSV_FILE)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutdown requested")
