#!/usr/bin/env python3
"""BLE data logger for the ESP32 greenhouse monitor."""

import asyncio
import csv
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Tuple

from bleak import BleakClient, BleakScanner


DEVICE_NAME = "Greenhouse Monitor system"
SERVICE_UUID = "FFF0"
CHAR_SENSOR = "FFF1"
CHAR_CONTROL = "FFF4"
CHAR_THRESHOLD = "FFF7"
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


def parse_threshold_payload(payload: str) -> Optional[Tuple[str, str]]:
    """Parse temperature and soil thresholds."""
    parts = [p.strip() for p in payload.split(",")]
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


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
        "SThresh: {soil_threshold}"
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
        "soil_threshold": None,
    }


async def find_device() -> Optional[str]:
    """Scan and return the BLE address for the greenhouse monitor."""
    logging.info("Scanning for BLE device")
    devices = await BleakScanner.discover()
    for device in devices:
        if device.name == DEVICE_NAME:
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


async def poll_characteristics(client: BleakClient, state: Dict[str, Optional[str]],
                               csv_path: str) -> None:
    """Periodically poll control and threshold characteristics."""
    while client.is_connected:
        control = await read_characteristic(client, CHAR_CONTROL)
        if control:
            parsed = parse_control_payload(control)
            if parsed:
                state["mode"], state["mist_status"], state["pump_status"] = parsed
                logging.info("Receiving control data")

        threshold = await read_characteristic(client, CHAR_THRESHOLD)
        if threshold:
            parsed = parse_threshold_payload(threshold)
            if parsed:
                state["temperature_threshold"], state["soil_threshold"] = parsed
                logging.info("Receiving threshold data")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


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
        log_row(state, csv_path)
        print_live_data(state)

    def on_control(_, data: bytearray) -> None:
        payload = bytes(data).decode("utf-8").strip()
        parsed = parse_control_payload(payload)
        if not parsed:
            return
        state["mode"], state["mist_status"], state["pump_status"] = parsed
        logging.info("Receiving control data")
        log_row(state, csv_path)
        print_live_data(state)

    def on_threshold(_, data: bytearray) -> None:
        payload = bytes(data).decode("utf-8").strip()
        parsed = parse_threshold_payload(payload)
        if not parsed:
            return
        state["temperature_threshold"], state["soil_threshold"] = parsed
        logging.info("Receiving threshold data")
        log_row(state, csv_path)
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


async def connect_and_stream(csv_path: str) -> None:
    """Connect to the device, subscribe, and keep logging until disconnect."""
    state = default_state()

    while True:
        try:
            address = await find_device()
            if not address:
                logging.info("Device not found, rescanning soon")
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)
                continue

            logging.info("Connecting to %s", address)
            async with BleakClient(address) as client:
                if not client.is_connected:
                    logging.warning("Connection failed, retrying")
                    await asyncio.sleep(RECONNECT_DELAY_SECONDS)
                    continue

                logging.info("Connected")

                notify_task = asyncio.create_task(
                    handle_notifications(client, state, csv_path)
                )
                poll_task = asyncio.create_task(
                    poll_characteristics(client, state, csv_path)
                )

                while client.is_connected:
                    await asyncio.sleep(1.0)

                logging.warning("Disconnect event detected")
                notify_task.cancel()
                poll_task.cancel()

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logging.warning("Unexpected error, reconnecting: %s", exc)

        logging.info("Reconnecting")
        await asyncio.sleep(RECONNECT_DELAY_SECONDS)


async def main() -> None:
    """Entry point."""
    setup_logging()
    ensure_csv_exists(CSV_FILE)
    logging.info("Starting BLE greenhouse logger")
    await connect_and_stream(CSV_FILE)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutdown requested")
